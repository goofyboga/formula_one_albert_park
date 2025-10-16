import pandas as pd
import logging
from .loading import read_data

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cleaning():
    df = read_data()
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

    df = remove_stuttery_laps(df)
    logger.info("Removed bad lap data.")

    return df


def filter_melbourne(df):
    """Keep only laps from the Melbourne circuit."""
    return df[df["M_TRACKID"] == 0]


def remove_na(df):
    return df.dropna(subset=["M_WORLDPOSITIONX_1", "M_WORLDPOSITIONY_1"]).reset_index(
        drop=True
    )


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
