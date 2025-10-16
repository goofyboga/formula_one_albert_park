import pandas as pd
from shapely.geometry import Polygon, Point, LineString
import numpy as np
from .loading import read_process_left, read_process_right
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def spatial(df):
    # Slice the track data to be between selected track start and finish lines for this sector
    df = track_slice(df)
    logger.info("Sliced track coordinates.")

    # Load track limits
    left = read_process_left()
    right = read_process_right()
    logger.info("Track limits loaded.")

    # Enforce track limits, to ensure laps wildly off track are removed.
    df = enforce_track_limits(df, left, right)
    logger.info("Enforced track limits.")

    return df, left, right


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
