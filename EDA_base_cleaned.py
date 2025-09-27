import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

"""
Steps:
    - Filters valid laps, sessions, and turns
    - Sorts by current time within a lap per session
    - Creates target variable (exit speed of Turn 2)
    - Recomputes velocity and G-force features
    - Handles missing values with interpolation
    - Removes redundant/duplicate columns
"""
def preprocess_f1_data(f1_main_df):
    """ 
    Defines a helper function plot_track_rotated that rotates track position coordinates by a 
    specified angle and plots them. Useful for visualizing the circuit with corrected orientation.

    Example Usage: plot_track_rotated(f1_main_df, angle_deg=135)
    """
    def plot_track_rotated(df, x_col="M_WORLDPOSITIONX_1", y_col="M_WORLDPOSITIONY_1", angle_deg=0):
        # Convert angle to radians
        theta = np.radians(angle_deg)
        
        # Original coordinates
        x = df[x_col].values
        y = df[y_col].values
        
        # Rotate
        x_rot = x * np.cos(theta) + y * np.sin(theta)
        y_rot = -x * np.sin(theta) + y * np.cos(theta)
        
        # Plot
        plt.figure(figsize=(10, 8))
        plt.scatter(x_rot, y_rot, s=2, alpha=0.6, c="blue")
        plt.xlabel(f"{x_col} (rotated)")
        plt.ylabel(f"{y_col} (rotated)")
        plt.title(f"Car Position Rotated {angle_deg}° Clockwise")
        plt.axis("equal")
        plt.show()

    """
    FILTERS: Applies data quality filters to retain only Melbourne laps, valid laps, valid racing 
    status rows, and realistic sector times. Also restricts data to turns 1 and 2 for focused analysis.
    """
    # Filter for Melbourne track ID only
    melbourne_df = f1_main_df[
        (f1_main_df["M_TRACKID"] == 0) & (f1_main_df["R_TRACKID"] == 0)
    ]

    # Drop invalid laps 
    melbourne_df = melbourne_df[
        (melbourne_df["M_CURRENTLAPINVALID_1"] == 0) & (melbourne_df["M_LAPINVALID"] == 0)
    ]

    # Keep only valid racing status rows
    melbourne_df = melbourne_df[
        (melbourne_df["M_DRIVERSTATUS_1"] == 1) 
    ]

    # Drop NaNs coordinates
    melbourne_df = melbourne_df.dropna(subset=["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1", "M_WORLDPOSITIONZ_1"])

    # Drop negative lap distance
    melbourne_df = melbourne_df[
        (melbourne_df["M_LAPDISTANCE_1"] >= 0)
    ]

    # Limit data to turns 1 and 2 only
    melbourne_df = melbourne_df[melbourne_df["TURN"].isin([1, 2])]

    """
    SORTING: Sorts all rows by the current time within a lap (per session) to ensure chronology
    """
    # Sort each lap per session by time 
    melbourne_df = melbourne_df.sort_values(
        by=["M_SESSIONUID", "M_CURRENTLAPNUM", "M_CURRENTLAPTIMEINMS_1"],
        ascending=True
    )

    '''
    TARGET VARIABLE: Creates a target variable (exit_T2_speed) by capturing the last recorded speed 
    after Turn 2 for each session-lap combination, then merges it back into the main dataframe.
    '''
    ## Add exit speed of Turn 2 as target variable
    t2_df = melbourne_df[melbourne_df["TURN"] == 2]

    # For each session + lap combo, take the exit speed of T2 
    exit_t2 = (
        t2_df.groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])["M_SPEED_1"]
        .last()
        .reset_index(name="exit_T2_speed")
    )

    melbourne_df = melbourne_df.merge(
        exit_t2,
        on=["M_SESSIONUID", "M_CURRENTLAPNUM"],
        how="left"
    )

    """
    MISSING VALUES: Recomputes directional velocity and G-force features from positional data 
    and timestamps, handles missing values, clips unrealistic outliers, and applies interpolation. 
    Also smooths front wheel angle readings.
    """
    # Remake all velocity and G-force columns in m/s
    melbourne_df = melbourne_df.drop(
        columns=[ "M_WORLDVELOCITYX_1", "M_WORLDVELOCITYY_1", "M_WORLDVELOCITYZ_1", 
                "M_GFORCELATERAL_1", "M_GFORCELONGITUDINAL_1", "M_GFORCEVERTICAL_1"]
    )

    # Velocity 
    for axis in ["X", "Y", "Z"]: 
        melbourne_df[f"VEL_{axis}"] = (
            melbourne_df.groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])[f"M_WORLDPOSITION{axis}_1"].diff() /
            melbourne_df.groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])["M_CURRENTLAPTIMEINMS_1"].diff()
        )
        melbourne_df[f"VEL_{axis}"] *= 1000
        # Replace every first row NaN (each lap per session) with zero
        melbourne_df[f"VEL_{axis}"] = melbourne_df[f"VEL_{axis}"].fillna(0)

    # Clip X,Y,Z velocities extreme outliers (~100m/s is realistic top velocity of an F1 car for THIS data)
    melbourne_df["VEL_X"] = melbourne_df["VEL_X"].clip(-100, 100)
    melbourne_df["VEL_Y"] = melbourne_df["VEL_Y"].clip(-100, 100)
    melbourne_df["VEL_Z"] = melbourne_df["VEL_Z"].clip(-100, 100)

    # G-force
    for axis in ["X", "Y", "Z"]: 
        # Acceleration
        melbourne_df[f"GFORCE_{axis}"] = (
            melbourne_df.groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])[f"VEL_{axis}"].diff() /
            melbourne_df.groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])["M_CURRENTLAPTIMEINMS_1"].diff() 
        )
        melbourne_df[f"GFORCE_{axis}"] *= 1000
        # Convert to Gs 
        melbourne_df[f"GFORCE_{axis}"] /= 9.8
        # Replace everry first row NaN with zero
        melbourne_df[f"GFORCE_{axis}"] = melbourne_df[f"GFORCE_{axis}"].fillna(0)

        # Mask unrealistic extremes (Outside of 7Gs)
        melbourne_df.loc[(melbourne_df[f"GFORCE_{axis}"] > 7) | (melbourne_df[f"GFORCE_{axis}"] < -7), f"GFORCE_{axis}"] = np.nan
        # Interpolate linearly per session/lap
        melbourne_df[f"GFORCE_{axis}"] = (
            melbourne_df
            .groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])[f"GFORCE_{axis}"]
            .transform(lambda g: g.interpolate(method="linear"))
            .ffill()
            .bfill()
        )

    # Linear interpolation for the front wheels angle
    melbourne_df["M_FRONTWHEELSANGLE"] = (
        melbourne_df
        .groupby(["M_SESSIONUID", "M_CURRENTLAPNUM"])["M_FRONTWHEELSANGLE"]
        .transform(lambda g: g.interpolate(method="linear")).ffill().bfill()
    )


    """
    REDUNDANT VARIABLES: Removes session metadata, duplicates, and irrelevant columns that are either 
    redundant, empty, or not needed for modeling/analysis, leaving only clean and relevant features.
    """
    red_cols = [
        "CREATED_ON", "GAMEHOST", "DEVICENAME", "SESSION_GUID", "R_SESSION", "R_GAMEHOST",
        "M_PACKETFORMAT", "M_GAMEMAJORVERSION", "M_GAMEMINORVERSION", "M_FRAMEIDENTIFIER", "R_STATUS",
        "M_CURRENTLAPNUM_1", "M_TRACKID", "R_TRACKID", "M_LAPINVALID", "M_SECTOR1TIMEMSPART_1", 
        "M_SECTOR1TIMEMINUTESPART_1", "M_SECTOR2TIMEMSPART_1", "M_SECTOR2TIMEMINUTESPART_1", "M_SECTOR_1",
        "M_CURRENTLAPINVALID_1", "M_DRIVERSTATUS_1", "FRAMEID", "M_TOTALLAPS", "M_SESSIONTYPE", "R_FAV_TEAM",
        'M_TYRESSURFACETEMPERATURE_RL_1', 'M_TYRESSURFACETEMPERATURE_RR_1', 'M_TYRESSURFACETEMPERATURE_FL_1', 
        'M_TYRESSURFACETEMPERATURE_FR_1', 'M_TYRESINNERTEMPERATURE_RL_1', 'M_TYRESINNERTEMPERATURE_RR_1', 
        'M_TYRESINNERTEMPERATURE_FL_1', 'M_TYRESINNERTEMPERATURE_FR_1', 'M_ENGINETEMPERATURE_1'
    ]

    melbourne_df = melbourne_df.drop(columns=red_cols)
    return melbourne_df
