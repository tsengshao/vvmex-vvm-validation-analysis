#!/usr/bin/env python3
"""Plot smoothed VVM and VVMex water-path time series as a two-panel PDF."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# The normal Matplotlib cache is read-only on the target machine.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vvm-matplotlib-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "water_path_timeseries.nc"
DEFAULT_OUTPUT = SCRIPT_DIR / "fig_water_path_timeseries.pdf"

MODEL_NAMES = ("VVM", "VVMex")
VARIABLES = ("cwv_mean", "cwv_std", "lwp_mean", "iwp_mean", "dryfrac")

CWV_COLOR = "#000000"
LWP_COLOR = "#0072B2"
IWP_COLOR = "#7B2CBF"
DRYFRAC_COLOR = "#D55E00"
LWP_IWP_AXIS_COLOR = "#5250B8"
VVM_WHITE_FRACTION = 0.38
LINE_WIDTH = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--running-mean-days",
        type=float,
        default=1.0,
        help=(
            "Width of the centered running-mean window in days; "
            "use 0 for no smoothing (default: 1)."
        ),
    )
    parser.add_argument("--title", default="300 K", help="Bold upper-left title.")
    return parser.parse_args()


def lighten(color: str, white_fraction: float = VVM_WHITE_FRACTION) -> tuple[float, ...]:
    """Mix a Matplotlib color with white."""
    if not 0.0 <= white_fraction <= 1.0:
        raise ValueError("white_fraction must be between 0 and 1")
    rgb = np.asarray(to_rgb(color), dtype=np.float64)
    return tuple(rgb + (1.0 - rgb) * white_fraction)


def centered_running_mean(
    values: np.ndarray, time_days: np.ndarray, window_days: float
) -> np.ndarray:
    """Return a centered mean using all available points near each time.

    For a one-day window, each output at time t uses samples from
    t - 0.5 day through t + 0.5 day, including both endpoints. Values are NaN
    where a complete centered window does not fit inside the time series.
    """
    values = np.asarray(values, dtype=np.float64)
    time_days = np.asarray(time_days, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"values must have shape (model, time), got {values.shape}")
    if time_days.ndim != 1 or values.shape[1] != time_days.size:
        raise ValueError("time coordinate does not match the data time dimension")
    if window_days < 0.0:
        raise ValueError("running-mean window must be non-negative")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(time_days)):
        raise ValueError("running-mean input contains non-finite values")
    if not np.all(np.diff(time_days) > 0.0):
        raise ValueError("time coordinate must be strictly increasing")
    if window_days == 0.0:
        return values.copy()

    half_window = 0.5 * window_days
    left = np.searchsorted(time_days, time_days - half_window, side="left")
    right = np.searchsorted(time_days, time_days + half_window, side="right")
    cumulative = np.pad(np.cumsum(values, axis=1), ((0, 0), (1, 0)))
    sums = cumulative[:, right] - cumulative[:, left]
    counts = right - left
    result = sums / counts[None, :]
    complete_window = (time_days - half_window >= time_days[0]) & (
        time_days + half_window <= time_days[-1]
    )
    result[:, ~complete_window] = np.nan
    return result


def running_mean_label(window_days: float) -> str:
    if window_days == 0.0:
        return "No running mean"
    number = f"{window_days:g}"
    unit = "day" if np.isclose(window_days, 1.0) else "days"
    return f"{number}-{unit} running mean"


def set_plot_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 18,
            "axes.labelsize": 20,
            "axes.titlesize": 24,
            "axes.linewidth": 1.5,
            "xtick.labelsize": 17,
            "ytick.labelsize": 17,
            "xtick.major.size": 7,
            "ytick.major.size": 7,
            "xtick.major.width": 1.4,
            "ytick.major.width": 1.4,
            "legend.fontsize": 18,
            "lines.linewidth": LINE_WIDTH,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def load_data(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if not path.is_file():
        raise FileNotFoundError(f"Input NetCDF not found: {path}")

    with xr.open_dataset(path, decode_times=False) as dataset:
        missing = [name for name in VARIABLES if name not in dataset]
        if missing:
            raise KeyError(f"Missing variables in {path}: {', '.join(missing)}")
        if "model" not in dataset.coords or "time" not in dataset.coords:
            raise KeyError("Input dataset must have model and time coordinates")

        available_models = [str(value) for value in dataset["model"].values]
        if set(available_models) != set(MODEL_NAMES):
            raise ValueError(
                f"Expected models {MODEL_NAMES}, found {tuple(available_models)}"
            )
        dataset = dataset.sel(model=list(MODEL_NAMES))
        time_seconds = np.asarray(dataset["time"], dtype=np.float64)
        data = {
            name: np.asarray(dataset[name], dtype=np.float64) for name in VARIABLES
        }

    time_days = time_seconds / 86400.0
    if time_days[0] != 0.0:
        time_days = time_days - time_days[0]
    return time_days, data


def plot_model_pair(
    axis: mpl.axes.Axes,
    time_days: np.ndarray,
    values: np.ndarray,
    color: str,
) -> None:
    """Plot VVM as a pale dashed line and VVMex as a solid line."""
    vvm_index = MODEL_NAMES.index("VVM")
    vvmex_index = MODEL_NAMES.index("VVMex")
    axis.plot(
        time_days,
        values[vvm_index],
        color=lighten(color),
        linestyle=(0, (7, 4)),
        label="_nolegend_",
        zorder=2,
    )
    axis.plot(
        time_days,
        values[vvmex_index],
        color=color,
        linestyle="-",
        label="_nolegend_",
        zorder=3,
    )


def semantic_legends(
    axis: mpl.axes.Axes,
    variables: tuple[tuple[str, str], ...],
    *,
    variable_location: str,
) -> tuple[mpl.legend.Legend, mpl.legend.Legend]:
    """Draw separate framed, single-column model and variable legends."""
    model_handles = [
        Line2D([], [], color="0.15", linestyle="-", label="VVMex"),
        Line2D(
            [],
            [],
            color="0.45",
            linestyle=(0, (7, 4)),
            label="VVM",
        ),
    ]
    variable_handles = [
        Line2D([], [], color=color, linestyle="-", label=label)
        for label, color in variables
    ]
    model_legend = axis.legend(
        handles=model_handles,
        loc="upper left",
        bbox_to_anchor=(0.01, 0.99),
        ncol=1,
        frameon=True,
        framealpha=0.92,
        facecolor="white",
        edgecolor="0.35",
        columnspacing=1.4,
        handlelength=3.2,
        handletextpad=0.6,
    )
    axis.add_artist(model_legend)
    if variable_location == "upper right":
        legend_location = "upper right"
        legend_anchor = (0.99, 0.99)
    elif variable_location == "below model":
        legend_location = "upper left"
        legend_anchor = (0.01, 0.80)
    else:
        raise ValueError(f"Unsupported variable legend location: {variable_location}")
    variable_legend = axis.legend(
        handles=variable_handles,
        loc=legend_location,
        bbox_to_anchor=legend_anchor,
        ncol=1,
        frameon=True,
        framealpha=0.92,
        facecolor="white",
        edgecolor="0.35",
        columnspacing=1.4,
        handlelength=3.2,
        handletextpad=0.6,
    )
    return model_legend, variable_legend


def color_y_axis(axis: mpl.axes.Axes, color: str, side: str) -> None:
    """Color a y-axis label, ticks, and visible side spine consistently."""
    axis.yaxis.label.set_color(color)
    axis.tick_params(axis="y", colors=color)
    axis.spines[side].set_color(color)


def draw_figure(
    time_days: np.ndarray,
    data: dict[str, np.ndarray],
    running_mean_days: float,
    title: str,
) -> mpl.figure.Figure:
    smoothed = {
        name: centered_running_mean(values, time_days, running_mean_days)
        for name, values in data.items()
    }

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(16, 14),
        sharex=True,
        gridspec_kw={"height_ratios": [1, 1], "hspace": 0.10},
    )
    top_left, bottom_left = axes
    top_right = top_left.twinx()
    bottom_right = bottom_left.twinx()

    plot_model_pair(top_left, time_days, smoothed["cwv_mean"], CWV_COLOR)
    plot_model_pair(
        top_right,
        time_days,
        smoothed["lwp_mean"] / 0.01,
        LWP_COLOR,
    )
    plot_model_pair(
        top_right,
        time_days,
        smoothed["iwp_mean"] / 0.01,
        IWP_COLOR,
    )

    plot_model_pair(
        bottom_left,
        time_days,
        smoothed["cwv_std"],
        CWV_COLOR,
    )
    plot_model_pair(
        bottom_right,
        time_days,
        smoothed["dryfrac"],
        DRYFRAC_COLOR,
    )

    top_left.set_ylim(10.0, 60.0)
    top_left.set_yticks(np.arange(10.0, 61.0, 10.0))
    top_right.set_ylim(0.0, 15.0)
    top_right.set_yticks(np.arange(0.0, 15.1, 3.0))
    bottom_left.set_ylim(0.0, 25.0)
    bottom_left.set_yticks(np.arange(0.0, 25.1, 5.0))
    bottom_right.set_ylim(0.0, 1.0)
    bottom_right.set_yticks(np.arange(0.0, 1.01, 0.2))
    bottom_left.set_xlim(float(time_days[0]), float(time_days[-1]))

    top_left.set_ylabel("CWV [mm]")
    top_right.set_ylabel(r"LWP & IWP [$10^{-2}$ mm]")
    bottom_left.set_ylabel("CWV std [mm]")
    bottom_right.set_ylabel(r"DRYFRAC (CWV $\leq$ 30 mm)")
    bottom_left.set_xlabel("Time [day]")

    color_y_axis(top_left, CWV_COLOR, "left")
    color_y_axis(top_right, LWP_IWP_AXIS_COLOR, "right")
    color_y_axis(bottom_left, CWV_COLOR, "left")
    color_y_axis(bottom_right, DRYFRAC_COLOR, "right")

    top_left.set_title(title, loc="left", fontweight="bold", pad=14)
    top_left.set_title(running_mean_label(running_mean_days), loc="right", pad=14)

    for axis in (top_left, top_right, bottom_left, bottom_right):
        axis.tick_params(direction="out")
    for axis in (top_left, bottom_left):
        axis.grid(axis="both", color="0.88", linewidth=0.9, zorder=0)

    semantic_legends(
        top_left,
        (("CWV", CWV_COLOR), ("LWP", LWP_COLOR), ("IWP", IWP_COLOR)),
        variable_location="upper right",
    )
    semantic_legends(
        bottom_left,
        (("CWV std", CWV_COLOR), ("DRYFRAC", DRYFRAC_COLOR)),
        variable_location="below model",
    )

    figure.subplots_adjust(left=0.10, right=0.90, bottom=0.10, top=0.92, hspace=0.12)
    return figure


def main() -> None:
    args = parse_args()
    if args.running_mean_days < 0.0:
        raise ValueError("--running-mean-days must be non-negative")

    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if output_path.suffix.lower() != ".pdf":
        raise ValueError("--output must use the .pdf extension")

    set_plot_style()
    time_days, data = load_data(input_path)
    figure = draw_figure(time_days, data, args.running_mean_days, args.title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the requested 16:10 (8:5) canvas ratio exactly. Tight bounding-box
    # cropping would change the final PDF aspect ratio because of the twin axes.
    figure.savefig(output_path, format="pdf")
    plt.close(figure)
    print(f"Input: {input_path}")
    print(f"Running mean: {running_mean_label(args.running_mean_days)}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
