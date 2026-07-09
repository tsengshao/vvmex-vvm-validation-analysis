#!/usr/bin/env python3
"""Compute horizontal-mean PBL diagnostics from VVM and VVMex outputs."""

from __future__ import annotations

import argparse
import multiprocessing as mp
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import xarray as xr


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CPU_ROOT = (SCRIPT_DIR / "../../cpu").resolve()
DEFAULT_GPU_ROOT = (SCRIPT_DIR / "../../gpu").resolve()
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data"
LANDS = ("grass", "evergreen", "urban")
MODELS = ("VVM", "VVMex")
PROFILE_VARS = ("thbar", "qvbar", "qcbar", "qibar", "qrbar")
SURFACE_VARS = ("tg", "ta", "sw", "lw", "lh", "sh", "gfx", "ws")
VVM_NC_KIND = Literal["Thermodynamic", "Dynamic", "Surface", "Radiation", "LandSurface"]


@dataclass(frozen=True)
class CasePaths:
    land: str
    vvm_case: Path
    vvmex_case: Path


@dataclass(frozen=True)
class ModelTask:
    land: str
    model: Literal["VVM", "VVMex"]
    step: int
    paths: dict[str, Path]
    rhobar0: float


@dataclass(frozen=True)
class StepMean:
    step: int
    time_seconds: float
    profiles: dict[str, np.ndarray]
    surface: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu-root", type=Path, default=DEFAULT_CPU_ROOT)
    parser.add_argument("--gpu-root", type=Path, default=DEFAULT_GPU_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--lands", nargs="+", choices=LANDS, default=list(LANDS))
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--skip-l2",
        action="store_true",
        help="Do not write {land}_l2.nc comparison files.",
    )
    return parser.parse_args()


def case_paths(land: str, cpu_root: Path, gpu_root: Path) -> CasePaths:
    return CasePaths(
        land=land,
        vvm_case=cpu_root / f"pbl_{land}_aaron_dz200",
        vvmex_case=gpu_root / f"{land}_good_luck",
    )


