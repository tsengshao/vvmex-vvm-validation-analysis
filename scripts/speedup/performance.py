import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pathlib import Path

# ============================================================
# Data: mean_s from timing summaries
# ============================================================

data = [
    # GPUs, component, mean_s
    (8,  "total_vvm", 64182.7327),
    (8,  "dynamics_wind_total", 31102.9425),
    (8,  "microphysics", 13312.5297),
    (8,  "dynamics_thermo", 9026.7011),
    (8,  "dynamics_vorticity", 3302.5842),
    (8,  "radiation", 2672.3222),
    (8,  "halo_exchange", 2550.7065),
    (8,  "io", 1066.4419),
    (8,  "turbulence", 672.3864),
    (8,  "area_mean_nudging", 317.5380),
    (8,  "dynamics_diagnostics", 130.1988),
    (8,  "sponge_layer", 10.1130),
    (8,  "land", 8.0938),
    (8,  "surface", 2.8732),
    (8,  "time_integrator_thermo", 2.6423),
    (8,  "time_integrator_vorticity", 1.0310),
    (8,  "initialize", 1.0240),

    (16, "total_vvm", 32945.6672),
    (16, "dynamics_wind_total", 16934.2224),
    (16, "microphysics", 5568.2048),
    (16, "dynamics_thermo", 5041.9438),
    (16, "dynamics_vorticity", 1820.2466),
    (16, "radiation", 1332.1804),
    (16, "halo_exchange", 1300.1000),
    (16, "turbulence", 361.7414),
    (16, "io", 276.5342),
    (16, "area_mean_nudging", 160.0913),
    (16, "dynamics_diagnostics", 92.4476),
    (16, "initialize", 28.6178),
    (16, "sponge_layer", 12.3597),
    (16, "land", 5.3457),
    (16, "surface", 3.8863),
    (16, "time_integrator_thermo", 3.3751),
    (16, "time_integrator_vorticity", 1.3124),

    (32, "total_vvm", 18070.9018),
    (32, "dynamics_wind_total", 9428.6386),
    (32, "dynamics_thermo", 2817.2723),
    (32, "microphysics", 2229.4000),
    (32, "turbulence", 705.7980),
    (32, "dynamics_vorticity", 1015.8387),
    (32, "halo_exchange", 721.2244),
    (32, "radiation", 669.0310),
    (32, "io", 297.5576),
    (32, "area_mean_nudging", 82.3631),
    (32, "dynamics_diagnostics", 60.6851),
    (32, "initialize", 15.1656),
    (32, "sponge_layer", 12.2113),
    (32, "surface", 3.6668),
    (32, "land", 3.6375),
    (32, "time_integrator_thermo", 3.3336),
    (32, "time_integrator_vorticity", 1.2830),

    (64, "total_vvm", 10578.3102),
    (64, "dynamics_wind_total", 5461.1856),
    (64, "dynamics_thermo", 1800.5622),
    (64, "microphysics", 1048.1131),
    (64, "turbulence", 610.9504),
    (64, "halo_exchange", 440.5926),
    (64, "dynamics_vorticity", 631.8437),
    (64, "radiation", 333.6015),
    (64, "io", 114.8697),
    (64, "dynamics_diagnostics", 49.9471),
    (64, "area_mean_nudging", 43.9453),
    (64, "initialize", 17.1926),
    (64, "sponge_layer", 11.8622),
    (64, "surface", 3.3796),
    (64, "time_integrator_thermo", 3.2361),
    (64, "land", 2.7421),
    (64, "time_integrator_vorticity", 1.2436),
]

# ============================================================
# Convert to dataframe
# ============================================================

df = pd.DataFrame(data, columns=["gpus", "component", "mean_s"])
wide = df.pivot(index="gpus", columns="component", values="mean_s").sort_index()

gpus = wide.index.to_numpy()
total_s = wide["total_vvm"]
total_h = total_s / 3600.0

# ============================================================
# Scaling metrics
# ============================================================

baseline_gpu = 8
baseline_total_s = total_s.loc[baseline_gpu]

