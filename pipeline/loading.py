import pandas as pd


def read_data(path=None):
    """Load the UNSW F1 2024 dataset, defaulting to repo structure if no path is given."""
    if path:
        return pd.read_csv(f"{path}")
    else:
        return pd.read_csv("data/UNSW F12024.csv")


def read_process_left(path=None):
    """Load and restrict the left track limits to expected coordinate bounds."""
    if path:
        left = pd.read_csv(f"{path}")
    else:
        left = pd.read_csv("data/f1sim-ref-left.csv")

    # Restrict to the same bounds as track_slice
    left = left[
        (left["WORLDPOSX"] >= 120)
        & (left["WORLDPOSX"] <= 600)
        & (left["WORLDPOSY"] >= -200)
        & (left["WORLDPOSY"] <= 600)
    ]

    return left


def read_process_right(path=None):
    """Load and restrict the right track limits to expected coordinate bounds."""
    if path:
        right = pd.read_csv(f"{path}")
    else:
        right = pd.read_csv("data/f1sim-ref-right.csv")

    # Restrict to the same bounds as track_slice
    right = right[
        (right["WORLDPOSX"] >= 120)
        & (right["WORLDPOSX"] <= 600)
        & (right["WORLDPOSY"] >= -200)
        & (right["WORLDPOSY"] <= 600)
    ]

    return right


def read_process_line(path=None):
    """Load and restrict the right track limits to expected coordinate bounds."""
    if path:
        line = pd.read_csv(f"{path}")
    else:
        line = pd.read_csv("data/f1sim-ref-line.csv")

    # Restrict to the same bounds as track_slice
    line = line[
        (line["WORLDPOSX"] >= 120)
        & (line["WORLDPOSX"] <= 600)
        & (line["WORLDPOSY"] >= -200)
        & (line["WORLDPOSY"] <= 600)
    ]

    line = line.sort_values("FRAME")
    return line
