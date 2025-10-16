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


def basic_features(df):
    """
    Creating a feature that combines the driver's throttle and brake input into
    one variable for convenient visualisation.

    Example usage.

    df = basic_features(df)
    """
    df["M_BRAKE_THROTTLE_1"] = df["M_THROTTLE_1"] - df["M_BRAKE_1"]

    return df
    # TEMPLATE
    """ 
    [FEATURE DESCRIPTION AND PURPOSE]
    """
    # [FEATURE CODE]

def front_wheel_vs_velocity(df):
    """
    Calculates the angle between the **front wheel direction** and the **car's velocity vector**.
    
    Interpretation:
    - Large angles indicate *understeer* or *slippage* (wheels pointing differently than where the car is going).
    - Small angles indicate the car is tracking well along the wheel direction.
    """
    car_forward = np.stack([df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1)
    wheel_angle_rad = np.deg2rad(df["M_FRONTWHEELSANGLE"].values)

    # Rotate car forward vector by wheel steering angle
    fw_x = car_forward[:, 0] * np.cos(wheel_angle_rad) - car_forward[:, 1] * np.sin(wheel_angle_rad)
    fw_y = car_forward[:, 0] * np.sin(wheel_angle_rad) + car_forward[:, 1] * np.cos(wheel_angle_rad)
    fw_vector = np.stack([fw_x, fw_y], axis=1)

    vel_vector = np.stack([df["VEL_X"], df["VEL_Y"]], axis=1)

    norm_fw = np.linalg.norm(fw_vector, axis=1)
    norm_vel = np.linalg.norm(vel_vector, axis=1)

    valid_mask = (norm_fw > 0) & (norm_vel > 0)

    dot = np.zeros(len(df))
    cos_theta = np.zeros(len(df))

    dot[valid_mask] = np.einsum('ij,ij->i', fw_vector[valid_mask], vel_vector[valid_mask])
    cos_theta[valid_mask] = np.clip(dot[valid_mask] / (norm_fw[valid_mask] * norm_vel[valid_mask]), -1, 1)

    df["angle_fw_vs_vel"] = np.full(len(df), np.nan)
    df.loc[valid_mask, "angle_fw_vs_vel"] = np.rad2deg(np.arccos(cos_theta[valid_mask]))

    # Correct to get deviation (e.g., 180° → 0°)
    df["angle_fw_vs_vel"] = 180 - df["angle_fw_vs_vel"]

    return df


def car_direction_vs_velocity(df):
    """
    Calculates the angle between the **car's facing direction** and its **velocity vector**.
    
    Interpretation:
    - High angles (after correction) indicate *drifting*, *oversteer*, or *sliding*.
    - Ideally small during stable turns (car moving roughly where it’s facing).
    """
    car_forward = np.stack([df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1)
    vel_vector = np.stack([df["VEL_X"], df["VEL_Y"]], axis=1)

    norm_forward = np.linalg.norm(car_forward, axis=1)
    norm_vel = np.linalg.norm(vel_vector, axis=1)

    valid_mask = (norm_forward > 0) & (norm_vel > 0)

    dot = np.zeros(len(df))
    cos_theta = np.zeros(len(df))

    dot[valid_mask] = np.einsum('ij,ij->i', car_forward[valid_mask], vel_vector[valid_mask])
    cos_theta[valid_mask] = np.clip(dot[valid_mask] / (norm_forward[valid_mask] * norm_vel[valid_mask]), -1, 1)

    df["angle_car_vs_vel"] = np.full(len(df), np.nan)
    df.loc[valid_mask, "angle_car_vs_vel"] = np.rad2deg(np.arccos(cos_theta[valid_mask]))

    # Correct to get deviation (e.g., 180° → 0°)
    df["angle_car_vs_vel"] = 180 - df["angle_car_vs_vel"]

    return df


def front_wheel_vs_car_direction(df):
    """
    Calculates the angle between the **front wheel direction** and the **car's facing direction**.
    
    Interpretation:
    - Reflects the *steering input* directly.
    - Large angles → strong steering correction (possibly entering or exiting a turn).
    - Useful for measuring steering aggressiveness or response.
    """
    car_forward = np.stack([df["M_WORLDFORWARDDIRX_1"], df["M_WORLDFORWARDDIRY_1"]], axis=1)
    wheel_angle_rad = np.deg2rad(df["M_FRONTWHEELSANGLE"].values)

    # Rotate car forward vector by front wheel angle
    fw_x = car_forward[:, 0] * np.cos(wheel_angle_rad) - car_forward[:, 1] * np.sin(wheel_angle_rad)
    fw_y = car_forward[:, 0] * np.sin(wheel_angle_rad) + car_forward[:, 1] * np.cos(wheel_angle_rad)
    fw_vector = np.stack([fw_x, fw_y], axis=1)

    dot = np.einsum('ij,ij->i', fw_vector, car_forward)
    norm_fw = np.linalg.norm(fw_vector, axis=1)
    norm_forward = np.linalg.norm(car_forward, axis=1)
    cos_theta = np.clip(dot / (norm_fw * norm_forward), -1, 1)

    df["angle_fw_vs_car"] = np.rad2deg(np.arccos(cos_theta))

    # Small correction to keep everything within 0–90 range
    df["angle_fw_vs_car"] = np.where(df["angle_fw_vs_car"] > 90, 180 - df["angle_fw_vs_car"], df["angle_fw_vs_car"])

    return df