speedup = baseline_total_s / total_s
ideal_speedup = gpus / baseline_gpu
parallel_efficiency = speedup / ideal_speedup

# CPU reference run.  Its plotting coordinate is intentionally separate from
# the numeric GPU coordinates so the existing GPU scaling geometry is retained.
cpu_x = 5
cpu_count = 1024
cpu_total_h = 71.716667
cpu_speedup = (baseline_total_s / 3600.0) / cpu_total_h

# ============================================================
# GMD-oriented plot style
# ============================================================
# - Single sans-serif font family.
# - TrueType font embedding in vector outputs.
# - Color-vision-deficiency-friendly line colors based on Okabe-Ito.
# - CVD-friendly sequential heatmap using cividis, lightly truncated to avoid
#   excessively dark near-zero cells.
# - No long figure title: case details belong in the manuscript caption.

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.0,
    "axes.labelsize": 8.0,
    "axes.titlesize": 8.5,
    "legend.fontsize": 7.2,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
})

# Okabe-Ito palette: generally robust for common CVD cases.
runtime_color = "#0072B2"  # blue
speedup_color = "#D55E00"  # vermilion
ideal_color = "0.20"

base_cmap = mpl.colormaps["cividis"]
heatmap_cmap = LinearSegmentedColormap.from_list(
    "cividis_truncated",
    base_cmap(np.linspace(0.12, 0.95, 256)),
)
heatmap_norm = Normalize(vmin=0.0, vmax=55.0)

base_cmap = mpl.colormaps["afmhot_r"]
heatmap_cmap = LinearSegmentedColormap.from_list(
    "cividis_truncated",
    base_cmap(np.linspace(0.001, 0.75, 256)),
)
heatmap_norm = Normalize(vmin=2.5, vmax=25.0)

# ============================================================
# Heatmap data
# ============================================================

main_components = [
    "dynamics_wind_total",
    "microphysics",
    "dynamics_thermo",
    "dynamics_vorticity",
    "radiation",
    "halo_exchange",
    "turbulence",
    "io",
    "area_mean_nudging",
    "dynamics_diagnostics",
]

shown_sum_s = wide[main_components].sum(axis=1)
others_s = total_s - shown_sum_s

if (others_s < -1e-6).any():
    print("Warning: selected component timers exceed total_vvm.")
    print("This suggests overlapping or inclusive timers.")
    print(others_s)

others_s = others_s.clip(lower=0.0)

wide_for_heatmap = wide[main_components].copy()
wide_for_heatmap["others"] = others_s

components_for_heatmap = main_components + ["others"]
component_fraction = wide_for_heatmap.div(total_s, axis=0) * 100.0
heatmap_data = component_fraction[components_for_heatmap].T

print("Heatmap column sums (%):")
print(heatmap_data.sum(axis=0).round(3))

component_labels = {
    "dynamics_wind_total": "Wind solver",
    "microphysics": "Microphysics",
    "dynamics_thermo": "Dynamics\nthermo_vars",
    "dynamics_vorticity": "Dynamics\nvorticity_vars",
    "radiation": "Radiation",
    "halo_exchange": "Halo exchange",
    "turbulence": "Turbulence",
    "io": "Output",
    "area_mean_nudging": "Nudging",
    "dynamics_diagnostics": "Diagnostics",
    "others": "Others\n(including land)",
}



cm = 1 / 2.54
fig = plt.figure(figsize=(18.0 * cm, 11.5 * cm), constrained_layout=False)


gs = fig.add_gridspec(
    nrows=1,
    ncols=2,
    width_ratios=[1.8, 1.0],
    wspace=0.52,
)

# ============================================================
# Panel (a): total runtime and speedup
# ============================================================

gs_left = gs[0, 0].subgridspec(
    nrows=2,
    ncols=1,
    height_ratios=[1, 9],
    hspace=0.06,
)

ax1_top = fig.add_subplot(gs_left[0, 0])
ax1 = fig.add_subplot(gs_left[1, 0], sharex=ax1_top)
ax1_top.set_zorder(3)

