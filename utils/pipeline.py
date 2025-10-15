import pandas as pd
import logging
from shapely.geometry import Polygon, Point
import numpy as np
from scipy.spatial import cKDTree

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


def read_process_line(path=None):
    """Load and restrict the right track limits to expected coordinate bounds."""
    if path:
        line = pd.read_csv(f"{path}")
    else:
        line = pd.read_csv("data/f1sim-ref-line.csv")

    # Restrict to the same bounds as track_slice
    line = line[
        (line["WORLDPOSX"] >= 120)
        & (line["WORLDPOSX"] <= 600)
        & (line["WORLDPOSY"] >= -200)
        & (line["WORLDPOSY"] <= 600)
    ]

    line = line.sort_values("FRAME")
    return line


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


def remove_stuttery_laps(df, min_points=500):
    # Drop duplicate positions within each lap
    df_unique = df.drop_duplicates(
        subset=["lap_index", "M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]
    )

    # Count distinct points per lap
    lap_counts = df_unique.groupby("lap_index").size().reset_index(name="n_points")

    # Keep only laps with enough distinct points
    valid_laps = lap_counts[lap_counts["n_points"] >= min_points]["lap_index"]
    df_clean = df[df["lap_index"].isin(valid_laps)]

    return df_clean


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
        summary_rows.append({"lap_index": lap_idx, "sector_time": sector_time})

    summary = pd.DataFrame(summary_rows)
    return summary

def find_nearest_point(df_ref, x, y):
    """
    Finds the index of the point in df_ref closest to the given (x, y) coordinate.
    """
    # Compute the Euclidean distance between each point and the reference point (x, y)
    diffs = np.sqrt((df_ref["WORLDPOSX"] - x) ** 2 + (df_ref["WORLDPOSY"] - y) ** 2)

    # Get the index of the point with the minimum distance
    idx_nearest = diffs.idxmin()

    return idx_nearest


def define_cut_line(df_right, df_left, x, y):
    """
    Defines a perpendicular line ("cut line") across the track between the right and left boundaries.
    The line starts at the nearest point on the right boundary to (x, y) and extends perpendicularly
    toward the left boundary, finding the nearest point on the left boundary to complete the line.
    
    start_line = define_cut_line(right, left, x=152.5310179012927, y=413.5544859306186)
    end_line   = define_cut_line(right, left,  x=564.8183173166642, y=-138.23284559314058)
    """
    # Sort both left and right boundaries by frame to ensure sequential order
    df_right = df_right.sort_values(by="FRAME", ascending=True).reset_index(drop=True)
    df_left = df_left.sort_values(by="FRAME", ascending=True).reset_index(drop=True)

    # Find the index of the nearest point on the right boundary to the given (x, y)
    right_idx = find_nearest_point(df_right, x, y)

    # Retrieve the current and next points on the right boundary to estimate local direction
    current_row = df_right.iloc[right_idx]
    next_row = df_right.iloc[right_idx + 1]

    # Compute direction vector along the right boundary
    direction_vector_x = next_row["WORLDPOSX"] - current_row["WORLDPOSX"]
    direction_vector_y = next_row["WORLDPOSY"] - current_row["WORLDPOSY"]

    # Compute perpendicular vector (normal to the right boundary)
    perpendicular_vector_x = -direction_vector_y
    perpendicular_vector_y = direction_vector_x

    # Normalize the perpendicular vector to unit length
    norm = np.sqrt(perpendicular_vector_x**2 + perpendicular_vector_y**2)
    perpendicular_vector_x = perpendicular_vector_x / norm
    perpendicular_vector_y = perpendicular_vector_y / norm

    # Extend the perpendicular vector from the right boundary toward the left boundary
    right_len = 20  # Approximate track width (in meters)
    x2 = x + perpendicular_vector_x * right_len
    y2 = y + perpendicular_vector_y * right_len

    # Find the nearest point on the left boundary corresponding to the projected left-side location
    left_idx = find_nearest_point(df_left, x2, y2)
    left_x = float(df_left.iloc[left_idx]["WORLDPOSX"])
    left_y = float(df_left.iloc[left_idx]["WORLDPOSY"])

    cut_line = LineString([(float(x), float(y)), (left_x, left_y)])

    print("Cut line:")
    print(cut_line)
    print(f"Right border coordinate: ({float(x):.3f}, {float(y):.3f})")
    print(f"Left border coordinate:  ({left_x:.3f}, {left_y:.3f})")

    return cut_line, (float(x), float(y)), (left_x, float(left_y))


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


def racing_line_deviation(df, line):
    line_points = line[["WORLDPOSX", "WORLDPOSY"]].to_numpy()
    tree = cKDTree(line_points)

    driver_points = df[["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]].to_numpy()
    distances, _ = tree.query(driver_points)

    df["line_distance"] = distances
    return df


def avg_line_distance(df, summary):
    """
    Calculate the average distance from the racing line per lap
    and add it to the summary dataframe.
    """
    avg_dist = df.groupby("lap_index")["line_distance"].mean().reset_index()
    avg_dist.rename(columns={"line_distance": "avg_line_distance"}, inplace=True)

    summary = summary.merge(avg_dist, on="lap_index", how="left")
    return summary


def min_apex_distance(df, summary):
    p1 = (375.57, 191.519)
    p2 = (368.93, 90.0)
    rows = []
    for i in df["lap_index"].unique():
        lap = df[df["lap_index"] == i]
        lap_points = lap[["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]].to_numpy()
        tree = cKDTree(lap_points)
        distance1, _ = tree.query((p1[0], p1[1]))
        distance2, _ = tree.query((p2[0], p2[1]))
        rows.append((i, distance1, distance2))

    distances = pd.DataFrame(
        rows, columns=["lap_index", "dist_to_apex1", "dist_to_apex2"]
    )
    summary = pd.merge(summary, distances, on="lap_index", how="inner")

    return summary


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
    logger.info("Data loaded.")

    # Removes laps from trakcs that are not melbourne
    df = filter_melbourne(df)
    logger.info("Filtered Melbourne laps.")

    # Removes rows with NA (X,Y) coordinates
    df = remove_na(df)
    logger.info("Removed data points with missing x or y co-ordinates.")

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
    df = remove_stuttery_laps(df)
    logger.info("Removed laps with insufficient data.")

    # Compute turning window metrics.
    df = compute_turning_window(df)
    logger.info("Computed turning window metrics.")

    # Interpolates steering angle where possible.
    df = interpolate_steering(df)
    logger.info("Interpolating steering data.")

    # Load racing line.
    line = read_process_line()
    logger.info("Racing line loaded.")

    # Finding deviation from racing line at each point.
    df = racing_line_deviation(df, line)
    logger.info("Calculated deviation from racing line.")

    # Creates a summary df with index and sector_time as columns.
    summary = initialise_lap_summary(df)
    logger.info("Created summary dataframe.")

    # Calculates the average deviation from the racing line.
    summary = avg_line_distance(df, summary)
    logger.info("Calculated average distance to racing line.")

    # Calculates the minimum distances to either apex.
    summary = min_apex_distance(df, summary)
    logger.info("Calculated minimum distance to apex 1 and 2.")

    return df, left, right, line, summary
