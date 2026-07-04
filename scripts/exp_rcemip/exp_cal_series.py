#!/usr/bin/env python3
"""Compute VVM and VVMex domain-mean water-path time series.

For every common output step, this script vertically integrates qv, qc, qi,
and qr with the VVMex base-state density. It then saves domain statistics for
CWV, LWP, IWP, CWV standard deviation, and dry-column fraction to NetCDF.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Importing VVMTools imports Matplotlib. Its normal cache is read-only here.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vvm-matplotlib-cache")

import h5py
import numpy as np
import xarray as xr
from vvmtools.analyze import DataRetriever


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_VVM_CASE = (SCRIPT_DIR / "../../cpu/case_rce_f1_aaron_rad").resolve()
DEFAULT_VVMEX_CASE = (SCRIPT_DIR / "../../gpu/rcemip_0623").resolve()
DEFAULT_OUTPUT = SCRIPT_DIR / "water_path_timeseries.nc"

VVM_PATTERN = re.compile(r"\.L\.Thermodynamic-(\d{6})\.nc$")
VVMEX_PATTERN = re.compile(r"vvm_output_(\d{6})\.h5$")
MODEL_NAMES = ("VVM", "VVMex")
WATER_VARIABLES = ("qv", "qc", "qi", "qr")


@dataclass(frozen=True)
class Task:
    model: Literal["VVM", "VVMex"]
    step: int
    path: Path


@dataclass(frozen=True)
class Result:
    model: Literal["VVM", "VVMex"]
    step: int
    time_seconds: float
    cwv_mean: float
    cwv_std: float
    lwp_mean: float
    iwp_mean: float
    dryfrac: float


_WEIGHTS: np.ndarray | None = None
_DRY_THRESHOLD: float | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vvm-case", type=Path, default=DEFAULT_VVM_CASE)
    parser.add_argument("--vvmex-case", type=Path, default=DEFAULT_VVMEX_CASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of worker processes (default: 10).",
    )
    parser.add_argument(
        "--dry-threshold",
        type=float,
        default=30.0,
        help="CWV threshold in mm for DRYFRAC (default: 30).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Process only the first N common steps; useful for testing.",
    )
    return parser.parse_args()


def index_files(folder: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Input directory not found: {folder}")

    files: dict[int, Path] = {}
    for path in folder.iterdir():
        match = pattern.search(path.name)
        if match:
            step = int(match.group(1))
            if step in files:
                raise ValueError(f"Duplicate step {step:06d} below {folder}")
            files[step] = path
    return files


def discover_vvm_files(case_path: Path) -> dict[int, Path]:
    archive = case_path / "archive"
    files = index_files(archive, VVM_PATTERN)
    if not files:
        raise FileNotFoundError(f"No VVM Thermodynamic NetCDF files in {archive}")
    return files


def discover_vvmex_files(case_path: Path) -> dict[int, Path]:
    files = index_files(case_path, VVMEX_PATTERN)
    if not files:
        raise FileNotFoundError(f"No VVMex HDF5 files in {case_path}")
    return files


def read_and_validate_vertical_grid(
    vvm_case: Path,
    first_vvm_file: Path,
    first_vvmex_file: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (zz, dz, rhobar), all in the common 74-level convention."""
    retriever = DataRetriever(case_path=str(vvm_case))
    zz = np.asarray(retriever.DIM["zz"], dtype=np.float64)
    if zz.ndim != 1 or zz.size < 2 or not np.all(np.diff(zz) > 0.0):
        raise ValueError("VVMTools DIM['zz'] must be a strictly increasing profile")

    with xr.open_dataset(first_vvm_file, decode_times=False) as dataset:
        if "zc" not in dataset:
            raise KeyError(f"Missing zc in {first_vvm_file}")
        netcdf_zc = np.asarray(dataset["zc"], dtype=np.float64)

    with h5py.File(first_vvmex_file, "r") as handle:
        z_mid = np.asarray(handle["Step0/coordinates/z_mid"][:], dtype=np.float64)
        rhobar = np.asarray(handle["Step0/rhobar"][:], dtype=np.float64)

    if not np.array_equal(zz, netcdf_zc):
        raise ValueError("VVMTools DIM['zz'] does not exactly match VVM NetCDF zc")
    if not np.array_equal(zz[1:], z_mid):
        raise ValueError("VVM zz[1:] does not exactly match VVMex z_mid")

    dz = np.diff(zz)
    if dz.shape != z_mid.shape or rhobar.shape != z_mid.shape:
        raise ValueError(
            f"Vertical shape mismatch: dz={dz.shape}, z_mid={z_mid.shape}, "
            f"rhobar={rhobar.shape}"
        )
    if not np.all(np.isfinite(rhobar)) or np.any(rhobar <= 0.0):
        raise ValueError("VVMex rhobar must contain only finite positive values")

    return zz, dz, rhobar


