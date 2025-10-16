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
file_paths = {
    "telemetry": os.path.join(output_dir, "telemetry.csv"),
    "summary": os.path.join(output_dir, "summary.csv"),
    "left": os.path.join(output_dir, "left.csv"),
    "right": os.path.join(output_dir, "right.csv"),
    "line": os.path.join(output_dir, "line.csv"),
}

# Remove existing files if they exist
for path in file_paths.values():
    if os.path.exists(path):
        os.remove(path)

# Save outputs
data.to_csv(file_paths["telemetry"], index=False)
summary.to_csv(file_paths["summary"], index=False)
left.to_csv(file_paths["left"], index=False)
right.to_csv(file_paths["right"], index=False)
line.to_csv(file_paths["line"], index=False)
