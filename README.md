# VVM and VVMex Analysis

This repository contains analysis and plotting scripts for comparing simulation
output from **VVMex** and **VVM**.  The workflow covers several experiments,
including P3, dynamical-core, mountain-wave, sea--land--mountain, planetary
boundary layer (PBL), RCEMIP, performance, dry-bubble, and TaiwanVVM cases.

The scripts use:

- **OpenGrADS** for GrADS (`.gs`) data processing and figures;
- **Python** for NetCDF/HDF5 processing, diagnostics, and plots; and
- the Conda environment specified in [`environment.yml`](environment.yml).

## Repository layout

| Path | Purpose |
| --- | --- |
| `VVM/` | VVM simulation outputs used by the comparisons. |
| `VVMex/` | VVMex simulation outputs used by the comparisons. |
| `DATA/` | Derived NetCDF input data used by selected plotting scripts. |
| `scripts/` | Experiment-specific Python and OpenGrADS analysis scripts. |
| `scripts/GRADSLIB/` | Shared GrADS utility scripts. |
| `run.sh` | Runs the complete analysis and figure-generation workflow. |
| `OUTPUT_FIGURES/` | Final figures produced by `run.sh`. |

## Requirements

- [Conda](https://docs.conda.io/) or [Mamba](https://mamba.readthedocs.io/en/latest/index.html)
- [OpenGrADS](http://opengrads.org) available as the `opengrads` command
- VVM and VVMex data arranged in the repository's `VVM/`, `VVMex/`, and
  `DATA/` directories

`environment.yml` installs Python 3.11 and the required Python packages,
including `vvmtools`, `h5py`, `xarray`, `netcdf4`, `numpy`, `pandas`,
`matplotlib`, and `pypdf`.  OpenGrADS is installed separately, so make sure
that [`opengrads`](http://opengrads.org) is on your `PATH` before running the workflow.

## Create the Python environment

Using [Mamba](https://mamba.readthedocs.io/en/latest/index.html):

```bash
mamba env create -f environment.yml
mamba activate vvm-vvmex-analysis
```

Or using Conda:

```bash
conda env create -f environment.yml
conda activate vvm-vvmex-analysis
```

If the environment already exists and `environment.yml` changes, update it
with either `mamba env update -f environment.yml` or
`conda env update -f environment.yml`.

## Run the full workflow

From the repository root, activate the environment and run:

```bash
bash run.sh
```

The script checks that both `python` and `opengrads` are available, adds the
repository's shared GrADS library to `GASCRP`, runs the experiment scripts, and
collects the final PDF and PNG files in:

```text
OUTPUT_FIGURES/
```

Intermediate files may be generated within individual directories under
`scripts/`; the collected deliverables are the files in `OUTPUT_FIGURES/`.