def index_steps(folder: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Directory not found: {folder}")
    files: dict[int, Path] = {}
    for path in folder.iterdir():
        match = pattern.fullmatch(path.name)
        if match:
            step = int(match.group(1))
            if step in files:
                raise ValueError(f"Duplicate step {step:06d} in {folder}")
            files[step] = path
    return files


def vvm_nc_files(case: Path, kind: VVM_NC_KIND) -> dict[int, Path]:
    prefix = case.name
    stem = f"{prefix}.L.{kind}" if kind in {"Thermodynamic", "Dynamic", "Radiation"} else f"{prefix}.C.{kind}"
    pattern = re.compile(rf"{re.escape(stem)}-(\d{{6}})\.nc")
    files = index_steps(case / "archive", pattern)
    if not files:
        raise FileNotFoundError(f"No {kind} files found below {case / 'archive'}")
    return files


def vvmex_files(case: Path) -> dict[int, Path]:
    pattern = re.compile(r"vvm_output_(\d{6})\.h5")
    files = index_steps(case, pattern)
    if not files:
        raise FileNotFoundError(f"No VVMex HDF5 files found below {case}")
    return files


def common_steps(paths: CasePaths, max_steps: int | None) -> list[int]:
    file_sets = [
        set(vvm_nc_files(paths.vvm_case, kind))
        for kind in ("Thermodynamic", "Dynamic", "Surface", "Radiation", "LandSurface")
    ]
    file_sets.append(set(vvmex_files(paths.vvmex_case)))
    steps = sorted(set.intersection(*file_sets))
    if not steps:
        raise RuntimeError(f"No common output steps for {paths.land}")
    if max_steps is not None:
        steps = steps[:max_steps]
    return steps


def build_task_paths(paths: CasePaths, step: int, model: str) -> dict[str, Path]:
    if model.lower() == "vvm":
        return {
            "thermo": paths.vvm_case / "archive" / f"{paths.vvm_case.name}.L.Thermodynamic-{step:06d}.nc",
            "dynamic": paths.vvm_case / "archive" / f"{paths.vvm_case.name}.L.Dynamic-{step:06d}.nc",
            "surface": paths.vvm_case / "archive" / f"{paths.vvm_case.name}.C.Surface-{step:06d}.nc",
            "radiation": paths.vvm_case / "archive" / f"{paths.vvm_case.name}.L.Radiation-{step:06d}.nc",
            "landsurface": paths.vvm_case / "archive" / f"{paths.vvm_case.name}.C.LandSurface-{step:06d}.nc",
        }
    if model.lower() == "vvmex":
        return {"h5": paths.vvmex_case / f"vvm_output_{step:06d}.h5"}
    raise ValueError(f"Unknown model: {model}")


def read_static_grid(paths: CasePaths, first_step: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    thermo = paths.vvm_case / "archive" / f"{paths.vvm_case.name}.L.Thermodynamic-{first_step:06d}.nc"
    h5_path = paths.vvmex_case / f"vvm_output_{first_step:06d}.h5"
    with xr.open_dataset(thermo, decode_times=False) as ds:
        z_vvm = np.asarray(ds["zc"], dtype=np.float64)
    with h5py.File(h5_path, "r") as handle:
        z_vvmex = np.asarray(handle["Step0/coordinates/z_mid"][:], dtype=np.float64)
        rhobar = np.asarray(handle["Step0/rhobar"][:], dtype=np.float64)

    if z_vvm.ndim != 1 or z_vvm.size != z_vvmex.size + 1:
        raise ValueError(f"Unexpected z size for {paths.land}: VVM={z_vvm.shape}, VVMex={z_vvmex.shape}")
    if not np.array_equal(z_vvm[1:], z_vvmex):
        raise ValueError(f"VVM z=2..nz does not match VVMex z=1..nz for {paths.land}")
    if rhobar.shape != z_vvmex.shape:
        raise ValueError(f"rhobar shape {rhobar.shape} does not match z {z_vvmex.shape}")
    if not np.all(np.isfinite(rhobar)) or np.any(rhobar <= 0.0):
        raise ValueError(f"Invalid rhobar values for {paths.land}")
    dz = np.full_like(z_vvmex, 200.0, dtype=np.float64)
    return z_vvmex, dz, rhobar


def require_shape(name: str, array: np.ndarray, expected: tuple[int, ...]) -> None:
    if array.shape != expected:
        raise ValueError(f"{name} shape {array.shape}; expected {expected}")


def mean_xy(field: np.ndarray) -> float:
    return float(np.mean(field, dtype=np.float64))


def profile_mean(field: np.ndarray, name: str, nz: int) -> np.ndarray:
    require_shape(name, field, (nz, 128, 128))
    return np.mean(field, axis=(1, 2), dtype=np.float64)


def read_vvm_task(task: ModelTask) -> StepMean:
    nz = 149
    profiles: dict[str, np.ndarray] = {}
    surface: dict[str, float] = {}

    with xr.open_dataset(task.paths["thermo"], decode_times=False) as ds:
        time_seconds = float(np.asarray(ds["time"]).squeeze()) * 60.0
        for out_name, source_name in {
            "thbar": "th",
            "qvbar": "qv",
            "qcbar": "qc",
            "qibar": "qi",
            "qrbar": "qr",
        }.items():
            field = np.asarray(ds[source_name][0, 1:, :, :], dtype=np.float64)
            profiles[out_name] = profile_mean(field, source_name, nz)
        th_sfc = np.asarray(ds["th"][0, 1, :, :], dtype=np.float64)
        surface["ta"] = mean_xy(th_sfc) * task.rhobar0

    with xr.open_dataset(task.paths["surface"], decode_times=False) as ds:
        surface["tg"] = mean_xy(np.asarray(ds["tg"][0, :, :], dtype=np.float64))
        surface["lh"] = mean_xy(np.asarray(ds["wqv"][0, :, :], dtype=np.float64)) * 2.5e6
        surface["sh"] = mean_xy(np.asarray(ds["wth"][0, :, :], dtype=np.float64)) * 1004.0

    with xr.open_dataset(task.paths["radiation"], decode_times=False) as ds:
        surface["sw"] = mean_xy(np.asarray(ds["fdsw"][0, 1, :, :], dtype=np.float64))
        surface["lw"] = mean_xy(np.asarray(ds["fdlw"][0, 1, :, :], dtype=np.float64))

    with xr.open_dataset(task.paths["landsurface"], decode_times=False) as ds:
        surface["gfx"] = mean_xy(np.asarray(ds["ssoil"][0, :, :], dtype=np.float64))

    with xr.open_dataset(task.paths["dynamic"], decode_times=False) as ds:
        u = np.asarray(ds["u"][0, 1, :, :], dtype=np.float64)
        v = np.asarray(ds["v"][0, 1, :, :], dtype=np.float64)
        surface["ws"] = mean_xy(np.hypot(u, v))

    return StepMean(task.step, time_seconds, profiles, surface)


def read_vvmex_task(task: ModelTask) -> StepMean:
    nz = 149
    profiles: dict[str, np.ndarray] = {}
    surface: dict[str, float] = {}
    with h5py.File(task.paths["h5"], "r") as handle:
        group = handle["Step0"]
        time_seconds = float(group["time"][()])
        for out_name, source_name in {
            "thbar": "th",
            "qvbar": "qv",
            "qcbar": "qc",
            "qibar": "qi",
            "qrbar": "qr",
        }.items():
            field = np.asarray(group[source_name][:], dtype=np.float64)
            profiles[out_name] = profile_mean(field, source_name, nz)
        surface["tg"] = mean_xy(np.asarray(group["Tg"][:], dtype=np.float64))
        surface["ta"] = mean_xy(np.asarray(group["th"][0, :, :], dtype=np.float64)) * task.rhobar0
        surface["sw"] = mean_xy(np.asarray(group["swdn_sfc"][:], dtype=np.float64))
        surface["lw"] = mean_xy(np.asarray(group["lwdn_sfc"][:], dtype=np.float64))
        surface["lh"] = mean_xy(np.asarray(group["le"][:], dtype=np.float64)) * 2.5e6
        surface["sh"] = mean_xy(np.asarray(group["hfx"][:], dtype=np.float64)) * 1004.0
        surface["gfx"] = mean_xy(np.asarray(group["gfx"][:], dtype=np.float64))
        u = np.asarray(group["u"][0, :, :], dtype=np.float64)
        v = np.asarray(group["v"][0, :, :], dtype=np.float64)
        surface["ws"] = mean_xy(np.hypot(u, v))
    return StepMean(task.step, time_seconds, profiles, surface)


def process_task(task: ModelTask) -> StepMean:
    if task.model.lower() == "vvm":
        return read_vvm_task(task)
    if task.model.lower() == "vvmex":
        return read_vvmex_task(task)
    raise ValueError(f"Unknown model: {task.model}")


def collect_means(tasks: list[ModelTask], workers: int) -> list[StepMean]:
    if workers == 1:
        results = []
        for index, task in enumerate(tasks, start=1):
            results.append(process_task(task))
            if index == 1 or index % 50 == 0 or index == len(tasks):
                print(f"  processed {index}/{len(tasks)} {task.model} steps", flush=True)
        return results

    context = mp.get_context("spawn")
    results = []
    with context.Pool(processes=workers) as pool:
        for index, result in enumerate(pool.imap_unordered(process_task, tasks, chunksize=1), start=1):
            results.append(result)
            if index == 1 or index % 50 == 0 or index == len(tasks):
                print(f"  processed {index}/{len(tasks)} steps", flush=True)
    return results


def build_model_dataset(
    land: str,
    model: str,
    results: list[StepMean],
    steps: list[int],
    z: np.ndarray,
    dz: np.ndarray,
    rhobar: np.ndarray,
    source_case: Path,
) -> xr.Dataset:
    by_step = {result.step: result for result in results}
    missing = sorted(set(steps) - set(by_step))
    if missing:
        raise RuntimeError(f"Missing processed {model} steps for {land}: {missing[:5]}")

    time = np.asarray([by_step[step].time_seconds for step in steps], dtype=np.float64)
    data_vars: dict[str, tuple[tuple[str, ...], np.ndarray]] = {
        "rhobar": (("lev",), np.asarray(rhobar, dtype=np.float64)),
        "dz": (("lev",), np.asarray(dz, dtype=np.float64)),
    }
    for name in PROFILE_VARS:
        values = np.asarray([by_step[step].profiles[name] for step in steps], dtype=np.float64)
        data_vars[name] = (
            ("time", "lev", "lat", "lon"),
            values[:, :, None, None],
        )
    for name in SURFACE_VARS:
        values = np.asarray([by_step[step].surface[name] for step in steps], dtype=np.float64)
        data_vars[name] = (
            ("time", "lat", "lon"),
            values[:, None, None],
        )

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": time,
            "step": (("time",), np.asarray(steps, dtype=np.int32)),
            "lev": np.asarray(z, dtype=np.float64),
            "lat": np.asarray([0.0], dtype=np.float64),
            "lon": np.asarray([0.0], dtype=np.float64),
        },
        attrs={
            "Conventions": "CF-1.4",
            "title": f"{land} {model.upper()} horizontal-mean PBL diagnostics",
            "land_type": land,
            "model": model,
            "source_case": str(source_case.resolve()),
            "horizontal_mean": "Mean over all 128 x 128 x-y grid cells.",
            "vertical_alignment": "VVM z=2..150 corresponds to VVMex z=1..149. Output coordinate lev is the common height.",
            "dz_definition": "Constant 200 m, matching GrADS lev(z=2)-lev(z=1) on the common VVMex grid.",
            "ta_definition": "Horizontal-mean first common theta level multiplied by VVMex rhobar(z=1).",
        },
    )
    add_attrs(ds)
    return ds


