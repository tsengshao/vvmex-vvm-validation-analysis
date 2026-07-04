import os
import re
import h5py
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib import font_manager


# ============================================================
# User settings
# ============================================================

base_dir = "../.."

experiments = {
    "advection_u": "th",
    "advection_v": "th",
    "advection_w": "th",
    "stretching": "eta",
    "twisting": "eta",
}

step_min = 1
step_max = 30

# Model time step.
# Time on the x-axis is computed as:
#     time_s = step * dt_seconds
dt_seconds = 50.0

# For x-y plane:
# field[k_level, :, :]
k_level = 16

eps = 1.0e-30

output_csv = "relative_l2_theta_eta_selected_experiments.csv"

# GMD-style figure naming: Arabic numerals, e.g. fig01
output_png = "fig01_relative_l2_theta_eta_selected_experiments.png"
output_pdf = "fig01_relative_l2_theta_eta_selected_experiments.pdf"


# ============================================================
# GMD-style matplotlib settings
# ============================================================

def setup_gmd_figure_style():
    """
    Style choices:
    - one sans-serif font family
    - embedded TrueType fonts in PDF/PS
    - CVD-friendly line colors
    - clean journal-style figure without a title
    """

    available_fonts = {f.name for f in font_manager.fontManager.ttflist}

    if "Arial" in available_fonts:
        selected_font = "Arial"
    elif "Helvetica" in available_fonts:
        selected_font = "Helvetica"
    else:
        selected_font = "DejaVu Sans"

    plt.rcParams.update({
        # Font
        "font.family": "sans-serif",
        "font.sans-serif": [selected_font],
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,

        # Embed editable TrueType fonts in vector output
        "pdf.fonttype": 42,
        "ps.fonttype": 42,

        # Avoid excessive visual weight
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.width": 0.6,
        "ytick.minor.width": 0.6,

        # Output quality
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
    })

    return selected_font


selected_font = setup_gmd_figure_style()
print(f"[Figure style] Using font family: {selected_font}")


# ============================================================
# File-path helpers
# ============================================================

def gpu_dir(exp):
    return os.path.join(base_dir, 'gpu', exp)


def vvm_dir(exp):
    return os.path.join(base_dir, 'cpu', exp, 'archive')


def gpu_file(exp, step):
    return os.path.join(gpu_dir(exp), f"vvm_output_{step:06d}.h5")


def vvm_stream(var):
    if var == "th":
        return "Thermodynamic"
    else:
        return "Dynamic"


def vvm_file(exp, var, step):
    stream = vvm_stream(var)
    return os.path.join(vvm_dir(exp), f"{exp}.L.{stream}-{step:06d}.nc")


# ============================================================
# Step discovery
# ============================================================

def discover_gpu_steps(exp):
    folder = gpu_dir(exp)

    if not os.path.isdir(folder):
        print(f"[Missing GPU directory] {folder}")
        return set()

    pattern = re.compile(r"vvm_output_(\d{6})\.h5$")
    steps = set()

    for name in os.listdir(folder):
        match = pattern.match(name)
        if match:
            step = int(match.group(1))
            if step_min <= step <= step_max:
                steps.add(step)

    return steps


def discover_vvm_steps(exp, var):
    folder = vvm_dir(exp)

    if not os.path.isdir(folder):
        print(f"[Missing VVM directory] {folder}")
        return set()

    stream = vvm_stream(var)
    pattern = re.compile(rf"{re.escape(exp)}\.L\.{stream}-(\d{{6}})\.nc$")
    steps = set()

    for name in os.listdir(folder):
        match = pattern.match(name)
        if match:
            step = int(match.group(1))
            if step_min <= step <= step_max:
                steps.add(step)

    return steps


def discover_common_steps(exp, var):
    gpu_steps = discover_gpu_steps(exp)
    vvm_steps = discover_vvm_steps(exp, var)

    common_steps = sorted(gpu_steps & vvm_steps)

    if not common_steps:
        print(f"[{exp}] No common GPU/VVM steps found.")

    missing_gpu = sorted(vvm_steps - gpu_steps)
    missing_vvm = sorted(gpu_steps - vvm_steps)

    if missing_gpu:
        print(f"[{exp}] Missing GPU files for steps: {missing_gpu}")

    if missing_vvm:
        print(f"[{exp}] Missing VVM {var} files for steps: {missing_vvm}")

    return common_steps


# ============================================================
# Data readers
# ============================================================

def read_gpu_var(exp, var, step):
    path = gpu_file(exp, step)

    with h5py.File(path, "r") as f:
        if "Step0" not in f:
            raise KeyError(f"Missing Step0 in {path}")

        if var not in f["Step0"]:
            raise KeyError(f"Missing {var} in {path}")

        return np.array(f["Step0"][var][:])


