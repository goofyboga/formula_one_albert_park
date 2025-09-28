import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

f1_left_limit = pd.read_csv("f1sim-ref-left.csv")
f1_right_limit = pd.read_csv("f1sim-ref-right.csv")
f1_turns_limit = pd.read_csv("f1sim-ref-turns.csv")

def plot_racing_line_t1_t2(
    df, left, right,
    x_col="M_WORLDPOSITIONX_1",
    y_col="M_WORLDPOSITIONY_1",
    color_col="exit_T2_speed",
    lower_limit=None, upper_limit=None,
    cmap="plasma_r",  # reversed gradient
    track_linestyle="--",
    show_apex=True,
    apex_marker="X",
):
    """
    Plots racing line from start of Turn 1 to end of Turn 2.
    Coloring can be any telemetry variable with optional numeric filtering.
    Track boundaries and apex shown.

    Example Usage: 
    plot_racing_line_t1_t2(f1_cleaned_df, f1_left_limit, f1_right_limit,
                       color_col="exit_T2_speed",
                       lower_limit=240, upper_limit=250)
    """

    # --- Copy df ---
    plot_df = df.copy()

    # --- Apply numeric filters ---
    if lower_limit is not None:
        plot_df = plot_df[plot_df[color_col] >= lower_limit]
    if upper_limit is not None:
        plot_df = plot_df[plot_df[color_col] <= upper_limit]

    # --- Sort by color to emphasize high values ---
    if color_col in plot_df:
        plot_df = plot_df.sort_values(by=color_col)

    # --- Extract variables ---
    x = plot_df[x_col]
    y = plot_df[y_col]
    colors = plot_df[color_col] if color_col in plot_df else "pink"

    # --- Hardcoded zoom covering Turn 1 → Turn 2 ---
    xlim = (315, 425)  # start of T1 → end of T2
    ylim = (0, 260)    # min/max Y across T1+T2

    # --- Plot ---
    plt.figure(figsize=(12, 10))

    # Track boundaries
    plt.plot(
        left[(left["WORLDPOSX"].between(*xlim)) & (left["WORLDPOSY"].between(*ylim))]
            .sort_values(by="FRAME")["WORLDPOSX"],
        left[(left["WORLDPOSX"].between(*xlim)) & (left["WORLDPOSY"].between(*ylim))]
            .sort_values(by="FRAME")["WORLDPOSY"],
        linestyle=track_linestyle, color="lightgray", linewidth=1.5, label="Left boundary"
    )
    plt.plot(
        right[(right["WORLDPOSX"].between(*xlim)) & (right["WORLDPOSY"].between(*ylim))]
            .sort_values(by="FRAME")["WORLDPOSX"],
        right[(right["WORLDPOSX"].between(*xlim)) & (right["WORLDPOSY"].between(*ylim))]
            .sort_values(by="FRAME")["WORLDPOSY"],
        linestyle=track_linestyle, color="slategray", linewidth=1.5, label="Right boundary"
    )

    # Racing line
    sc = plt.scatter(x, y, c=colors, cmap=cmap, s=3, alpha=0.7)
    if isinstance(colors, pd.Series) and pd.api.types.is_numeric_dtype(colors):
        plt.colorbar(sc, label=color_col)

    # Optional apex markers (T1 + T2)
    if show_apex:
        # Apex points from your CSV (hardcoded for T1+T2)
        t1_apex = (375.57, 191.519)
        t2_apex = (368.93, 90)
        plt.scatter(*t1_apex, marker=apex_marker, color="lime", s=100, label="T1 Apex", zorder=5)
        plt.scatter(*t2_apex, marker=apex_marker, color="aqua", s=100, label="T2 Apex", zorder=5)

    # Labels & title
    limit_text = ""
    if lower_limit is not None or upper_limit is not None:
        low = lower_limit if lower_limit is not None else ""
        high = upper_limit if upper_limit is not None else ""
        limit_text = f" [{low}–{high}]"

    plt.xlabel("X Position")
    plt.ylabel("Y Position")
    plt.title(f"Turns 1–2 Racing Line by {color_col}{limit_text}")
    plt.axis("equal")
    plt.xlim(*xlim)
    plt.ylim(*ylim)
    plt.legend()
    plt.show()