def add_attrs(ds: xr.Dataset) -> None:
    ds["time"].attrs.update(
        standard_name="time",
        long_name="simulation time",
        units="seconds since 1998-01-01 05:00:00",
        calendar="standard",
        axis="T",
    )
    ds["step"].attrs.update(long_name="model output step")
    ds["lev"].attrs.update(
        standard_name="altitude",
        long_name="height of common VVM/VVMex model layer centers",
        units="m",
        axis="Z",
        positive="up",
    )
    ds["lat"].attrs.update(
        standard_name="latitude",
        long_name="latitude",
        units="degrees_north",
        axis="Y",
    )
    ds["lon"].attrs.update(
        standard_name="longitude",
        long_name="longitude",
        units="degrees_east",
        axis="X",
    )
    ds["rhobar"].attrs.update(long_name="VVMex base-state air density", units="kg m-3")
    ds["dz"].attrs.update(long_name="vertical layer thickness used for diagnostics", units="m")
    for name in ("thbar",):
        ds[name].attrs.update(long_name="horizontal-mean potential temperature", units="K")
    for name, long_name in {
        "qvbar": "horizontal-mean water vapor mixing ratio",
        "qcbar": "horizontal-mean cloud water mixing ratio",
        "qibar": "horizontal-mean cloud ice mixing ratio",
        "qrbar": "horizontal-mean rain water mixing ratio",
    }.items():
        ds[name].attrs.update(long_name=long_name, units="kg kg-1")
    ds["tg"].attrs.update(long_name="horizontal-mean ground or skin temperature", units="K")
    ds["ta"].attrs.update(long_name="horizontal-mean density-weighted first-level theta", units="kg K m-3")
    ds["sw"].attrs.update(long_name="horizontal-mean downward shortwave radiation at surface", units="W m-2")
    ds["lw"].attrs.update(long_name="horizontal-mean downward longwave radiation at surface", units="W m-2")
    ds["lh"].attrs.update(long_name="horizontal-mean latent heat flux diagnostic", units="W m-2", applied_factor=2.5e6)
    ds["sh"].attrs.update(long_name="horizontal-mean sensible heat flux diagnostic", units="W m-2", applied_factor=1004.0)
    ds["gfx"].attrs.update(long_name="horizontal-mean ground heat flux", units="W m-2")
    ds["ws"].attrs.update(long_name="horizontal-mean first-level wind speed", units="m s-1")