def read_vvm_var(exp, var, step):
    path = vvm_file(exp, var, step)

    with xr.open_dataset(path) as ds:
        if var not in ds:
            raise KeyError(f"Missing {var} in {path}")

        # Same convention as your original code:
        # vvm_var = np.array(data_raw[var][0, 1:])
        return np.array(ds[var][0, 1:])


# ============================================================
# Slice selection
# ============================================================

def get_slice(exp, var, gpu_data, vvm_data):
    """
    Assumed array convention:
        field[z, y, x]

    advection_w:
        x-z plane at y=4:
            field[:, y_mid, :]

    all other cases:
        x-y plane at fixed z:
            field[k_level, :, :]
    """

    if gpu_data.shape != vvm_data.shape:
        raise ValueError(f"Shape mismatch: GPU {gpu_data.shape}, VVM {vvm_data.shape}")

    nz, ny, nx = gpu_data.shape

    # if exp == "advection_w":
    #     # Requested x-z plane.
    #     # Use y=4. For exact middle plane, replace this with:
    #     # y_mid = ny // 2
    #     # y_mid = 4

    #     if y_mid >= ny:
    #         raise ValueError(f"y_mid={y_mid} is outside ny={ny}")

    #     gpu_slice = gpu_data[:, y_mid, :]
    #     vvm_slice = vvm_data[:, y_mid, :]

    #     slice_info = f"x-z plane, y={y_mid}"

    # else:
    if k_level >= nz:
        raise ValueError(f"k_level={k_level} is outside nz={nz}")

    gpu_slice = gpu_data[k_level, :, :]
    vvm_slice = vvm_data[k_level, :, :]

    slice_info = f"x-y plane, k={k_level}"

    return gpu_slice, vvm_slice, slice_info


# ============================================================
# Relative L2 norm
# ============================================================

def relative_l2(gpu_slice, vvm_slice):
    gpu_slice = np.asarray(gpu_slice)
    vvm_slice = np.asarray(vvm_slice)

    if gpu_slice.shape != vvm_slice.shape:
        raise ValueError(f"Slice shape mismatch: GPU {gpu_slice.shape}, VVM {vvm_slice.shape}")

    mask = np.isfinite(gpu_slice) & np.isfinite(vvm_slice)

    if not np.any(mask):
        return np.nan, np.nan, np.nan

    diff = gpu_slice[mask] - vvm_slice[mask]
    ref = vvm_slice[mask]

    diff_l2 = np.sqrt(np.sum(diff ** 2))
    ref_l2 = np.sqrt(np.sum(ref ** 2))

    if ref_l2 < eps:
        rel_l2 = np.nan
    else:
        rel_l2 = diff_l2 / ref_l2

    return rel_l2, diff_l2, ref_l2


# ============================================================
# Main calculation
# ============================================================

records = []

for exp, var in experiments.items():
    steps = discover_common_steps(exp, var)

    print(f"\n[{exp}] variable={var}, common steps={steps}")

    for step in steps:
        try:
            gpu_data = read_gpu_var(exp, var, step)
            vvm_data = read_vvm_var(exp, var, step)

            gpu_slice, vvm_slice, slice_info = get_slice(exp, var, gpu_data, vvm_data)

            rel_l2, diff_l2, ref_l2 = relative_l2(gpu_slice, vvm_slice)

            time_s = step * dt_seconds

            records.append({
                "experiment": exp,
                "variable": var,
                "step": step,
                "time_s": time_s,
                "slice": slice_info,
                "relative_l2": rel_l2,
                "diff_l2": diff_l2,
                "ref_l2": ref_l2,
            })

            print(
                f"[{exp}] step={step:06d}, "
                f"time={time_s:.1f} s, "
                f"var={var}, "
                f"slice={slice_info}, "
                f"rel_l2={rel_l2}, "
                f"diff_l2={diff_l2:.6e}, "
                f"ref_l2={ref_l2:.6e}"
            )

        except Exception as e:
            time_s = step * dt_seconds

            print(f"[Warning] exp={exp}, var={var}, step={step:06d}: {e}")

            records.append({
                "experiment": exp,
                "variable": var,
                "step": step,
                "time_s": time_s,
                "slice": "error",
                "relative_l2": np.nan,
                "diff_l2": np.nan,
                "ref_l2": np.nan,
            })


df = pd.DataFrame(records)
df.to_csv(output_csv, index=False)

print(f"\nSaved CSV: {output_csv}")
print(df)


# ============================================================
# One figure: relative L2 norm versus time
# ============================================================

# Larger journal-style figure.
# 13.0 cm x 8.0 cm.
# This keeps the text readable but prevents labels from visually dominating.
cm_to_inch = 1.0 / 2.54
fig_width = 13.0 * cm_to_inch
fig_height = 8.0 * cm_to_inch

fig, ax = plt.subplots(figsize=(fig_width, fig_height))


