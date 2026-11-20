#!/usr/bin/env python3
"""Compare VVM and VVMex near-surface wind and draw y-mean Hovmollers."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# The normal user Matplotlib cache is read-only on the target machine.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vvm-matplotlib-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from vvm_readers import CPUReader, GPUReader
from near_surface import (
    extract_near_surface,
    topography_for_variable,
    validate_topography,
)


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
DEFAULT_CASE = "grass"
DEFAULT_CASE_PATHS = {
    "grass": {
        "cpu": SCRIPT_DIR / "../../VVM/nb_g_eb_300m_aaron_new",
        "gpu": SCRIPT_DIR / "../../VVMex/sea_grass_mountain_good_luck",
    },
    "urban": {
        "cpu": SCRIPT_DIR / "../../VVM/nb_u_eb_300m_aaron",
        "gpu": SCRIPT_DIR / "../../VVMex/sea_urban_mountain_good_luck_2",
    },
}
DEFAULT_CACHE_DIR = ROOT_DIR / "DATA/exp_sea_land_mountain"

FIELD_CLEVS = np.arange(-5.0, 5.1, 0.5)
DIFFERENCE_CLEVS = np.arange(0, 1.1, 0.1)
RELATIVE_ERROR_MIN_REFERENCE = 1.0e-6
SURFACE_SAMPLING = "periodic_staggered_topo_no_z_offset_v1"


class OutdatedSurfaceCacheError(ValueError):
    """A comparison cache predates the current surface sampling method."""


def build_pwo_colormap() -> mpl.colors.ListedColormap:
    """Purple-white-orange colormap used by the reference Hovmoller script."""
    purple = mpl.colormaps["Purples_r"]
    orange = mpl.colormaps["Oranges"]
    colors = np.vstack(
        (
            purple(np.linspace(0.3, 1.0, 128)),
            orange(np.linspace(0.0, 0.7, 128)),
        )
    )
    return mpl.colors.ListedColormap(colors, name="pwo")


def common_steps(cpu: CPUReader, gpu: GPUReader, max_times: int | None) -> list[int]:
    steps = sorted(set(cpu.steps).intersection(gpu.steps))
    if not steps:
        raise RuntimeError("VVM and VVMex outputs have no common time steps")
    if max_times is not None:
        steps = steps[:max_times]
    return steps


def collect_comparison(
    cpu: CPUReader,
    gpu: GPUReader,
    variable: str,
    steps: list[int],
) -> dict[str, np.ndarray]:
    """Stream through files and collect near-surface y means for plotting."""
    topo = cpu.read_topo()
    # gpu_topo = gpu.read_2d("topo", steps[0])
    # expected_gpu_topo = np.where(topo == 0, 1, topo)
    # if not np.array_equal(gpu_topo, expected_gpu_topo):
    #     mismatch = int(np.count_nonzero(gpu_topo != expected_gpu_topo))
    #     print(
    #         f"WARNING: VVMex topo differs from the expected VVM convention at "
    #         f"{mismatch} cells; VVM topo is still used for both fields."
    #     )
    #     sys.exit()

    # Retain the common CPU topography used for comparing both normalized fields.
    topo = topography_for_variable(topo, variable)

    nt = len(steps)
    nx = topo.shape[1]
    cpu_ymean = np.empty((nt, nx), dtype=np.float64)
    gpu_ymean = np.empty((nt, nx), dtype=np.float64)
    relative_error_ymean = np.empty((nt, nx), dtype=np.float64)
    times_minutes = np.empty(nt, dtype=np.float64)

    topo_indices: np.ndarray | None = None
    for it, step in enumerate(steps):
        cpu_field = cpu.read_3d(variable, step)
        gpu_field = gpu.read_3d(variable, step)
        if cpu_field.shape != gpu_field.shape:
            raise ValueError(
                f"Shape mismatch at step {step:06d}: VVM {cpu_field.shape}, "
                f"VVMex {gpu_field.shape}"
            )

        if topo_indices is None:
            topo_indices = validate_topography(topo, cpu_field.shape)

        cpu_surface = extract_near_surface(cpu_field, topo_indices).astype(
            np.float64, copy=False
        )
        gpu_surface = extract_near_surface(gpu_field, topo_indices).astype(
            np.float64, copy=False
        )

        cpu_ymean[it] = np.mean(cpu_surface, axis=0)
        gpu_ymean[it] = np.mean(gpu_surface, axis=0)

        relative_error_ymean[it] = np.divide(
            np.abs(gpu_ymean[it] - cpu_ymean[it]),
            np.abs(cpu_ymean[it]),
            out=np.full_like(cpu_ymean[it], np.nan),
            where=np.abs(cpu_ymean[it]) >= RELATIVE_ERROR_MIN_REFERENCE,
        )

        cpu_time = cpu.time_minutes(step)
        gpu_time = gpu.time_minutes(step)
        if not np.isclose(cpu_time, gpu_time):
            raise ValueError(
                f"Time mismatch at step {step:06d}: VVM={cpu_time} min, "
                f"VVMex={gpu_time} min"
            )
        times_minutes[it] = cpu_time

        if it == 0 or (it + 1) % 10 == 0 or it + 1 == nt:
            print(f"Processed {it + 1:3d}/{nt} time steps (step {step:06d})")

    return {
        "steps": np.asarray(steps, dtype=np.int64),
        "time_minutes": times_minutes,
        "cpu_ymean": cpu_ymean,
        "gpu_ymean": gpu_ymean,
        "relative_error_ymean": relative_error_ymean,
    }


def case_label(cpu_case: Path, gpu_case: Path) -> str:
    """Infer the sea-surface case label used in output filenames."""
    names = f"{cpu_case} {gpu_case}".lower()
    if "urban" in names or "nb_u" in names:
        return "urban"
    if "grass" in names or "nb_g" in names:
        return "grass"
    raise ValueError(
        "Could not infer case label from --cpu-case/--gpu-case; expected grass or urban"
    )


def resolve_case_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    defaults = DEFAULT_CASE_PATHS[args.case]
    cpu_case = args.cpu_case if args.cpu_case is not None else defaults["cpu"]
    gpu_case = args.gpu_case if args.gpu_case is not None else defaults["gpu"]
    return cpu_case, gpu_case


def cache_path_for_args(args: argparse.Namespace, label: str) -> Path:
    if args.cache_file is not None:
        return args.cache_file

    suffix = "" if args.max_times is None else f"_max{args.max_times}"
    return args.cache_dir / f"sea_{label}_mountain{suffix}.nc"


def output_dir_for_args(args: argparse.Namespace) -> Path:
    if args.output_dir is not None:
        return args.output_dir
    return SCRIPT_DIR / "fig"


def comparison_to_dataset(
    comparison: dict[str, np.ndarray],
    x_m: np.ndarray,
    variable: str,
    vvm_case: Path,
    vvmex_case: Path,
    max_times: int | None,
) -> xr.Dataset:
    return xr.Dataset(
        data_vars={
            "cpu_ymean": (("time", "x"), comparison["cpu_ymean"]),
            "gpu_ymean": (("time", "x"), comparison["gpu_ymean"]),
            "relative_error_ymean": (
                ("time", "x"),
                comparison["relative_error_ymean"],
            ),
        },
        coords={
            "time": np.arange(comparison["time_minutes"].size, dtype=np.int64),
            "x": np.asarray(x_m, dtype=np.float64),
            "step": ("time", comparison["steps"]),
            "time_minutes": ("time", comparison["time_minutes"]),
        },
        attrs={
            "variable": variable,
            "surface_sampling": SURFACE_SAMPLING,
            "vvm_case": str(vvm_case.resolve()),
            "vvmex_case": str(vvmex_case.resolve()),
            "max_times": "" if max_times is None else str(max_times),
        },
    )


def dataset_to_comparison(
    dataset: xr.Dataset, variable: str
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Validate a cache file and return its plot-ready comparison and x coordinate."""
    required_data_vars = ("cpu_ymean", "gpu_ymean", "relative_error_ymean")
    missing_data_vars = [name for name in required_data_vars if name not in dataset.data_vars]
    if missing_data_vars:
        raise KeyError(
            "Cache file is missing data variables: "
            f"{', '.join(missing_data_vars)}"
        )

    required_coords = ("x", "step", "time_minutes")
    missing_coords = [name for name in required_coords if name not in dataset.coords]
    if missing_coords:
        raise KeyError(f"Cache file is missing coordinates: {', '.join(missing_coords)}")

    cached_variable = dataset.attrs.get("variable")
    if cached_variable != variable:
        raise ValueError(
            f"Cache variable mismatch: cache has {cached_variable!r}, "
            f"but --variable is {variable!r}"
        )

    if dataset.attrs.get("surface_sampling") != SURFACE_SAMPLING:
        raise OutdatedSurfaceCacheError(
            "Cache does not use the current topou/topov/topow sampling method"
        )

    comparison = {
        "steps": np.asarray(dataset["step"].values, dtype=np.int64),
        "time_minutes": np.asarray(dataset["time_minutes"].values, dtype=np.float64),
        "cpu_ymean": np.asarray(dataset["cpu_ymean"].values, dtype=np.float64),
        "gpu_ymean": np.asarray(dataset["gpu_ymean"].values, dtype=np.float64),
        "relative_error_ymean": np.asarray(
            dataset["relative_error_ymean"].values, dtype=np.float64
        ),
    }
    return comparison, np.asarray(dataset["x"].values, dtype=np.float64)


