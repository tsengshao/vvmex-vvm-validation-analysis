#!/usr/bin/env python3
"""Compare CPU and GPU near-surface VVM wind and draw y-mean Hovmollers."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

# The normal user Matplotlib cache is read-only on the target machine.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vvm-matplotlib-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from vvm_readers import CPUReader, GPUReader
from l2_norm import (
    atmospheric_mask,
    layer_thickness,
    relative_weighted_l2_norm,
    weighted_l2_norm,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CPU_CASE = SCRIPT_DIR / "../../cpu/nb_g_eb_300m_aaron_new"
DEFAULT_GPU_CASE = SCRIPT_DIR / "../../gpu/sea_grass_mountain_good_luck"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "fig_grass"

## DEFAULT_CPU_CASE = SCRIPT_DIR / "../../cpu/nb_u_eb_300m_aaron"
## DEFAULT_GPU_CASE = SCRIPT_DIR / "../../gpu/sea_urban_mountain_good_luck_2"
## DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "fig_urban"

FIELD_CLEVS = np.arange(-5.0, 5.1, 0.5)
DIFFERENCE_CLEVS = np.arange(0, 1.1, 0.1)
RELATIVE_ERROR_MIN_REFERENCE = 1.0e-6


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


def validate_topography(topo: np.ndarray, field_shape: tuple[int, ...]) -> np.ndarray:
    """Validate and return topography as integer indices into a (z, y, x) field."""
    if topo.shape != field_shape[1:]:
        raise ValueError(
            f"Topography shape {topo.shape} does not match field y/x shape "
            f"{field_shape[1:]}"
        )
    if not np.all(np.isfinite(topo)):
        raise ValueError("Topography contains non-finite values")
    if not np.allclose(topo, np.rint(topo)):
        raise ValueError("Topography contains non-integer level indices")

    indices = np.rint(topo).astype(np.intp)
    if indices.min() < 0 or indices.max() >= field_shape[0]:
        raise IndexError(
            f"Topography indices [{indices.min()}, {indices.max()}] exceed "
            f"available z indices [0, {field_shape[0] - 1}]"
        )
    return indices


def extract_near_surface(field: np.ndarray, topo_indices: np.ndarray) -> np.ndarray:
    """Select field[topo[y, x], y, x] for every horizontal grid cell."""
    return np.take_along_axis(field, topo_indices[None, :, :], axis=0)[0]


def common_steps(cpu: CPUReader, gpu: GPUReader, max_times: int | None) -> list[int]:
    steps = sorted(set(cpu.steps).intersection(gpu.steps))
    if not steps:
        raise RuntimeError("CPU and GPU outputs have no common time steps")
    if max_times is not None:
        steps = steps[:max_times]
    return steps


def collect_comparison(
    cpu: CPUReader,
    gpu: GPUReader,
    variable: str,
    steps: list[int],
    rho: np.ndarray,
    dz: np.ndarray,
) -> dict[str, np.ndarray]:
    """Stream through files and collect y means plus surface-domain error norms."""
    topo = cpu.read_topo()
    # gpu_topo = gpu.read_2d("topo", steps[0])
    # expected_gpu_topo = np.where(topo == 0, 1, topo)
    # if not np.array_equal(gpu_topo, expected_gpu_topo):
    #     mismatch = int(np.count_nonzero(gpu_topo != expected_gpu_topo))
    #     print(
    #         f"WARNING: GPU topo differs from the expected CPU convention at "
    #         f"{mismatch} cells; CPU topo is still used for both fields."
    #     )
    #     sys.exit()

    nt = len(steps)
    nx = topo.shape[1]
    cpu_ymean = np.empty((nt, nx), dtype=np.float64)
    gpu_ymean = np.empty((nt, nx), dtype=np.float64)
    difference_ymean = np.empty((nt, nx), dtype=np.float64)
    relative_error_ymean = np.empty((nt, nx), dtype=np.float64)
    times_minutes = np.empty(nt, dtype=np.float64)
    l2 = np.empty(nt, dtype=np.float64)
    rmse = np.empty(nt, dtype=np.float64)
    relative_l2 = np.empty(nt, dtype=np.float64)
    weighted_l2_3d = np.empty(nt, dtype=np.float64)
    relative_weighted_l2_3d = np.empty(nt, dtype=np.float64)

    topo_indices: np.ndarray | None = None
    atmosphere: np.ndarray | None = None
    for it, step in enumerate(steps):
        cpu_field = cpu.read_3d(variable, step)
        gpu_field = gpu.read_3d(variable, step)
        if cpu_field.shape != gpu_field.shape:
            raise ValueError(
                f"Shape mismatch at step {step:06d}: CPU {cpu_field.shape}, "
                f"GPU {gpu_field.shape}"
            )

        if topo_indices is None:
            topo_indices = validate_topography(topo, cpu_field.shape)
            atmosphere = atmospheric_mask(topo_indices, cpu_field.shape[0])
            print(np.arange(0,1024,64,dtype=int)/1024)
            print(topo[0,np.arange(0,1024,64,dtype=int)])

        cpu_surface = extract_near_surface(cpu_field, topo_indices).astype(
            np.float64, copy=False
        )
        gpu_surface = extract_near_surface(gpu_field, topo_indices).astype(
            np.float64, copy=False
        )
        difference = gpu_surface - cpu_surface

        cpu_ymean[it] = np.mean(cpu_surface, axis=0)
        gpu_ymean[it] = np.mean(gpu_surface, axis=0)
        difference_ymean[it] = np.mean(difference, axis=0)

        relative_error_ymean[it] = np.divide(
                    np.abs((gpu_ymean[it]-cpu_ymean[it])),
                    np.abs(cpu_ymean[it]),
                    out=np.full_like(cpu_ymean[it], np.nan),
                    where=np.abs(cpu_ymean[it]) >= RELATIVE_ERROR_MIN_REFERENCE,
                )

        valid = np.isfinite(cpu_surface) & np.isfinite(gpu_surface)
        if not np.any(valid):
            raise ValueError(f"No finite CPU/GPU surface pairs at step {step:06d}")
        error_values = difference[valid]
        cpu_values = cpu_surface[valid]
        #l2[it] = np.linalg.norm(error_values)
        l2[it] = np.sqrt(np.mean((error_values)**2))
        cpu_l2 = np.sqrt(np.mean(cpu_values**2))
        relative_l2[it] = l2[it] / cpu_l2 if cpu_l2 > 0 else np.nan

        ## cpu_l2 = np.linalg.norm(cpu_values)
        ## relative_l2[it] = l2[it] / cpu_l2 if cpu_l2 > 0.0 else np.nan

        error_3d = gpu_field.astype(np.float64, copy=False) - cpu_field
        weighted_l2_3d[it] = weighted_l2_norm(
            error_3d, rho, dz, mask=atmosphere
        )
        relative_weighted_l2_3d[it] = relative_weighted_l2_norm(
            error_3d,
            cpu_field,
            rho,
            dz,
            mask=atmosphere,
        )

        cpu_time = cpu.time_minutes(step)
        gpu_time = gpu.time_minutes(step)
        if not np.isclose(cpu_time, gpu_time):
            raise ValueError(
                f"Time mismatch at step {step:06d}: CPU={cpu_time} min, "
                f"GPU={gpu_time} min"
            )
        times_minutes[it] = cpu_time

        if it == 0 or (it + 1) % 10 == 0 or it + 1 == nt:
            print(f"Processed {it + 1:3d}/{nt} time steps (step {step:06d})")

    return {
        "steps": np.asarray(steps, dtype=np.int64),
        "time_minutes": times_minutes,
        "cpu_ymean": cpu_ymean,
        "gpu_ymean": gpu_ymean,
        "topo_indices":topo_indices,
        "difference_ymean": difference_ymean,
        "relative_error_ymean": relative_error_ymean,
        "l2": l2,
        "rmse": rmse,
        "relative_l2": relative_l2,
        "weighted_l2_3d": weighted_l2_3d,
        "relative_weighted_l2_3d": relative_weighted_l2_3d,
    }


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


def draw_hovmoller(
    data: np.ndarray,
    x_m: np.ndarray,
    time_minutes: np.ndarray,
    title: str,
    output_path: Path,
    clevs: np.ndarray,
    cmap: mpl.colors.Colormap,
    colorbar_label: str,
    extend: str,
) -> None:
    set_plot_defaults()
    fig, ax = plt.subplots(figsize=(10, 8), layout="constrained")
    mesh = draw_hovmoller_on_axis(
        ax, data, x_m, time_minutes, title, clevs, cmap, extend
    )
    colorbar = fig.colorbar(
        mesh,
        ax=ax,
        orientation="horizontal",
        extend=extend,
        pad=0.07,
        aspect=45,
    )
    colorbar.set_ticks(clevs[::2])
    colorbar.set_label(colorbar_label)

    fig.savefig(output_path, dpi=300, transparent=True)
    plt.close(fig)


def draw_combined_hovmoller(
    plot_specs: tuple[
        tuple[np.ndarray, str, np.ndarray, mpl.colors.Colormap, str, str], ...
    ],
    x_m: np.ndarray,
    time_minutes: np.ndarray,
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


def write_norm_csv(output_path: Path, comparison: dict[str, np.ndarray]) -> None:
    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "step",
                "time_minutes",
                "surface_l2",
                "surface_rmse",
                "surface_relative_l2",
                "weighted_l2_3d_rho_dz",
                "relative_weighted_l2_3d_rho_dz",
            ]
        )
        for row in zip(
            comparison["steps"],
            comparison["time_minutes"],
            comparison["l2"],
            comparison["rmse"],
            comparison["relative_l2"],
            comparison["weighted_l2_3d"],
            comparison["relative_weighted_l2_3d"],
            strict=True,
        ):
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu-case", type=Path, default=DEFAULT_CPU_CASE)
    parser.add_argument("--gpu-case", type=Path, default=DEFAULT_GPU_CASE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
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
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"CPU case: {args.cpu_case.resolve()}")
    print(f"GPU case: {args.gpu_case.resolve()}")
    cpu = CPUReader(args.cpu_case)
    gpu = GPUReader(args.gpu_case)

    if cpu.x.shape != gpu.x.shape or cpu.y.shape != gpu.y.shape:
        raise ValueError(
            f"Horizontal grid shape mismatch: CPU {(cpu.y.size, cpu.x.size)}, "
            f"GPU {(gpu.y.size, gpu.x.size)}"
        )
    if not np.allclose(cpu.z, gpu.z):
        raise ValueError("CPU levels after dropping level zero do not match GPU z_mid")
    gpu_rho = gpu.read_profile("rhobar")
    dz = layer_thickness(gpu.z)

    steps = common_steps(cpu, gpu, args.max_times)
    print(f"Common time steps selected: {len(steps)}")
    comparison = collect_comparison(cpu, gpu, args.variable, steps, gpu_rho, dz)

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
            args.output_dir / "hov_u_surface_ymean_VVMex.png",
            FIELD_CLEVS,
            field_cmap,
            "u [m s$^{-1}$]",
            "both",
        ),
        (
            comparison["cpu_ymean"],
            "(b) VVM",
            args.output_dir / "hov_u_surface_ymean_VVM.png",
            FIELD_CLEVS,
            field_cmap,
            "u [m s$^{-1}$]",
            "both",
        ),
        (
            comparison["relative_error_ymean"],
            "(c) Relative error",
            args.output_dir / "hov_u_surface_ymean_gpu_minus_cpu.png",
            DIFFERENCE_CLEVS,
            difference_cmap,
            "abs(VVMex-VVM)/abs(VVM)",
            "max",
        ),
    )
    for data, title, output_path, clevs, cmap, colorbar_label, extend in outputs:
        draw_hovmoller(
            data,
            cpu.x,
            comparison["time_minutes"],
            title,
            output_path,
            clevs,
            cmap,
            colorbar_label,
            extend,
        )
        print(f"Wrote {output_path}")

    combined_path = args.output_dir / "hov_u_surface_ymean_combined.png"
    combined_specs = tuple(
        (data, title, clevs, cmap, colorbar_label, extend)
        for data, title, _output_path, clevs, cmap, colorbar_label, extend in outputs
    )
    draw_combined_hovmoller(
        combined_specs,
        cpu.x,
        comparison["time_minutes"],
        combined_path,
    )
    print(f"Wrote {combined_path}")

    csv_path = args.output_dir / "near_surface_u_norms.csv"
    write_norm_csv(csv_path, comparison)
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