def validate_static_vvmex_profiles(
    files: dict[int, Path], z_mid_reference: np.ndarray, rho_reference: np.ndarray
) -> None:
    """Check that vertical coordinates and density are constant through time."""
    for step in (min(files), max(files)):
        with h5py.File(files[step], "r") as handle:
            z_mid = np.asarray(handle["Step0/coordinates/z_mid"][:])
            rhobar = np.asarray(handle["Step0/rhobar"][:])
        if not np.array_equal(z_mid, z_mid_reference):
            raise ValueError(f"VVMex z_mid changed at step {step:06d}")
        if not np.array_equal(rhobar, rho_reference):
            raise ValueError(f"VVMex rhobar changed at step {step:06d}")


def initialize_worker(weights: np.ndarray, dry_threshold: float) -> None:
    global _WEIGHTS, _DRY_THRESHOLD
    _WEIGHTS = np.asarray(weights, dtype=np.float64)
    _DRY_THRESHOLD = float(dry_threshold)


def integrate_field(field: np.ndarray, expected_shape: tuple[int, ...]) -> np.ndarray:
    if _WEIGHTS is None:
        raise RuntimeError("Worker weights have not been initialized")
    field = np.asarray(field)
    if field.shape != expected_shape:
        raise ValueError(f"Field shape {field.shape}; expected {expected_shape}")
    if not np.all(np.isfinite(field)):
        raise ValueError("Water mixing-ratio field contains non-finite values")
    return np.tensordot(_WEIGHTS, field, axes=(0, 0))


def read_vvm_columns(path: Path) -> tuple[float, dict[str, np.ndarray]]:
    if _WEIGHTS is None:
        raise RuntimeError("Worker weights have not been initialized")
    nz = _WEIGHTS.size
    expected_shape: tuple[int, ...] | None = None
    columns: dict[str, np.ndarray] = {}

    with xr.open_dataset(path, decode_times=False) as dataset:
        time_seconds = float(np.asarray(dataset["time"]).squeeze()) * 60.0
        for name in WATER_VARIABLES:
            if name not in dataset:
                raise KeyError(f"Missing {name} in {path}")
            field = np.asarray(dataset[name][0, 1:, :, :])
            if expected_shape is None:
                expected_shape = (nz, *field.shape[1:])
            columns[name] = integrate_field(field, expected_shape)

    return time_seconds, columns


def read_vvmex_columns(path: Path) -> tuple[float, dict[str, np.ndarray]]:
    if _WEIGHTS is None:
        raise RuntimeError("Worker weights have not been initialized")
    nz = _WEIGHTS.size
    expected_shape: tuple[int, ...] | None = None
    columns: dict[str, np.ndarray] = {}

    with h5py.File(path, "r") as handle:
        time_seconds = float(handle["Step0/time"][()])
        for name in WATER_VARIABLES:
            key = f"Step0/{name}"
            if key not in handle:
                raise KeyError(f"Missing {key} in {path}")
            field = np.asarray(handle[key][:])
            if expected_shape is None:
                expected_shape = (nz, *field.shape[1:])
            columns[name] = integrate_field(field, expected_shape)

    return time_seconds, columns


def process_task(task: Task) -> Result:
    if _DRY_THRESHOLD is None:
        raise RuntimeError("Worker dry threshold has not been initialized")

    if task.model == "VVM":
        time_seconds, columns = read_vvm_columns(task.path)
    else:
        time_seconds, columns = read_vvmex_columns(task.path)

    cwv = columns["qv"]
    lwp = columns["qc"] + columns["qr"]
    iwp = columns["qi"]
    return Result(
        model=task.model,
        step=task.step,
        time_seconds=time_seconds,
        cwv_mean=float(np.mean(cwv, dtype=np.float64)),
        cwv_std=float(np.std(cwv, ddof=0, dtype=np.float64)),
        lwp_mean=float(np.mean(lwp, dtype=np.float64)),
        iwp_mean=float(np.mean(iwp, dtype=np.float64)),
        dryfrac=float(np.mean(cwv <= _DRY_THRESHOLD, dtype=np.float64)),
    )


def collect_results(
    tasks: list[Task], weights: np.ndarray, dry_threshold: float, workers: int
) -> list[Result]:
    if workers == 1:
        initialize_worker(weights, dry_threshold)
        results = []
        for index, task in enumerate(tasks, start=1):
            results.append(process_task(task))
            if index == 1 or index % 20 == 0 or index == len(tasks):
                print(f"Processed {index}/{len(tasks)} model-step tasks", flush=True)
        return results

    context = mp.get_context("spawn")
    results = []
    with context.Pool(
        processes=workers,
        initializer=initialize_worker,
        initargs=(weights, dry_threshold),
    ) as pool:
        for index, result in enumerate(
            pool.imap_unordered(process_task, tasks, chunksize=1), start=1
        ):
            results.append(result)
            if index == 1 or index % 20 == 0 or index == len(tasks):
                print(f"Processed {index}/{len(tasks)} model-step tasks", flush=True)
    return results