def load_cached_comparison(
    cache_path: Path, variable: str
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Load a validated cache without accessing VVM or VVMex outputs."""
    print(f"Reading cached comparison: {cache_path}")
    with xr.open_dataset(cache_path, decode_times=False) as dataset:
        return dataset_to_comparison(dataset, variable)


def write_comparison_cache(
    cache_path: Path,
    comparison: dict[str, np.ndarray],
    x_m: np.ndarray,
    variable: str,
    vvm_case: Path,
    vvmex_case: Path,
    max_times: int | None,
) -> None:
    """Write a newly computed comparison cache."""
    dataset = comparison_to_dataset(
        comparison,
        x_m,
        variable,
        vvm_case,
        vvmex_case,
        max_times,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_netcdf(cache_path)
    print(f"Wrote {cache_path}")


def set_plot_defaults() -> None:
    plt.rcParams.update(
        {
            "font.size": 20,
            "axes.linewidth": 2,
            "lines.linewidth": 5,
        }
    )


def draw_hovmoller_on_axis(
    ax: mpl.axes.Axes,
    data: np.ndarray,
    x_m: np.ndarray,
    time_minutes: np.ndarray,
    title: str,
    clevs: np.ndarray,
    cmap: mpl.colors.Colormap,
    extend: str,
) -> mpl.collections.QuadMesh:
    norm = mpl.colors.BoundaryNorm(clevs, ncolors=cmap.N, extend=extend)
    x_km = np.asarray(x_m, dtype=np.float64) / 1000.0
    time_hours = np.asarray(time_minutes, dtype=np.float64) / 60.0
    dx_km = float(np.median(np.diff(x_km)))
    nx = x_km.size

    mesh = ax.pcolormesh(
        x_km,
        time_hours,
        data,
        cmap=cmap,
        norm=norm,
        shading="auto",
    )
    x_tick_indices = np.arange(0, nx + 1, 256)
    x_tick_indices = np.insert(x_tick_indices, -2, 896)
    ax.set_xticks(x_tick_indices * dx_km)
    ax.set_xlim(0.0, nx * dx_km)
    ax.set_yticks(np.arange(0.0, time_hours.max() + 0.01, 3.0))
    if time_hours.max() > 0.0:
        ax.set_ylim(0.0, time_hours.max())
    for grid_index in (512, 768):
        ax.axvline(
            grid_index * dx_km,
            color="0.25",
            linestyle="--",
            linewidth=1.5,
            zorder=10,
        )

    ax.set_xlabel("x [km]")
    ax.set_ylabel("Local Time [hr]")
    ax.set_title(title, loc="left", fontweight="bold", fontsize=25)
    return mesh


def draw_land_region_axis(panel: mpl.axes.Axes, case: str) -> None:
    """Draw the land-type guide aligned with the Hovmoller x axis."""
    region_ax = panel.inset_axes([0.0, 0.78, 1.0, 0.22])
    region_ax.set_xlim(0.0, 256.0)
    region_ax.set_ylim(0.0, 1.0)
    region_ax.set_axis_off()
    region_ax.set_yticks([])

    labels = (
        (64.0, "sea"),
        (160.0, f"plain\n({case})"),
        (224.0, "mountain\n(evergreen)"),
    )
    for x_position, label in labels:
        region_ax.text(
            x_position,
            0.8,
            label,
            ha="center",
            va="center",
            fontsize=22,
            linespacing=1.1,
        )

    for x_position in (0.0, 128.0, 192.0, 256.0):
        region_ax.vlines(
            x_position,
            ymin=0.6,
            ymax=1.0,
            color="black",
            linewidth=1.5,
            clip_on=False,
        )


def draw_combined_hovmoller(
    plot_specs: tuple[
        tuple[np.ndarray, str, np.ndarray, mpl.colors.Colormap, str, str], ...
    ],
    x_m: np.ndarray,
    time_minutes: np.ndarray,
    case: str,
    output_path: Path,
) -> None:
    """Draw three fields in a 2x2 layout with colorbars at lower right."""
    set_plot_defaults()
    fig, axes_2d = plt.subplots(
        2,
        2,
        figsize=(20, 16),
        sharex=True,
        sharey=True,
        layout="constrained",
    )
    plot_axes = (axes_2d[0, 0], axes_2d[0, 1], axes_2d[1, 0])
    meshes = []
    for index, (
        ax,
        (data, title, clevs, cmap, _colorbar_label, extend),
    ) in enumerate(
        zip(plot_axes, plot_specs, strict=True)
    ):
        mesh = draw_hovmoller_on_axis(
            ax, data, x_m, time_minutes, title, clevs, cmap, extend
        )
        meshes.append(mesh)
        ax.tick_params(axis="x", labelbottom=True)
        if index == 1:
            ax.set_ylabel("")

    colorbar_panel = axes_2d[1, 1]
    colorbar_panel.set_axis_off()
    draw_land_region_axis(colorbar_panel, case)
    field_cax = colorbar_panel.inset_axes([0.08, 0.62, 0.84, 0.10])
    difference_cax = colorbar_panel.inset_axes([0.08, 0.25, 0.84, 0.10])

    field_colorbar = fig.colorbar(
        meshes[0],
        cax=field_cax,
        orientation="horizontal",
        extend=plot_specs[0][5],
    )
    field_colorbar.set_ticks(plot_specs[0][2][::2])
    field_colorbar.set_label(plot_specs[0][4])

    difference_colorbar = fig.colorbar(
        meshes[2],
        cax=difference_cax,
        orientation="horizontal",
        extend=plot_specs[2][5],
    )
    difference_colorbar.set_ticks(plot_specs[2][2][::2])
    difference_colorbar.set_label(plot_specs[2][4])

    fig.savefig(output_path, dpi=300, transparent=False)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=tuple(DEFAULT_CASE_PATHS),
        default=DEFAULT_CASE,
        help="Select the default VVM/VVMex case directories.",
    )
    parser.add_argument(
        "--vvm-case",
        "--cpu-case",
        dest="cpu_case",
        type=Path,
        default=None,
        metavar="VVM_CASE",
        help="Override the VVM case directory selected by --case.",
    )
    parser.add_argument(
        "--vvmex-case",
        "--gpu-case",
        dest="gpu_case",
        type=Path,
        default=None,
        metavar="VVMEX_CASE",
        help="Override the VVMex case directory selected by --case.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the combined figure; defaults to ./fig.",
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=None,
        help=(
            "Use an explicit NetCDF cache file instead of "
            "DATA/exp_sea_land_mountain/sea_{case}_mountain.nc."
        ),
    )
    parser.add_argument("--variable", default="u")
    parser.add_argument(
        "--max-times",
        type=int,
        default=None,
        help="Limit the number of common time steps (useful for smoke tests).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    label = args.case
    cache_path = cache_path_for_args(args, label)
    output_dir = output_dir_for_args(args)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Case: {label}")
    comparison = None
    if cache_path.exists():
        try:
            comparison, x_m = load_cached_comparison(cache_path, args.variable)
        except OutdatedSurfaceCacheError:
            print("Surface sampling changed; recomputing the comparison cache.")
    if comparison is None:
        cpu_case, gpu_case = resolve_case_paths(args)
        if args.cpu_case is not None or args.gpu_case is not None:
            label = case_label(cpu_case, gpu_case)
        print(f"Computing comparison: {cache_path}")
        print(f"VVM case: {cpu_case.resolve()}")
        print(f"VVMex case: {gpu_case.resolve()}")
        cpu = CPUReader(cpu_case)
        gpu = GPUReader(gpu_case)

        if cpu.x.shape != gpu.x.shape or cpu.y.shape != gpu.y.shape:
            raise ValueError(
                f"Horizontal grid shape mismatch: VVM {(cpu.y.size, cpu.x.size)}, "
                f"VVMex {(gpu.y.size, gpu.x.size)}"
            )
        if not np.allclose(cpu.z, gpu.z):
            raise ValueError(
                "VVM levels after dropping level zero do not match VVMex z_mid"
            )

        steps = common_steps(cpu, gpu, args.max_times)
        print(f"Common time steps selected: {len(steps)}")
        comparison = collect_comparison(cpu, gpu, args.variable, steps)
        x_m = cpu.x
        write_comparison_cache(
            cache_path,
            comparison,
            x_m,
            args.variable,
            cpu.case_path,
            gpu.case_path,
            args.max_times,
        )

    field_cmap = build_pwo_colormap()
    difference_cmap = mpl.colors.ListedColormap(
        plt.cm.Greys(np.linspace(0.0, 0.7, 128)), name="white_to_gray"
    )
    difference_cmap.set_over(plt.cm.Greys(0.85))
    difference_cmap.set_bad("white")

    outputs = (
        (
            comparison["gpu_ymean"],
            "(a) VVMex",
            FIELD_CLEVS,
            field_cmap,
            "u [m s$^{-1}$]",
            "both",
        ),
        (
            comparison["cpu_ymean"],
            "(b) VVM",
            FIELD_CLEVS,
            field_cmap,
            "u [m s$^{-1}$]",
            "both",
        ),
        (
            comparison["relative_error_ymean"],
            "(c) Relative L$_2$ norm",
            DIFFERENCE_CLEVS,
            difference_cmap,
            "Relative L$_2$ norm",
            "max",
        ),
    )

    time_suffix = "" if args.max_times is None else f"_max{args.max_times}"
    combined_path = (
        output_dir
        / f"hov_{args.variable}_surface_ymean_{label}_combined{time_suffix}.png"
    )
    draw_combined_hovmoller(
        outputs,
        x_m,
        comparison["time_minutes"],
        label,
        combined_path,
    )
    print(f"Wrote {combined_path}")


if __name__ == "__main__":
    main()
