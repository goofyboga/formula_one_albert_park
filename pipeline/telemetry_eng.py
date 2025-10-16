import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import logging
from .loading import read_process_line

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def telemetry_eng(df):
    # Compute turning window metrics.
    df = compute_turning_window(df)
    logger.info("Computed turning window metrics.")

    # Interpolates steering angle where possible.
    df = interpolate_wheel_angle(df)
    logger.info("Interpolating steering data.")

    # Load racing line.
    line = read_process_line()
    logger.info("Racing line loaded.")

    # Finding deviation from racing line at each point.
    df = racing_line_deviation(df, line)
    logger.info("Calculated deviation from racing line.")

    # Creates a combined brake–throttle feature for easier driver input analysis.
    df = brake_throttle(df)
    logger.info("Created combined brake–throttle variable.")

    # Defines the turning window around each apex (T1 and T2) using distance thresholds.
    df = compute_turning_window(df)
    logger.info("Computed turning window around each apex.")

    # Computes velocity and g-force.
    df = recompute_velocity_and_gforce(df)
    logger.info("Computed velocity and g-force.")

    # Calculates the angle between the front wheel direction and velocity vector.
    # Helps measure understeer or wheel slip.
    df = front_wheel_vs_velocity(df)
    logger.info("Calculated front wheel vs velocity angle.")

    # Calculates the angle between the car's facing direction and its velocity vector.
    # Helps measure drift, slide, or oversteer.
    df = car_direction_vs_velocity(df)
    logger.info("Calculated car direction vs velocity angle.")

    # Calculates the angle between the front wheel direction and the car's facing direction.
    # Helps measure steering aggression and driver responsiveness.
    df = front_wheel_vs_car_direction(df)
    logger.info("Calculated front wheel vs car direction angle.")

    return df, line


def interpolate_wheel_angle(df):
    df["M_FRONTWHEELSANGLE"] = (
        df.groupby(["lap_index"])["M_FRONTWHEELSANGLE"]
        .transform(lambda g: g.interpolate(method="linear"))
        .ffill()
        .bfill()
    )

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