# The CPU reference is isolated in the upper part of the broken runtime axis.
point_cpu_runtime, = ax1_top.plot(
    cpu_x,
    cpu_total_h,
    marker="o",
    linestyle="none",
    markersize=4.6,
    markerfacecolor="white",
    markeredgecolor=runtime_color,
    markeredgewidth=1.2,
    zorder=4,
)

line_runtime, = ax1.plot(
    gpus,
    total_h,
    marker="o",
    linewidth=1.5,
    markersize=4.2,
    color=runtime_color,
    label="Wall-clock time",
)

ax1.set_xlabel("Number of GPUs")
ax1.set_ylabel("Total runtime (h)")
resource_ticks = np.concatenate(([cpu_x], gpus))
resource_labels = ["", *[str(gpu) for gpu in gpus]]
ax1.set_xticks(resource_ticks)
ax1.set_xticklabels(resource_labels)
ax1.annotate(
    f"{cpu_count}\nCPUs",
    xy=(cpu_x, 0),
    xycoords=ax1.get_xaxis_transform(),
    xytext=(-5, -6.5),
    textcoords="offset points",
    ha="center",
    va="top",
    fontsize=mpl.rcParams["xtick.labelsize"],
    annotation_clip=False,
)
ax1.set_xlim(2, 67)
ax1_top.set_title("(a) Scaling performance", loc="left", pad=3)
ax1_top.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
ax1_top.grid(True, color="0.88", linewidth=0.6)
ax1.grid(True, color="0.88", linewidth=0.6)

ax1_top.set_ylim(70.5, 72.5)
ax1.set_ylim(0, 19.0)
ax1.set_yticks(np.arange(0,19.1,2.5))

ax1_top.tick_params(axis="y", labelcolor=runtime_color)
ax1.tick_params(axis="y", labelcolor=runtime_color)

# Hide the touching spines and draw conventional broken-axis marks.
ax1_top.spines["bottom"].set_visible(False)
ax1.spines["top"].set_visible(False)
break_size = 0.012
break_kwargs = dict(color="black", clip_on=False, linewidth=0.7)
ax1_top.plot(
    (-break_size, +break_size),
    (-break_size, +break_size),
    transform=ax1_top.transAxes,
    **break_kwargs,
)
ax1_top.plot(
    (1 - break_size, 1 + break_size),
    (-break_size, +break_size),
    transform=ax1_top.transAxes,
    **break_kwargs,
)
ax1.plot(
    (-break_size, +break_size),
    (1 - break_size, 1 + break_size),
    transform=ax1.transAxes,
    **break_kwargs,
)
ax1.plot(
    (1 - break_size, 1 + break_size),
    (1 - break_size, 1 + break_size),
    transform=ax1.transAxes,
    **break_kwargs,
)

ax1b = ax1.twinx()
ax1b.spines["top"].set_visible(False)

line_speedup, = ax1b.plot(
    gpus,
    speedup,
    marker="s",
    linewidth=1.5,
    markersize=4.0,
    linestyle="--",
    color=speedup_color,
    label="Measured speedup",
)

ax1b.plot(
    cpu_x,
    cpu_speedup,
    marker="s",
    linestyle="none",
    markersize=4.4,
    markerfacecolor="white",
    markeredgecolor=speedup_color,
    markeredgewidth=1.2,
    zorder=4,
)

line_ideal, = ax1b.plot(
    gpus,
    ideal_speedup,
    linewidth=1.2,
    linestyle=":",
    color=ideal_color,
    label="Ideal speedup",
)

ax1b.set_ylabel("Speedup (8 GPUs = 1)")
#ax1b.set_ylim(0, ideal_speedup.max() * 1.14)
# Match the right-axis upper limit to half of the lower runtime-axis limit.
ax1b.set_yticks([0, 1, 2, 4, 6, 8, 10])
ax1b.set_ylim(0, ax1.get_ylim()[1] * 2 / 5)
ax1b.tick_params(axis="y", labelcolor=speedup_color)

# Keep axis spines neutral. The color coding is only on tick labels and curves.
for ax in [ax1_top, ax1, ax1b]:
    for spine in ["left", "right", "top", "bottom"]:
        ax.spines[spine].set_color("black")
        ax.spines[spine].set_linewidth(0.7)

