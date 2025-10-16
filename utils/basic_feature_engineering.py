import pandas as pd
import numpy as np


def optimize_target_variable(df):
    """
    Optimizing the target variable by cutting off outliers, before using a log
    transformation to treat heteroscadasticity and imbalance. Highly recommend
    during modelling to use quantile regression strategies to deal with the heavy
    left skew of the target variable.

    Example Usage: f1_cleaned_df = optimize_target_variable(f1_cleaned_df)
    """
    optdf = df[
        df["exit_T2_speed"] >= 175
    ]  # Clear outliers (invalid or non consequential speed)
    optdf["exit_T2_speed_log"] = np.log(
        optdf["exit_T2_speed"]
    )  # Reduce target variable imbalance
    return optdf


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


def compute_brake_balance(df):
    """
    Computes advanced brake temperature balance metrics.
        - brake_front_rear_diff: Avg(front) - Avg(rear)
            Indicates brake bias. Positive = front-biased (risk of understeer),
            Negative = rear-biased (risk of oversteer).

        - brake_left_right_diff: Avg(left) - Avg(right)
            Indicates lateral braking imbalance. Positive = left brakes hotter
            (often due to more right-hand cornering or uneven braking effort).
    """
    # Front vs rear average
    df["brake_front_avg"] = (
        df["M_BRAKESTEMPERATURE_FL_1"] + df["M_BRAKESTEMPERATURE_FR_1"]
    ) / 2
    df["brake_rear_avg"] = (
        df["M_BRAKESTEMPERATURE_RL_1"] + df["M_BRAKESTEMPERATURE_RR_1"]
    ) / 2
    df["brake_front_rear_diff"] = df["brake_front_avg"] - df["brake_rear_avg"]

    # Left vs right average
    df["brake_left_avg"] = (
        df["M_BRAKESTEMPERATURE_FL_1"] + df["M_BRAKESTEMPERATURE_RL_1"]
    ) / 2
    df["brake_right_avg"] = (
        df["M_BRAKESTEMPERATURE_FR_1"] + df["M_BRAKESTEMPERATURE_RR_1"]
    ) / 2
    df["brake_left_right_diff"] = df["brake_left_avg"] - df["brake_right_avg"]

    df.drop(
        columns=[
            "brake_front_avg",
            "brake_rear_avg",
            "brake_left_avg",
            "brake_right_avg",
        ],
        inplace=True,
    )

    return df