def racing_line_deviation(df, line):
    line_points = line[["WORLDPOSX", "WORLDPOSY"]].to_numpy()
    tree = cKDTree(line_points)

    driver_points = df[["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]].to_numpy()
    distances, _ = tree.query(driver_points)

    df["line_distance"] = distances
    return df


def brake_throttle(df):
    """
    Creating a feature that combines the driver's throttle and brake input into
    one variable for convenient visualisation.
    """
    df["M_BRAKE_THROTTLE_1"] = df["M_THROTTLE_1"] - df["M_BRAKE_1"]

    return df


def compute_turning_window(df):
    """
    Defines the *turning window* around each apex (T1 and T2) based on distance thresholds.

    This function computes the car's distance from each turn apex and creates binary flags
    that indicate whether the car is within the "turning zone" (a circular region around the apex).
    """
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


def front_wheel_vs_velocity(df):
    """
    Measures understeer or slip.
    Calculates the angle between the **front wheel direction** and the **car's velocity vector**.

    Interpretation:
    - Large angles indicate *understeer* or *slippage* (wheels pointing differently than where the car is going).
    - Small angles indicate the car is tracking well along the wheel direction.
    """
    car_forward = np.stack(
        [df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1
    )
    wheel_angle_rad = np.deg2rad(df["M_FRONTWHEELSANGLE"].values)

    # Rotate car forward vector by wheel steering angle
    fw_x = car_forward[:, 0] * np.cos(wheel_angle_rad) - car_forward[:, 1] * np.sin(
        wheel_angle_rad
    )
    fw_y = car_forward[:, 0] * np.sin(wheel_angle_rad) + car_forward[:, 1] * np.cos(
        wheel_angle_rad
    )
    fw_vector = np.stack([fw_x, fw_y], axis=1)

    vel_vector = np.stack([df["VEL_X"], df["VEL_Y"]], axis=1)

    norm_fw = np.linalg.norm(fw_vector, axis=1)
    norm_vel = np.linalg.norm(vel_vector, axis=1)

    valid_mask = (norm_fw > 0) & (norm_vel > 0)

    dot = np.zeros(len(df))
    cos_theta = np.zeros(len(df))

    dot[valid_mask] = np.einsum(
        "ij,ij->i", fw_vector[valid_mask], vel_vector[valid_mask]
    )
    cos_theta[valid_mask] = np.clip(
        dot[valid_mask] / (norm_fw[valid_mask] * norm_vel[valid_mask]), -1, 1
    )

    df["angle_fw_vs_vel"] = np.full(len(df), np.nan)
    df.loc[valid_mask, "angle_fw_vs_vel"] = np.rad2deg(np.arccos(cos_theta[valid_mask]))

    # Correct to get deviation (e.g., 180° → 0°)
    df["angle_fw_vs_vel"] = 180 - df["angle_fw_vs_vel"]

    return df


def car_direction_vs_velocity(df):
    """
    Measures oversteer, drift and slide.
    Calculates the angle between the **car's facing direction** and its **velocity vector**.

    Interpretation:
    - High angles (after correction) indicate *drifting*, *oversteer*, or *sliding*.
    - Ideally small during stable turns (car moving roughly where it’s facing).
    """
    car_forward = np.stack(
        [df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1
    )
    vel_vector = np.stack([df["VEL_X"], df["VEL_Y"]], axis=1)

    norm_forward = np.linalg.norm(car_forward, axis=1)
    norm_vel = np.linalg.norm(vel_vector, axis=1)

    valid_mask = (norm_forward > 0) & (norm_vel > 0)

    dot = np.zeros(len(df))
    cos_theta = np.zeros(len(df))

    dot[valid_mask] = np.einsum(
        "ij,ij->i", car_forward[valid_mask], vel_vector[valid_mask]
    )
    cos_theta[valid_mask] = np.clip(
        dot[valid_mask] / (norm_forward[valid_mask] * norm_vel[valid_mask]), -1, 1
    )

    df["angle_car_vs_vel"] = np.full(len(df), np.nan)
    df.loc[valid_mask, "angle_car_vs_vel"] = np.rad2deg(
        np.arccos(cos_theta[valid_mask])
    )

    # Correct to get deviation (e.g., 180° → 0°)
    df["angle_car_vs_vel"] = 180 - df["angle_car_vs_vel"]

    return df


def front_wheel_vs_car_direction(df):
    """
    Measures steering aggression and responsiveness.
    Calculates the angle between the **front wheel direction** and the **car's facing direction**.

    Interpretation:
    - Reflects the *steering input* directly.
    - Large angles → strong steering correction (possibly entering or exiting a turn).
    - Useful for measuring steering aggressiveness or response.
    """
    car_forward = np.stack(
        [df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1
    )
    wheel_angle_rad = np.deg2rad(df["M_FRONTWHEELSANGLE"].values)

    # Rotate car forward vector by front wheel angle
    fw_x = car_forward[:, 0] * np.cos(wheel_angle_rad) - car_forward[:, 1] * np.sin(
        wheel_angle_rad
    )
    fw_y = car_forward[:, 0] * np.sin(wheel_angle_rad) + car_forward[:, 1] * np.cos(
        wheel_angle_rad
    )
    fw_vector = np.stack([fw_x, fw_y], axis=1)

    dot = np.einsum("ij,ij->i", fw_vector, car_forward)
    norm_fw = np.linalg.norm(fw_vector, axis=1)
    norm_forward = np.linalg.norm(car_forward, axis=1)
    cos_theta = np.clip(dot / (norm_fw * norm_forward), -1, 1)

    df["angle_fw_vs_car"] = np.rad2deg(np.arccos(cos_theta))

    # Small correction to keep everything within 0–90 range
    df["angle_fw_vs_car"] = np.where(
        df["angle_fw_vs_car"] > 90, 180 - df["angle_fw_vs_car"], df["angle_fw_vs_car"]
    )

    return df


def recompute_velocity_and_gforce(df):
    """
    Recomputes directional velocity and G-force features from positional data and timestamps.
    Handles missing values, clips unrealistic outliers, and applies interpolation smoothing.
    Also smooths front wheel angle readings.

    Steps:
    1. Drops existing velocity and G-force columns (to fully recompute them).
    2. Recomputes velocity (m/s) per lap using position deltas over time.
    3. Recomputes acceleration and converts to G-force.
    4. Clips unrealistic values (>7 Gs or >100 m/s) and interpolates within laps.
    """

    # Drop old velocity and G-force columns
    df = df.drop(
        columns=[
            "M_WORLDVELOCITYX_1",
            "M_WORLDVELOCITYY_1",
            "M_WORLDVELOCITYZ_1",
            "M_GFORCELATERAL_1",
            "M_GFORCELONGITUDINAL_1",
            "M_GFORCEVERTICAL_1",
        ],
        errors="ignore",  # In case some columns are missing
    )

    # --- Velocity ---
    for axis in ["X", "Y", "Z"]:
        df[f"VEL_{axis}"] = (
            df.groupby("lap_index")[f"M_WORLDPOSITION{axis}_1"].diff()
            / df.groupby("lap_index")["M_CURRENTLAPTIMEINMS_1"].diff()
        )
        df[f"VEL_{axis}"] *= 1000  # Convert to m/s
        df[f"VEL_{axis}"] = df[f"VEL_{axis}"].fillna(0)

    # Clip extreme velocity outliers (~100 m/s max for F1 car)
    df["VEL_X"] = df["VEL_X"].clip(-100, 100)
    df["VEL_Y"] = df["VEL_Y"].clip(-100, 100)
    df["VEL_Z"] = df["VEL_Z"].clip(-100, 100)

    # --- G-force ---
    for axis in ["X", "Y", "Z"]:
        df[f"GFORCE_{axis}"] = (
            df.groupby("lap_index")[f"VEL_{axis}"].diff()
            / df.groupby("lap_index")["M_CURRENTLAPTIMEINMS_1"].diff()
        )
        df[f"GFORCE_{axis}"] *= 1000  # Convert to m/s²
        df[f"GFORCE_{axis}"] /= 9.8  # Convert to Gs
        df[f"GFORCE_{axis}"] = df[f"GFORCE_{axis}"].fillna(0)

        # Mask unrealistic extremes (>7 Gs)
        df.loc[
            (df[f"GFORCE_{axis}"] > 7) | (df[f"GFORCE_{axis}"] < -7),
            f"GFORCE_{axis}",
        ] = np.nan

        # Interpolate linearly per lap and fill remaining NaNs
        df[f"GFORCE_{axis}"] = df.groupby("lap_index")[f"GFORCE_{axis}"].transform(
            lambda g: g.interpolate(method="linear").ffill().bfill()
        )

    return df


def recompute_velocity_and_gforce(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recomputes directional velocity and G-force features from positional data
    and timestamps, handles missing values, clips unrealistic outliers, and
    applies interpolation. Also smooths front wheel angle readings.
    """

    df = df.copy()

    # Drop any existing velocity / G-force columns
    drop_cols = [
        "M_WORLDVELOCITYX_1",
        "M_WORLDVELOCITYY_1",
        "M_WORLDVELOCITYZ_1",
        "M_GFORCELATERAL_1",
        "M_GFORCELONGITUDINAL_1",
        "M_GFORCEVERTICAL_1",
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # --- Velocity computation ---
    for axis in ["X", "Y", "Z"]:
        df[f"VEL_{axis}"] = (
            df.groupby("lap_index")[f"M_WORLDPOSITION{axis}_1"].diff()
            / df.groupby("lap_index")["M_CURRENTLAPTIMEINMS_1"].diff()
        )
        df[f"VEL_{axis}"] *= 1000  # convert from ms to s
        df[f"VEL_{axis}"] = df[f"VEL_{axis}"].fillna(0)
        df[f"VEL_{axis}"] = df[f"VEL_{axis}"].clip(-100, 100)

    # --- G-force computation ---
    for axis in ["X", "Y", "Z"]:
        df[f"GFORCE_{axis}"] = (
            df.groupby("lap_index")[f"VEL_{axis}"].diff()
            / df.groupby("lap_index")["M_CURRENTLAPTIMEINMS_1"].diff()
        )
        df[f"GFORCE_{axis}"] *= 1000  # convert from ms to s
        df[f"GFORCE_{axis}"] /= 9.8  # convert to Gs
        df[f"GFORCE_{axis}"] = df[f"GFORCE_{axis}"].fillna(0)

        # Mask unrealistic extremes (outside ±7 Gs)
        df.loc[
            (df[f"GFORCE_{axis}"] > 7) | (df[f"GFORCE_{axis}"] < -7), f"GFORCE_{axis}"
        ] = np.nan

        # Interpolate per lap
        df[f"GFORCE_{axis}"] = df.groupby("lap_index")[f"GFORCE_{axis}"].transform(
            lambda g: g.interpolate(method="linear").ffill().bfill()
        )

    return df
