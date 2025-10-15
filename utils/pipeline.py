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


def remove_na(df):
    return df.dropna(subset=["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]).reset_index(
        drop=True
    )


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


def track_slice(df):
    df = df[
        (df["M_WORLDPOSITIONX_1"] >= 0)
        & (df["M_WORLDPOSITIONX_1"] <= 600)
        & (df["M_WORLDPOSITIONY_1"] >= -200)
        & (df["M_WORLDPOSITIONY_1"] <= 600)
    ]

    track_points = np.array(
        [
            [152.5310179012927, 413.5544859306186],
            [161.76398481864388, 423.11538718965284],
            [572, 423],
            [572.051098447852, -131.86683911251717],
            [564.8183173166642, -138.23284559314058],
            [152, -138],
        ],
        float,
    )

    polygon = Polygon(track_points)

    mask = df.apply(
        lambda row: polygon.contains(
            Point(row["M_WORLDPOSITIONX_1"], row["M_WORLDPOSITIONY_1"])
        ),
        axis=1,
    )

    return df[mask]


def remove_repeated_point_laps(df, max_repeats=10):
    """
    Remove laps that have any (X, Y) point repeated more than max_repeats times.
    """
    # Count occurrences of each (x, y) per lap
    repeated_counts = (
        df.groupby(["lap_index", "M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"])
        .size()
        .reset_index(name="count")
    )

    # Laps to discard
    discard_laps = repeated_counts[repeated_counts["count"] > max_repeats][
        "lap_index"
    ].unique()

    # Filter out those laps
    df_clean = df[~df["lap_index"].isin(discard_laps)]

    return df_clean


def read_process_left(path=None):
    """Load and restrict the left track limits to expected coordinate bounds."""
    if path:
        left = pd.read_csv(f"{path}")
    else:
        left = pd.read_csv("data/f1sim-ref-left.csv")

    # Restrict to the same bounds as track_slice
    left = left[
        (left["WORLDPOSX"] >= 120)
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
        (right["WORLDPOSX"] >= 120)
        & (right["WORLDPOSX"] <= 600)
        & (right["WORLDPOSY"] >= -200)
        & (right["WORLDPOSY"] <= 600)
    ]

    return right


def interpolate_steering(df):
    df["M_FRONTWHEELSANGLE"] = (
        df.groupby(["lap_index"])["M_FRONTWHEELSANGLE"]
        .transform(lambda g: g.interpolate(method="linear"))
        .ffill()
        .bfill()
    )

    return df


def enforce_track_limits(df, left, right):
    """Remove laps where any telemetry point exceeds a given distance from track edges."""
    threshold = 5
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

    offtrack_laps = df[df["dist_to_track"] > threshold][["lap_index"]].drop_duplicates()

    df = df.merge(offtrack_laps, on=["lap_index"], how="left", indicator=True)
    df = df[df["_merge"] == "left_only"].drop(
        columns=["_merge", "inside_track", "dist_to_track"]
    )

    return df


def remove_short_laps(df, min_points=700):
    """Remove laps that have fewer than min_points telemetry points."""
    # Count points per lap
    lap_counts = df.groupby("lap_index").size().reset_index(name="n_points")

    # Keep only laps with enough points
    valid_laps = lap_counts[lap_counts["n_points"] >= min_points]["lap_index"]

    df = df[df["lap_index"].isin(valid_laps)]
    return df


def compute_turning_window(df):
    # Apex coordinates
    t1_apex = (375.57, 191.519)
    t2_apex = (368.93, 90)
    turn_radius = 50  # meters

    # Compute distance to each apex
    df["dist_to_t1_apex"] = np.sqrt(
        (df["M_WORLDPOSITIONX_1"] - t1_apex[0]) ** 2
        + (df["M_WORLDPOSITIONY_1"] - t1_apex[1]) ** 2
    )

    df["dist_to_t2_apex"] = np.sqrt(
        (df["M_WORLDPOSITIONX_1"] - t2_apex[0]) ** 2
        + (df["M_WORLDPOSITIONY_1"] - t2_apex[1]) ** 2
    )

    # Binary columns indicating if point is inside turning window
    df["is_t1_window"] = df["dist_to_t1_apex"] <= turn_radius
    df["is_t2_window"] = df["dist_to_t2_apex"] <= turn_radius
    return df


def initialise_lap_summary(df):
    """
    Create a summary dataframe per lap with lap index and sector_time.
    sector_time is computed as the difference between the first and last CURRENTLAPTIME in seconds.
    """

    def time_to_seconds(t):
        """Convert 'M:SS.sss' string to seconds."""
        mins, secs = t.split(":")
        return float(mins) * 60 + float(secs)

    summary_rows = []

    for lap_idx in df["lap_index"].unique():
        lap = df[df["lap_index"] == lap_idx].sort_values("M_LAPDISTANCE_1")
        start_time = time_to_seconds(lap.iloc[0]["CURRENTLAPTIME"])
        end_time = time_to_seconds(lap.iloc[-1]["CURRENTLAPTIME"])
        sector_time = end_time - start_time
        summary_rows.append({"index": lap_idx, "sector_time": sector_time})

    summary_df = pd.DataFrame(summary_rows)
    return summary_df


def remove_redundant_cols(df):
    """
    REDUNDANT VARIABLES: Removes session metadata, duplicates, and irrelevant columns that are either
    redundant, empty, or not needed for modeling/analysis, leaving only clean and relevant features.
    """
    red_cols = [
        "CREATED_ON",
        "GAMEHOST",
        "DEVICENAME",
        "SESSION_GUID",
        "R_SESSION",
        "R_GAMEHOST",
        "M_PACKETFORMAT",
        "M_GAMEMAJORVERSION",
        "M_GAMEMINORVERSION",
        "M_FRAMEIDENTIFIER",
        "R_STATUS",
        "M_CURRENTLAPNUM_1",
        "M_TRACKID",
        "R_TRACKID",
        "M_LAPINVALID",
        "M_SECTOR1TIMEMSPART_1",
        "M_SECTOR1TIMEMINUTESPART_1",
        "M_SECTOR2TIMEMSPART_1",
        "M_SECTOR2TIMEMINUTESPART_1",
        "M_SECTOR_1",
        "M_CURRENTLAPINVALID_1",
        "M_DRIVERSTATUS_1",
        "FRAMEID",
        "M_TOTALLAPS",
        "M_SESSIONTYPE",
        "R_FAV_TEAM",
        "M_TYRESSURFACETEMPERATURE_RL_1",
        "M_TYRESSURFACETEMPERATURE_RR_1",
        "M_TYRESSURFACETEMPERATURE_FL_1",
        "M_TYRESSURFACETEMPERATURE_FR_1",
        "M_TYRESINNERTEMPERATURE_RL_1",
        "M_TYRESINNERTEMPERATURE_RR_1",
        "M_TYRESINNERTEMPERATURE_FL_1",
        "M_TYRESINNERTEMPERATURE_FR_1",
        "M_ENGINETEMPERATURE_1",
    ]

    df = df.drop(columns=red_cols)

    return df


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

    # Removes laps from trakcs that are not melbourne
    df = filter_melbourne(df)
    logger.info("Filtered Melbourne laps.")

    # Removes rows with NA (X,Y) coordinates
    df = remove_na(df)
    logger.info("Removed data points with missing (x,y)")

    # Re-index the laps for easier access
    df = re_index(df)
    logger.info("Re-indexed data.")

    # Removing uselss/redundant columns from the data
    df = remove_redundant_cols(df)
    logger.info("Removed redundant columns")
    # Slice the track data to be between selected track start and finish lines for this sector
    df = track_slice(df)
    logger.info("Sliced track coordinates.")

    # Load track limits
    left = read_process_left(left_path)
    right = read_process_right(right_path)
    logger.info("Track limits loaded.")

    # Enforce track limits, to ensure laps wildly off track are removed.
    df = enforce_track_limits(df, left, right)
    logger.info("Enforced track limits.")

    # Remove laps with too few data points.
    df = remove_short_laps(df)
    logger.info("Removed laps with insufficient data.")

    # Compute turning window metrics
    df = compute_turning_window(df)
    logger.info("Computed turning window metrics")

    df = interpolate_steering(df)
    logger.info("Interpolating steering data")

    # Creates a summary df with index and sector_time as columns
    summary_df = initialise_lap_summary(df)
    logger.info("Created sumamry dataframe.")
    return df, left, right, summary_df