def write_dataset(ds: xr.Dataset, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoding = {
        name: {"zlib": True, "complevel": 4, "shuffle": True}
        for name in ds.data_vars
        if ds[name].ndim > 0
    }
    ds.to_netcdf(output, engine="netcdf4", encoding=encoding)
    print(f"  wrote {output}", flush=True)


def build_l2_dataset(land: str, vvm: xr.Dataset, vvmex: xr.Dataset) -> xr.Dataset:
    if not np.array_equal(vvm["step"].values, vvmex["step"].values):
        raise ValueError(f"Cannot compute L2 for {land}: VVM and VVMex steps differ")
    if not np.array_equal(vvm["lev"].values, vvmex["lev"].values):
        raise ValueError(f"Cannot compute L2 for {land}: VVM and VVMex lev coordinates differ")

    wei = vvm["rhobar"].values * vvm["dz"].values
    data_vars = {
        "rhobar": (("lev",), vvm["rhobar"].values),
        "dz": (("lev",), vvm["dz"].values),
        "weight": (("lev",), wei),
    }
    for name in PROFILE_VARS:
        vvm_values = np.asarray(vvm[name].values[:, :, 0, 0], dtype=np.float64)
        vvmex_values = np.asarray(vvmex[name].values[:, :, 0, 0], dtype=np.float64)
        diff = (vvmex_values - vvm_values) * wei[None, :]
        denom_field = vvm_values * wei[None, :]
        numerator = np.sqrt(np.mean(diff * diff, axis=1, dtype=np.float64))
        denominator = np.sqrt(np.mean(denom_field * denom_field, axis=1, dtype=np.float64))
        data_vars[f"{name}_l2"] = (
            ("time", "lat", "lon"),
            np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 1.0e-12)[:, None, None],
        )

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": vvm["time"].values,
            "step": (("time",), vvm["step"].values),
            "lev": vvm["lev"].values,
            "lat": vvm["lat"].values,
            "lon": vvm["lon"].values,
        },
        attrs={
            "Conventions": "CF-1.4",
            "title": f"{land} VVMex relative L2 norm against VVM",
            "land_type": land,
            "formula": "sqrt(mean(((vvmex - vvm) * rhobar * dz)^2, z)) / sqrt(mean((vvm * rhobar * dz)^2, z))",
            "dz_definition": "Constant 200 m.",
        },
    )
    ds["time"].attrs.update(vvm["time"].attrs)
    ds["step"].attrs.update(vvm["step"].attrs)
    ds["lev"].attrs.update(vvm["lev"].attrs)
    ds["lat"].attrs.update(vvm["lat"].attrs)
    ds["lon"].attrs.update(vvm["lon"].attrs)
    ds["rhobar"].attrs.update(vvm["rhobar"].attrs)
    ds["dz"].attrs.update(vvm["dz"].attrs)
    ds["weight"].attrs.update(long_name="rhobar multiplied by dz", units="kg m-2")
    for name in PROFILE_VARS:
        ds[f"{name}_l2"].attrs.update(
            long_name=f"relative L2 norm for {name}, VVMex against VVM",
            units="1",
        )
    return ds


