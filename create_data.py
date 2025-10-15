# Adds the imports
import pandas
from utils.pipeline import data_pipeline, read_data
import os

data, left, right, summary = data_pipeline()

for path in ["data/telemetry.csv", "data/summary.csv"]:
    if os.path.exists(path):
        os.remove(path)

data.to_csv("data/telemetry.csv", index=False)
summary.to_csv("data/summary.csv", index=False)