# Okabe-Ito style CVD-friendly colors.
plot_styles = {
    "advection_u": {
        "color": "#0072B2",      # blue
        "linestyle": "-",
        "marker": "o",
        "linewidth": 1.6,
        "markersize": 4.5,
        "markerfacecolor": "none",
        "markeredgewidth": 0.9,
        "zorder": 5,
    },
    "advection_v": {
        "color": "#D55E00",      # vermillion
        "linestyle": "--",
        "marker": "s",
        "linewidth": 1.6,
        "markersize": 4.5,
        "markerfacecolor": "none",
        "markeredgewidth": 0.9,
        "zorder": 6,
    },
    "advection_w": {
        "color": "#009E73",      # bluish green
        "linestyle": "-.",
        "marker": "^",
        "linewidth": 1.6,
        "markersize": 4.6,
        "markerfacecolor": "none",
        "markeredgewidth": 0.9,
        "zorder": 4,
    },
    "stretching": {
        "color": "#CC79A7",      # reddish purple
        "linestyle": ":",
        "marker": "D",
        "linewidth": 1.8,
        "markersize": 4.4,
        "markerfacecolor": "none",
        "markeredgewidth": 0.9,
        "zorder": 3,
    },
    "twisting": {
        "color": "#000000",      # black
        "linestyle": "-",
        "marker": "x",
        "linewidth": 1.5,
        "markersize": 4.8,
        "markeredgewidth": 0.9,
        "zorder": 2,
    },
}


# Plotting-only x offsets in seconds.
# These do not change the calculated data.
# They only prevent nearly identical curves from hiding each other.
# ±0.05 step corresponds to ±2.5 s because dt = 50 s.
x_offsets_seconds = {
    "advection_u": -0.05 * dt_seconds,
    "advection_v":  0.05 * dt_seconds,
    "advection_w":  0.00 * dt_seconds,
    "stretching":   0.00 * dt_seconds,
    "twisting":     0.00 * dt_seconds,
}


legend_labels = {
    "advection_u": r"Advection $u$, $\theta$",
    "advection_v": r"Advection $v$, $\theta$",
    "advection_w": r"Advection $w$, $\theta$",
    "stretching":  r"Stretching, $\eta$",
    "twisting":    r"Twisting, $\eta$",
}


# Log-scale plotting floor.
# This is only for visualization if a relative L2 value is exactly zero.
# The original CSV values are unchanged.
log_plot_floor = 1.0e-16


for exp, var in experiments.items():
    sub = df[df["experiment"] == exp].copy()
    sub = sub.sort_values("time_s")

    y_raw = sub["relative_l2"].to_numpy(dtype=float)
    valid = np.isfinite(y_raw)

    if np.any(valid):
        style = plot_styles.get(exp, {})

        x_plot = sub["time_s"].to_numpy(dtype=float) + x_offsets_seconds.get(exp, 0.0)
        y_plot = y_raw.copy()

        zero_or_negative = valid & (y_plot <= 0.0)
        if np.any(zero_or_negative):
            print(
                f"[Plot floor] {exp}: "
                f"{np.sum(zero_or_negative)} non-positive relative_l2 value(s) "
                f"shown at {log_plot_floor:.1e} for log-scale plotting."
            )
            y_plot[zero_or_negative] = log_plot_floor

        ax.plot(
            x_plot[valid],
            y_plot[valid],
            label=legend_labels.get(exp, f"{exp} ({var})"),
            **style,
        )
    else:
        print(f"[Not plotted] {exp} ({var}): all relative_l2 values are NaN")


ax.set_xlabel("Time (s)")
ax.set_ylabel(r"Relative $L_2$ norm")
# ax.set_yscale("log")
#ax.set_ylim(5.0e-9, 5.0e-8)
ax.set_ylim(1.0e-9, 6.0e-8)

ax.grid(
    True,
    which="major",
    linestyle="--",
    linewidth=0.45,
    alpha=0.55,
)

ax.grid(
    True,
    which="minor",
    linestyle=":",
    linewidth=0.35,
    alpha=0.35,
)

ax.tick_params(direction="out", length=3.0, width=0.8)
ax.tick_params(which="minor", direction="out", length=1.8, width=0.6)

# Keep the legend inside the figure so line/marker meanings are clear.
ax.legend(
    frameon=False,
    loc="best",
    handlelength=2.8,
    handletextpad=0.6,
    borderaxespad=0.3,
)

fig.tight_layout()

fig.savefig(output_png, dpi=300)
fig.savefig(output_pdf)

print(f"Saved PNG: {output_png}")
print(f"Saved PDF: {output_pdf}")

for path in [output_png, output_pdf]:
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / 1024.0 / 1024.0
        print(f"[File size] {path}: {size_mb:.3f} MB")

plt.show()
