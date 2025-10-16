# Adds the imports
import pandas as pd
from pipeline.pipeline import data_pipeline
import os

# Getting the data into pandas dataframes
data, left, right, line, summary = data_pipeline()

# Make sure output directory exists
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Define output file paths
telemetry_path = os.path.join(output_dir, "telemetry.csv")
summary_path = os.path.join(output_dir, "summary.csv")

# Remove existing files if they exist
for path in [telemetry_path, summary_path]:
    if os.path.exists(path):
        os.remove(path)

# Save outputs
data.to_csv(telemetry_path, index=False)
summary.to_csv(summary_path, index=False)
