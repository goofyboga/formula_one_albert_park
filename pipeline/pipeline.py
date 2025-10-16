import pandas as pd
import logging
from .cleaning import cleaning
from .spatial import spatial
from .telemetry_eng import telemetry_eng
from .summary_eng import summary_eng

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def data_pipeline():
    """
    Complete data pipeline:
        - load data
        - filter for Melbourne laps
        - slice track coordinates
        - re-index the data
        - enforce track limits
        - remove laps with insufficient data
    """

    df = cleaning()
    logger.info("Cleaning Complete.")

    df, left, right = spatial(df)
    logger.info("Spatial engineering compelete.")

    df, line = telemetry_eng(df)
    logger.info("Telemetry engineering complete.")

    df, summary = summary_eng(df)
    logger.info("Summary Engineering complete.")

    logger.info("Pipeline Complete.... Happy Exploring :-)")
    return df, left, right, line, summary
