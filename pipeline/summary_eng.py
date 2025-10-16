import pandas as pd
from scipy.spatial import cKDTree
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def summary_eng(df):
    # Creates the summary dataframe containing lap-level statistics.
    summary = initialise_lap_summary(df)
    logger.info("Created summary dataframe.")

    # Calculates the average deviation from the racing line.
    summary = avg_line_distance(df, summary)
    logger.info("Calculated average distance to racing line.")

    # Calculates the minimum distances to either apex.
    summary = min_apex_distance(df, summary)
    logger.info("Calculated minimum distance to apex 1 and 2.")

    # Calculating average brake and throttle pressure.
    summary = add_avg_brake_pressure(df, summary)
    summary = add_avg_throttle_pressure(df, summary)
    logger.info("Calculated average brake and throttle pressure per lap.")

    # Calculating max brake and throttle pressure.
    summary = add_peak_brake_pressure(df, summary)
    summary = add_peak_throttle_pressure(df, summary)
    logger.info("Calculated peak brake and throttle pressure per lap.")

    # Calculating brake and turning points.
    summary = first_braking_point(df, summary)
    summary = first_turning_point(df, summary)
    logger.info("Braking and turning points calculated.")

    return df, summary


def initialise_lap_summary(df):
    """
    Create a summary dataframe per lap with lap index and sector_time.
    sector_time is computed as the difference between the first and last CURRENTLAPTIME in seconds.
    """

    def time_to_seconds(t):
        """Convert 'M:SS.sss' string to seconds."""
        mins, secs = t.split(":")
        return float(mins) * 60 + float(secs)

    rows = []

    for i in df["lap_index"].unique():
        lap = df[df["lap_index"] == i].sort_values("M_LAPDISTANCE_1")
        start_time = time_to_seconds(lap.iloc[0]["CURRENTLAPTIME"])
        end_time = time_to_seconds(lap.iloc[-1]["CURRENTLAPTIME"])
        sector_time = end_time - start_time
        rows.append({"lap_index": i, "sector_time": sector_time})

    summary = pd.DataFrame(rows)
    return summary


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


def add_avg_brake_pressure(df, summary):
    avg = (
        df.groupby("lap_index")["M_BRAKE_1"]
        .mean()
        .reset_index(name="avg_brake_pressure")
    )
    summary = summary.merge(avg, on="lap_index", how="left")
    return summary


def add_avg_throttle_pressure(df, summary):
    avg = (
        df.groupby("lap_index")["M_THROTTLE_1"]
        .mean()
        .reset_index(name="avg_throttle_pressure")
    )
    summary = summary.merge(avg, on="lap_index", how="left")
    return summary


def add_peak_brake_pressure(df, summary):
    peak = (
        df.groupby("lap_index")["M_BRAKE_1"]
        .max()
        .reset_index(name="peak_brake_pressure")
    )
    summary = summary.merge(peak, on="lap_index", how="left")
    return summary


def add_peak_throttle_pressure(df, summary):
    peak = (
        df.groupby("lap_index")["M_THROTTLE_1"]
        .max()
        .reset_index(name="peak_throttle_pressure")
    )
    summary = summary.merge(peak, on="lap_index", how="left")
    return summary


def first_braking_point(df, summary, brake_thresh=0.2):
    rows = []
    for i in df["lap_index"].unique():
        lap = df[df["lap_index"] == i]
        braking_points = lap[lap["M_BRAKE_1"] > brake_thresh]
        if not braking_points.empty:
            first_brake = braking_points.iloc[0]
            rows.append(
                (
                    i,
                    first_brake["M_WORLDPOSITIONX_1"],
                    first_brake["M_WORLDPOSITIONY_1"],
                    first_brake["M_BRAKE_1"],
                )
            )
        else:
            rows.append((i, None, None, 0))

    brake_df = pd.DataFrame(
        rows, columns=["lap_index", "brake_x", "brake_y", "brake_pressure"]
    )
    summary = pd.merge(summary, brake_df, on="lap_index", how="left")
    return summary


def first_turning_point(df, summary, turn_thresh=0.2):
    rows = []
    for i in df["lap_index"].unique():
        lap = df[df["lap_index"] == i]
        turning_points = lap[lap["M_STEER_1"].abs() > turn_thresh]
        if not turning_points.empty:
            first_turn = turning_points.iloc[0]
            rows.append(
                (
                    i,
                    first_turn["M_WORLDPOSITIONX_1"],
                    first_turn["M_WORLDPOSITIONY_1"],
                    first_turn["M_STEER_1"],
                )
            )
        else:
            rows.append((i, None, None, 0))

    turn_df = pd.DataFrame(
        rows, columns=["lap_index", "turn_x", "turn_y", "steering_angle"]
    )
    summary = pd.merge(summary, turn_df, on="lap_index", how="left")
    return summary