def process_land(paths: CasePaths, output_dir: Path, workers: int, max_steps: int | None, skip_l2: bool) -> None:
    steps = common_steps(paths, max_steps)
    z, dz, rhobar = read_static_grid(paths, steps[0])
    print(f"{paths.land}: {len(steps)} common steps ({steps[0]:06d}-{steps[-1]:06d})", flush=True)

    datasets: dict[str, xr.Dataset] = {}
    for model in MODELS:
        tasks = [
            ModelTask(paths.land, model, step, build_task_paths(paths, step, model), float(rhobar[0]))
            for step in steps
        ]
        results = sorted(collect_means(tasks, workers), key=lambda item: item.step)
        source_case = paths.vvm_case if model.lower() == "vvm" else paths.vvmex_case
        ds = build_model_dataset(paths.land, model, results, steps, z, dz, rhobar, source_case)
        write_dataset(ds, output_dir / f"{paths.land}_{model}.nc")
        datasets[model] = ds

    if not skip_l2:
        l2 = build_l2_dataset(paths.land, datasets["vvm"], datasets["vvmex"])
        write_dataset(l2, output_dir / f"{paths.land}_l2.nc")
        l2.close()

    for ds in datasets.values():
        ds.close()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.max_steps is not None and args.max_steps < 1:
        raise ValueError("--max-steps must be at least 1")

    cpu_root = args.cpu_root.expanduser().resolve()
    gpu_root = args.gpu_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    for land in args.lands:
        paths = case_paths(land, cpu_root, gpu_root)
        process_land(paths, output_dir, args.workers, args.max_steps, args.skip_l2)


if __name__ == "__main__":
    main()
