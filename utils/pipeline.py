import pandas as pd
import logging
from shapely.geometry import Polygon, Point
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_data(path=None):
    """Load the UNSW F1 2024 dataset, defaulting to repo structure if no path is given."""
    if path:
        return pd.read_csv(f"{path}")
    else:
        return pd.read_csv("data/UNSW F12024.csv")


def filter_melbourne(df):
    """Keep only laps from the Melbourne circuit."""
    return df[df["M_TRACKID"] == 0]


def track_slice(df):
    """Restrict lap coordinates to X: [0,500], Y: [-250,600]."""
    return df[
        (df["M_WORLDPOSITIONX_1"] >= 0)
        & (df["M_WORLDPOSITIONX_1"] <= 600)
        & (df["M_WORLDPOSITIONY_1"] >= -200)
        & (df["M_WORLDPOSITIONY_1"] <= 600)
    ]


def re_index(df):
    """Add a global 0-based lap index per unique session/lap combination."""

    # Drop duplicates to get unique session/lap pairs in order
    unique_laps = df[["M_SESSIONUID", "M_CURRENTLAPNUM"]].drop_duplicates()

    # Sort by session, then lap
    unique_laps = unique_laps.sort_values(["M_SESSIONUID", "M_CURRENTLAPNUM"])

    # Assign a global 0-based index
    unique_laps["lap_index"] = range(len(unique_laps))

    # Map the lap_index back to all rows in the original dataframe
    df = df.merge(unique_laps, on=["M_SESSIONUID", "M_CURRENTLAPNUM"], how="left")

    return df


def read_process_left(path=None):
    """Load and restrict the left track limits to expected coordinate bounds."""
    if path:
        left = pd.read_csv(f"{path}")
    else:
        left = pd.read_csv("data/f1sim-ref-left.csv")

    # Restrict to the same bounds as track_slice
    left = left[
        (left["WORLDPOSX"] >= 0)
        & (left["WORLDPOSX"] <= 600)
        & (left["WORLDPOSY"] >= -200)
        & (left["WORLDPOSY"] <= 600)
    ]

    return left


def read_process_right(path=None):
    """Load and restrict the right track limits to expected coordinate bounds."""
    if path:
        right = pd.read_csv(f"{path}")
    else:
        right = pd.read_csv("data/f1sim-ref-right.csv")

    # Restrict to the same bounds as track_slice
    right = right[
        (right["WORLDPOSX"] >= 0)
        & (right["WORLDPOSX"] <= 600)
        & (right["WORLDPOSY"] >= -200)
        & (right["WORLDPOSY"] <= 600)
    ]

    return right


def enforce_track_limits(df, left, right):
    """Remove laps where any telemetry point exceeds a given distance from track edges."""

    # Combine track edges
    track_points = np.vstack(
        [
            left[["WORLDPOSX", "WORLDPOSY"]].values,
            right[["WORLDPOSX", "WORLDPOSY"]].values,
        ]
    )
    tracklims = Polygon(track_points)

    df["inside_track"] = df.apply(
        lambda row: tracklims.contains(
            Point(row["M_WORLDPOSITIONX_1"], row["M_WORLDPOSITIONY_1"])
        ),
        axis=1,
    )

    df["dist_to_track"] = df.apply(
        lambda row: (
            0
            if row["inside_track"]
            else tracklims.exterior.distance(
                Point(row["M_WORLDPOSITIONX_1"], row["M_WORLDPOSITIONY_1"])
            )
        ),
        axis=1,
    )

    offtrack_laps = df[df["dist_to_track"] > 10][["lap_index"]].drop_duplicates()

    df = df.merge(offtrack_laps, on=["lap_index"], how="left", indicator=True)
    df = df[df["_merge"] == "left_only"].drop(
        columns=["_merge", "inside_track", "dist_to_track"]
    )

    return df


# def remove_short_laps(df, min_points=900):
#     """Remove laps that have fewer than min_points telemetry points."""
#     # Count points per lap
#     lap_counts = df.groupby("lap_index").size().reset_index(name="n_points")

#     # Keep only laps with enough points
#     valid_laps = lap_counts[lap_counts["n_points"] >= min_points]["lap_index"]

#     df = df[df["lap_index"].isin(valid_laps)]
#     return df


def remove_short_laps(df, min_points=900):
    """
    Remove laps that have fewer than min_points telemetry points.

    Returns:
        df_clean: DataFrame with valid laps
        discarded_laps: DataFrame of laps that were removed
    """
    # Count points per lap
    lap_counts = df.groupby("lap_index").size().reset_index(name="n_points")

    # Identify valid and discarded laps
    valid_laps = lap_counts[lap_counts["n_points"] >= min_points]["lap_index"]
    discarded_laps_idx = lap_counts[lap_counts["n_points"] < min_points]["lap_index"]

    # Filter data
    df_clean = df[df["lap_index"].isin(valid_laps)]
    discarded_laps = df[df["lap_index"].isin(discarded_laps_idx)]

    return df_clean, discarded_laps


def data_pipeline(path=None, left_path=None, right_path=None):
    """
    Complete data pipeline:
        - load data
        - filter for Melbourne laps
        - slice track coordinates
        - re-index the data
        - enforce track limits
        - remove laps with insufficient data
    """
    df = read_data(path)
    logger.info("Data loaded successfully.")

    df = filter_melbourne(df)
    logger.info("Filtered Melbourne laps.")

    df = track_slice(df)
    logger.info("Sliced track coordinates.")

    df = re_index(df)
    logger.info("Re-indexed data.")

    # Load track limits
    left = read_process_left(left_path)
    right = read_process_right(right_path)
    logger.info("Track limits loaded.")

    # Enforce track limits, to ensure laps wildly off track are removed.
    df = enforce_track_limits(df, left, right)
    logger.info("Enforced track limits.")

    # Remove laps with too few data points.
    df, discarded = remove_short_laps(df)
    logger.info("Removed laps with insufficient data.")
    return df, left, right, discarded
