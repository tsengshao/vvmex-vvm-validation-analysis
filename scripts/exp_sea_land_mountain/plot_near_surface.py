#!/usr/bin/env python3
"""Plot a near-surface y-mean Hovmoller for one VVM or VVMex run."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# The normal user Matplotlib cache may be read-only on the target machine.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vvm-matplotlib-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from vvm_readers import CPUReader, GPUReader
from near_surface import (
    extract_near_surface,
    topography_for_variable,
    validate_topography,
)


DEFAULT_CLEVS = np.arange(-5.0, 5.1, 0.5)


def build_pwo_colormap() -> mpl.colors.ListedColormap:
    """Return the purple-white-orange colormap used by the comparison plot."""
    colors = np.vstack(
        (
            mpl.colormaps["Purples_r"](np.linspace(0.3, 1.0, 128)),
            mpl.colormaps["Oranges"](np.linspace(0.0, 0.7, 128)),
        )
    )
    return mpl.colors.ListedColormap(colors, name="pwo")


def collect_ymean(
    reader: CPUReader | GPUReader,
    variable: str,
    max_times: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Read one simulation and return time and near-surface y-mean arrays."""
    steps = list(reader.steps)
    if max_times is not None:
        steps = steps[:max_times]
    if not steps:
        raise RuntimeError("No output time steps were selected")

    if isinstance(reader, CPUReader):
        topo = reader.read_topo()
    else:
        topo = reader.read_2d("topo", steps[0])
    topo = topography_for_variable(topo, variable)

    ymean = np.empty((len(steps), reader.x.size), dtype=np.float64)
    times_minutes = np.empty(len(steps), dtype=np.float64)
    topo_indices: np.ndarray | None = None

    for index, step in enumerate(steps):
        field = reader.read_3d(variable, step)
        if topo_indices is None:
            topo_indices = validate_topography(topo, field.shape)
        surface = extract_near_surface(field, topo_indices)
        ymean[index] = np.mean(surface, axis=0, dtype=np.float64)
        times_minutes[index] = reader.time_minutes(step)

        if index == 0 or (index + 1) % 10 == 0 or index + 1 == len(steps):
            print(
                f"Processed {index + 1:3d}/{len(steps)} time steps "
                f"(step {step:06d})"
            )

    return times_minutes, ymean


def draw_hovmoller(
    data: np.ndarray,
    x_m: np.ndarray,
    time_minutes: np.ndarray,
    model: str,
    variable: str,
    output_path: Path,
) -> None:
    """Draw and save a single near-surface Hovmoller panel."""
    plt.rcParams.update({"font.size": 18, "axes.linewidth": 2})
    # Keep the plotting panel at the original subplot's 10:8 proportion and
    # reserve extra horizontal space for the standalone colorbar.
    fig, ax = plt.subplots(figsize=(12, 8), layout="constrained")
    ax.set_box_aspect(8.0 / 10.0)

    cmap = build_pwo_colormap()
    norm = mpl.colors.BoundaryNorm(DEFAULT_CLEVS, cmap.N, extend="both")
    x_km = np.asarray(x_m, dtype=np.float64) / 1000.0
    time_hours = time_minutes / 60.0
    mesh = ax.pcolormesh(
        x_km, time_hours, data, cmap=cmap, norm=norm, shading="auto"
    )
    colorbar = fig.colorbar(mesh, ax=ax, extend="both")
    colorbar.set_ticks(DEFAULT_CLEVS[::2])
    colorbar.set_label(f"{variable} [m s$^{{-1}}$]")

    dx_km = float(np.median(np.diff(x_km)))
    nx = x_km.size
    x_tick_indices = np.arange(0, nx + 1, 256)
    if 896 <= nx and 896 not in x_tick_indices:
        x_tick_indices = np.sort(np.append(x_tick_indices, 896))
    ax.set_xticks(x_tick_indices * dx_km)
    ax.set_xlim(0.0, nx * dx_km)
    ax.set_yticks(np.arange(0.0, time_hours.max() + 0.01, 3.0))

    ax.set_xlabel("x [km]")
    ax.set_ylabel("Model time [hr]")
    ax.set_title(f"{model}: near-surface y-mean {variable}", loc="left")
    if time_hours.max() > 0.0:
        ax.set_ylim(0.0, time_hours.max())
    for grid_index in (512, 768):
        if grid_index < x_km.size:
            ax.axvline(x_km[grid_index], color="0.25", linestyle="--", linewidth=1.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        required=True,
        type=str.lower,
        choices=("vvm", "vvmex"),
        help="Simulation output format to read.",
    )
    parser.add_argument(
        "--case-path",
        required=True,
        type=Path,
        help="Path to the VVM or VVMex simulation directory.",
    )
    parser.add_argument("--variable", default="u", help="3-D variable to plot.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output PNG path (default: fig/hov_<variable>_surface_ymean_<model>.png).",
    )
    parser.add_argument(
        "--max-times",
        type=int,
        default=None,
        help="Read only the first N output times (useful for a quick test).",
    )
    args = parser.parse_args()
    if args.max_times is not None and args.max_times <= 0:
        parser.error("--max-times must be a positive integer")
    return args


def main() -> None:
    args = parse_args()
    model_label = "VVM" if args.model == "vvm" else "VVMex"
    reader = CPUReader(args.case_path) if args.model == "vvm" else GPUReader(args.case_path)
    output_path = args.output or Path(
        f"fig_single/hov_{args.variable}_surface_ymean_{args.model}.png"
    )

    print(f"Model: {model_label}")
    print(f"Simulation directory: {reader.case_path}")
    times_minutes, ymean = collect_ymean(reader, args.variable, args.max_times)
    draw_hovmoller(
        ymean, reader.x, times_minutes, model_label, args.variable, output_path
    )
    print(f"Wrote {output_path.resolve()}")


if __name__ == "__main__":
    main()