# Parallel-efficiency labels; use a space before the percent sign.
for x, y, eff in zip(gpus, speedup, parallel_efficiency):
    dx = 20 if x == baseline_gpu else -1
    dy = -10 if x == baseline_gpu else 5
    ha = "right" if x == baseline_gpu else "center"
    ax1b.annotate(
        f"{eff * 100:.0f} %",
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        ha=ha,
        va="bottom",
        fontsize=7.0,
        color="0.10",
    )

# Legend inside the figure, with explicit symbols and line styles.
legend = ax1_top.legend(
    [line_runtime, point_cpu_runtime, line_speedup, line_ideal],
    ["Wall-clock time", "1024 CPUs", "Measured speedup", "Ideal speedup"],
    loc="upper right",
    frameon=True,
    handlelength=2.6,
    borderpad=0.2,
)
legend.set_zorder(10)

# ============================================================
# Panel (b): component fraction heatmap
# ============================================================

ax2 = fig.add_subplot(gs[0, 1])

im = ax2.imshow(
    heatmap_data,
    aspect="auto",
    origin="upper",
    cmap=heatmap_cmap,
    norm=heatmap_norm,
)

ax2.set_xticks(np.arange(len(gpus)))
ax2.set_xticklabels(gpus)
ax2.set_yticks(np.arange(len(components_for_heatmap)))
ax2.set_yticklabels([component_labels[c] for c in components_for_heatmap])
ax2.set_xlabel("Number of GPUs")
ax2.set_title("(b) Component time fraction", loc="left", pad=3)

# Cell grid lines.
ax2.set_xticks(np.arange(-0.5, len(gpus), 1), minor=True)
ax2.set_yticks(np.arange(-0.5, len(components_for_heatmap), 1), minor=True)
ax2.grid(which="minor", color="white", linestyle="-", linewidth=0.65)
ax2.tick_params(which="minor", bottom=False, left=False)

# Colorbar with unit in the label. Ticks stay numeric to reduce clutter.
cbar = fig.colorbar(im, ax=ax2, pad=0.016, fraction=0.046,extend='max')
cbar.set_label("Share of total runtime (%)")
#cbar.set_ticks([0, 10, 20, 30, 40, 50])
cbar.set_ticks([5, 10, 15, 20, 25])
cbar.outline.set_linewidth(0.6)

# Cell labels with automatic contrast for readability.
for i in range(len(components_for_heatmap)):
    for j in range(len(gpus)):
        value = heatmap_data.iloc[i, j]
        rgba = heatmap_cmap(heatmap_norm(value))
        luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        text_color = "black" if luminance > 0.50 else "white"
        ax2.text(
            j,
            i,
            f"{value:.1f}",
            ha="center",
            va="center",
            fontsize=6.5,
            color=text_color,
        )

for ax in [ax1_top, ax1, ax2]:
    ax.tick_params(direction="out")

# fig.subplots_adjust(
#     left=0.075,
#     right=0.970,
#     top=0.925,
#     bottom=0.175,
# )

fig.suptitle(
    "VVMex performance for 500 m TaiwanVVM on NVIDIA H200\n"
    r"($2048 \times 2048 \times 70$ grid, 1 d, $\Delta t = 1$ s; 8 GPUs per node)",
    fontsize=10,
    fontweight="normal",
    y=0.975,
    linespacing=1.15,
)

fig.subplots_adjust(
    left=0.07,
    right=0.96,
    top=0.85,
    bottom=0.20,
)



# ============================================================
# Save journal-ready outputs
# ============================================================

out_dir = Path("./")
pdf_path = out_dir / "f01_vvm_gpu_timing_gmd.pdf"
png_path = out_dir / "f01_vvm_gpu_timing_gmd.png"

fig.savefig(pdf_path, bbox_inches="tight", metadata={"Creator": "Matplotlib"})
fig.savefig(png_path, bbox_inches="tight")

#plt.show()

plt.close(fig)

print(f"Saved {pdf_path}")
print(f"Saved {png_path}")