def build_dataset(
    results: list[Result],
    steps: list[int],
    dz: np.ndarray,
    rhobar: np.ndarray,
    dry_threshold: float,
    vvm_case: Path,
    vvmex_case: Path,
) -> xr.Dataset:
    by_key = {(result.model, result.step): result for result in results}
    shape = (len(MODEL_NAMES), len(steps))

    def values(attribute: str) -> np.ndarray:
        return np.asarray(
            [
                [getattr(by_key[(model, step)], attribute) for step in steps]
                for model in MODEL_NAMES
            ],
            dtype=np.float64,
        )

    time_by_model = values("time_seconds")
    if not np.allclose(time_by_model[0], time_by_model[1], rtol=0.0, atol=1.0e-9):
        raise ValueError("VVM and VVMex time coordinates do not match")

    dataset = xr.Dataset(
        data_vars={
            "cwv_mean": (("model", "time"), values("cwv_mean")),
            "cwv_std": (("model", "time"), values("cwv_std")),
            "lwp_mean": (("model", "time"), values("lwp_mean")),
            "iwp_mean": (("model", "time"), values("iwp_mean")),
            "dryfrac": (("model", "time"), values("dryfrac")),
            "dz": (("level",), np.asarray(dz, dtype=np.float64)),
            "rhobar": (("level",), np.asarray(rhobar, dtype=np.float64)),
        },
        coords={
            "model": np.asarray(MODEL_NAMES, dtype=str),
            "time": time_by_model[0],
            "step": (("time",), np.asarray(steps, dtype=np.int32)),
            "level": np.arange(dz.size, dtype=np.int32),
        },
        attrs={
            "title": "VVM and VVMex domain-mean water-path time series",
            "integration_formula": "water_path(x,y) = sum_z(rhobar * q * dz)",
            "vertical_grid": "dz = diff(VVMTools DIM['zz']); VVM level 0 omitted",
            "density_source": "VVMex Step0/rhobar",
            "lwp_definition": "vertical integral of qc + qr",
            "iwp_definition": "vertical integral of qi; qrim is excluded",
            "cwv_std_definition": "population standard deviation over all x-y columns (ddof=0)",
            "dryfrac_definition": f"horizontal fraction of CWV <= {dry_threshold:g} mm",
            "vvm_case": str(vvm_case.resolve()),
            "vvmex_case": str(vvmex_case.resolve()),
        },
    )

    for name in ("cwv_mean", "cwv_std", "lwp_mean", "iwp_mean"):
        dataset[name].attrs["units"] = "kg m-2"
    dataset["cwv_mean"].attrs["long_name"] = "domain-mean column water vapor"
    dataset["cwv_std"].attrs["long_name"] = "spatial standard deviation of column water vapor"
    dataset["lwp_mean"].attrs["long_name"] = "domain-mean liquid water path (cloud plus rain)"
    dataset["iwp_mean"].attrs["long_name"] = "domain-mean ice water path"
    dataset["dryfrac"].attrs.update(
        long_name="fraction of dry columns", units="1", threshold_mm=dry_threshold
    )
    dataset["time"].attrs.update(long_name="simulation time", units="seconds")
    dataset["step"].attrs["long_name"] = "output step"
    dataset["dz"].attrs.update(long_name="vertical layer thickness", units="m")
    dataset["rhobar"].attrs.update(long_name="VVMex base-state air density", units="kg m-3")
    if dataset["cwv_mean"].shape != shape:
        raise RuntimeError("Unexpected output array shape")
    return dataset


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.dry_threshold < 0.0:
        raise ValueError("--dry-threshold must be non-negative")
    if args.max_steps is not None and args.max_steps < 1:
        raise ValueError("--max-steps must be at least 1")

    vvm_case = args.vvm_case.expanduser().resolve()
    vvmex_case = args.vvmex_case.expanduser().resolve()
    output = args.output.expanduser().resolve()
    vvm_files = discover_vvm_files(vvm_case)
    vvmex_files = discover_vvmex_files(vvmex_case)
    steps = sorted(set(vvm_files) & set(vvmex_files))
    if not steps:
        raise RuntimeError("VVM and VVMex have no common output steps")
    if args.max_steps is not None:
        steps = steps[: args.max_steps]

    zz, dz, rhobar = read_and_validate_vertical_grid(
        vvm_case, vvm_files[steps[0]], vvmex_files[steps[0]]
    )
    validate_static_vvmex_profiles(vvmex_files, zz[1:], rhobar)
    weights = rhobar * dz

    print(f"VVM case:   {vvm_case}")
    print(f"VVMex case: {vvmex_case}")
    print(f"Common steps selected: {len(steps)} ({steps[0]:06d}--{steps[-1]:06d})")
    print(f"Workers: {args.workers}")
    print(f"Dry threshold: {args.dry_threshold:g} mm")

    tasks = [Task("VVM", step, vvm_files[step]) for step in steps]
    tasks.extend(Task("VVMex", step, vvmex_files[step]) for step in steps)
    results = collect_results(tasks, weights, args.dry_threshold, args.workers)
    dataset = build_dataset(
        results,
        steps,
        dz,
        rhobar,
        args.dry_threshold,
        vvm_case,
        vvmex_case,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    encoding = {
        name: {"zlib": True, "complevel": 4, "shuffle": True}
        for name in dataset.data_vars
    }
    dataset.to_netcdf(output, engine="netcdf4", encoding=encoding)
    dataset.close()
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
