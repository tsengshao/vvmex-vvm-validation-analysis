#!/bin/bash
set -euo pipefail

SRCDIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTDIR="${SRCDIR}/scripts"
export GASCRP="$GASCRP:${SCRIPTDIR}/GRADSLIB/"
#python="~/miniforge3/envs/py311/bin/python"
#export PATH="$(dirname ${python}):$PATH"

for command in python opengrads; do
    if ! command -v "${command}" >/dev/null 2>&1; then
        echo "Error: '${command}' was not found in PATH. Please install it and try again." >&2
        exit 1
    fi
done

# Write generated figures to the repository root.
OUTDIR="${SRCDIR}/OUTPUT_FIGURES"
mkdir -p ${OUTDIR}

# rotate python script
export PYROTATE="${SCRIPTDIR}/tools/rotate_pdf_clockwise.py"

# fig 3, p3 test
cd "${SCRIPTDIR}/exp_p3"
opengrads -a 2.6666667 -blcx exp_p3_err.gs
opengrads -blcx  exp_p3.gs
python ${PYROTATE}  p3_l2_err.pdf ${OUTDIR}/f03_c_p3err.pdf
python ${PYROTATE}  fig/VVMex_000006.pdf ${OUTDIR}/f03_a.pdf
python ${PYROTATE}  fig/VVMex_000045.pdf ${OUTDIR}/f03_b.pdf
cd ${SRCDIR}

# fig 4, indiviual componet
cd "${SCRIPTDIR}/exp_dycore"
python exp_induval.py
cp fig01_relative_l2_theta_eta_selected_experiments.pdf ${OUTDIR}/f04.pdf
cd ${SRCDIR}

# fig 5, mountain wave
cd "${SCRIPTDIR}/exp_mountain"
opengrads -blcx exp_mountain.gs
python ${PYROTATE} mountain_VVMex.pdf ${OUTDIR}/f05.pdf
cd ${SRCDIR}

# fig 6, sea_land_mountain
cd "${SCRIPTDIR}/exp_sea_land_mountain"
python compare_near_surface.py --case urban
python compare_near_surface.py --case grass
opengrads -blcx initial_profile.gs
cp ./fig/hov_u_surface_ymean_grass_combined.png ${OUTDIR}/f06.png
cp ./fig/hov_u_surface_ymean_urban_combined.png ${OUTDIR}/fB02.png
python ${PYROTATE} ./fig/slm_initial.pdf ${OUTDIR}/fA01.pdf
cd ${SRCDIR}

# fig 7, pbl
cd "${SCRIPTDIR}/exp_pbl"
opengrads -a 1.7777778 -blcx exp_pbl.gs
opengrads -a 1.7777778 -blcx tg.gs
opengrads -blcx initial_profile.gs
python ${PYROTATE} ./fig/pbl_initial.pdf ${OUTDIR}/fA02.pdf
python ${PYROTATE} ./fig/tg2_VVMex_urban.pdf ${OUTDIR}/f07ab.pdf
python ${PYROTATE} ./fig/tg2_VVMex_grass.pdf ${OUTDIR}/f07cd.pdf
python ${PYROTATE} ./fig/tg2_VVMex_evergreen.pdf ${OUTDIR}/fB04.pdf
python ${PYROTATE} ./fig/tg_VVMex_grass.pdf ${OUTDIR}/fB03.pdf
cd ${SRCDIR}

# fig 8, rcemip
cd "${SCRIPTDIR}/exp_rcemip"
opengrads -blcx "draw_water_VVMex.gs 721 721"
opengrads -blcx "draw_water_VVM.gs 721 721"
python exp_plot_series.py
opengrads -blcx initial_profile.gs

cp ./figs_cwv_VVMex/whi_exp_000721.png ${OUTDIR}/f08a.png
cp ./figs_cwv_VVM/whi_exp_000721.png ${OUTDIR}/f08b.png
cp ./fig_water_path_timeseries.pdf ${OUTDIR}/f08cd.pdf
python ${PYROTATE} ./fig_rce_initial.pdf ${OUTDIR}/fA03.pdf
cd ${SRCDIR}

# fig 9, speed up
cd "${SCRIPTDIR}/speedup"
python performance.py
cp ./f01_vvm_gpu_timing_gmd.pdf ${OUTDIR}/f09.pdf
cd ${SRCDIR}

# fig B1, dry warm bubble
cd "${SCRIPTDIR}/exp_2dbubble"
opengrads -blcx exp_2dbubble.gs
opengrads -a 2.6666667 -blcx exp_err_2dbubble.gs
cp ./fig_VVMex/bubble2d_VVMex_000001.png ${OUTDIR}/fB01a.png
cp ./fig_VVMex/bubble2d_VVMex_000011.png ${OUTDIR}/fB01b.png
cp ./fig_VVMex/bubble2d_VVMex_000021.png ${OUTDIR}/fB01c.png
python ${PYROTATE} ./error_bubble2d.pdf ${OUTDIR}/fB01d.pdf
cd $SRCDIR

# fig B5, taiwanvvm
cd "${SCRIPTDIR}/exp_taiwanvvm"
opengrads -a 1.7777778 -blcx taiwanvvm.gs
python ${PYROTATE} ./fig/combine_taiwanvvm_2048.pdf ${OUTDIR}/fB05.pdf
cd $SRCDIR
