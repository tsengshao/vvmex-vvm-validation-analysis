#!/usr/bin/env python3
"""Write CF-style TaiwanVVM daily-mean rain and terrain-height NetCDF files."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import xarray as xr


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = (SCRIPT_DIR / "../..").resolve()

Model = Literal["VVM", "VVMex"]


@dataclass(frozen=True)
class CaseConfig:
    key: str
    exp_name: str
    resolution: str
    vvm_case: Path
    vvmex_case: Path
    nx: int
    ny: int
    lon0: float = 118.6387024
    lat0: float = 21.2194805
    dlon: float = 0.0046997
    dlat: float = 0.0046997
    roll_x_fraction: float = 0.0
    roll_y_fraction: float = 0.0


CASES = {
    "original": CaseConfig(
        key="original",
        exp_name="taiwanvvm",
        resolution="1024x1024",
        vvm_case=ROOT_DIR / "cpu/case_taiwanvvm_f1_aaron",
        vvmex_case=ROOT_DIR / "gpu/taiwanvvm_20120819_good_luck",
        nx=1024,
        ny=1024,
    ),
    "large": CaseConfig(
        key="large",
        exp_name="taiwanvvmlarge",
        resolution="2048x2048",
        vvm_case=ROOT_DIR / "cpu/case_taiwanvvm_f1_Large_aaron",
        vvmex_case=ROOT_DIR / "gpu/taiwanvvm_20120819_2048_64gpus_newtopo_test",
        nx=2048,
        ny=2048,
        roll_x_fraction=0.25,
        roll_y_fraction=0.25,
    ),
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["original", "large", "all"], default="all")
    parser.add_argument("--model", choices=["VVM", "VVMex", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "data" / "daily_rain_cf")
    parser.add_argument(
        "--skip-days",
        type=int,
        default=0,
        help="Number of complete days to skip after the initial output. The initial output step is always skipped.",
    )
    parser.add_argument("--days", type=int, default=1, help="Number of days to average after skipped days.")
    parser.add_argument("--steps-per-day", type=int, default=144, help="10-minute output gives 144 samples per day.")
    parser.add_argument("--no-half-grid-shift", action="store_true", help="Do not shift lon/lat by half a grid cell.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing NetCDF output files.")
    return parser.parse_args()


def selected_cases(name: str) -> list[CaseConfig]:
    if name == "all":
        return [CASES["original"], CASES["large"]]
    return [CASES[name]]


def selected_models(name: str) -> list[Model]:
    if name == "all":
        return ["VVMex", "VVM"]
    return [name]


def index_files(folder: Path, pattern: str) -> dict[int, Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Directory not found: {folder}")
    regex = re.compile(pattern)
    files: dict[int, Path] = {}
    for path in folder.iterdir():
        match = regex.fullmatch(path.name)
        if match:
            files[int(match.group(1))] = path
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} in {folder}")
    return files


def averaging_steps(files: dict[int, Path], skip_days: int, days: int, steps_per_day: int) -> list[int]:
    if skip_days < 0 or days < 1 or steps_per_day < 1:
        raise ValueError("--skip-days must be >= 0, --days and --steps-per-day must be >= 1")
    start = 1 + skip_days * steps_per_day
    stop = start + days * steps_per_day
    steps = list(range(start, stop))
    missing = [step for step in steps if step not in files]
    if missing:
        available = sorted(files)
        raise RuntimeError(
            f"Need steps {start:06d}-{stop - 1:06d} after skipping the initial output "
            f"for skip_days={skip_days}, days={days}, "
            f"but {len(missing)} steps are missing. Available range is "
            f"{available[0]:06d}-{available[-1]:06d} ({len(available)} files)."
        )
    return steps


def lon_lat(case: CaseConfig, half_grid_shift: bool) -> tuple[np.ndarray, np.ndarray]:
    shift = 0.5 if half_grid_shift else 0.0
    lon = case.lon0 + (np.arange(case.nx, dtype=np.float64) + shift) * case.dlon
    lat = case.lat0 + (np.arange(case.ny, dtype=np.float64) + shift) * case.dlat
    roll_x, roll_y = roll_offsets(case)
    lon = rolled_extended_axis(lon, roll_x, case.dlon)
    lat = rolled_extended_axis(lat, roll_y, case.dlat)
    return lon, lat


def read_vvm(case: CaseConfig, skip_days: int, days: int, steps_per_day: int) -> tuple[np.ndarray, np.ndarray, list[int]]:
    files = index_files(
        case.vvm_case / "archive",
        rf"{re.escape(case.vvm_case.name)}\.C\.Surface-(\d{{6}})\.nc",
    )
    steps = averaging_steps(files, skip_days, days, steps_per_day)
    rain_sum: np.ndarray | None = None
    for count, step in enumerate(steps, start=1):
        with xr.open_dataset(files[step], decode_times=False) as ds:
            rain = np.asarray(ds["sprec"].isel(time=0), dtype=np.float64)
        rain_sum = rain if rain_sum is None else rain_sum + rain
        if count == 1 or count % 48 == 0 or count == len(steps):
            print(f"  VVM {case.exp_name}: read rain {count}/{len(steps)}", flush=True)
    assert rain_sum is not None
    rain_mean = rain_sum / float(len(steps)) * 86400.0

    topo_path = case.vvm_case / "TOPO.nc"
    with xr.open_dataset(topo_path, decode_times=False) as ds:
        height = np.asarray(ds["height"], dtype=np.float64) * 1000.0
    return rain_mean, height, steps


def read_vvmex(case: CaseConfig, skip_days: int, days: int, steps_per_day: int) -> tuple[np.ndarray, np.ndarray, list[int]]:
    files = index_files(case.vvmex_case, r"vvm_output_(\d{6})\.h5")
    steps = averaging_steps(files, skip_days, days, steps_per_day)
    rain_sum: np.ndarray | None = None
    height: np.ndarray | None = None
    for count, step in enumerate(steps, start=1):
        with h5py.File(files[step], "r") as handle:
            group = handle["Step0"]
            rain = read_h5_2d(group, ("precip_liq", "precip_liq_surf_mass")) + read_h5_2d(
                group, ("precip_ice", "precip_ice_surf_mass")
            )
            if height is None:
                height = np.asarray(group["topo"][:], dtype=np.float64) * 100.0
        rain_sum = rain if rain_sum is None else rain_sum + rain
        if count == 1 or count % 48 == 0 or count == len(steps):
            print(f"  VVMex {case.exp_name}: read rain {count}/{len(steps)}", flush=True)
    assert rain_sum is not None and height is not None
    rain_mean = rain_sum / float(len(steps)) * 86400.0
    return rain_mean, height, steps


def read_h5_2d(group: h5py.Group, names: tuple[str, ...]) -> np.ndarray:
    for name in names:
        if name in group:
            return np.asarray(group[name][:], dtype=np.float64)
    raise KeyError(f"None of these datasets exist in {group.name}: {', '.join(names)}")


def shift_suffix(half_grid_shift: bool) -> str:
    return "halfshift" if half_grid_shift else "noshift"


def roll_suffix(case: CaseConfig) -> str:
    roll_x, roll_y = roll_offsets(case)
    return f"rollx{roll_x}_rolly{roll_y}"


def output_path(output_dir: Path, case: CaseConfig, models: list[Model], skip_days: int, days: int, half_grid_shift: bool) -> Path:
    model_tag = "_".join(models)
    return output_dir / (
        f"{case.exp_name}_{case.resolution}_{model_tag}_daily_rain_"
        f"skip{skip_days}_days{days}_{shift_suffix(half_grid_shift)}_{roll_suffix(case)}_cf.nc"
    )


def roll_offsets(case: CaseConfig) -> tuple[int, int]:
    return int(round(case.nx * case.roll_x_fraction)), int(round(case.ny * case.roll_y_fraction))


def rolled_extended_axis(axis: np.ndarray, roll: int, spacing: float) -> np.ndarray:
    if roll == 0:
        return axis
    rolled = np.roll(axis, roll).astype(np.float64, copy=True)
    wrap = roll % axis.size
    if wrap:
        rolled[:wrap] -= axis.size * spacing
    return rolled


def roll_large_domain(field: np.ndarray, case: CaseConfig) -> np.ndarray:
    roll_x, roll_y = roll_offsets(case)
    if roll_x == 0 and roll_y == 0:
        return field
    return np.roll(field, shift=(roll_y, roll_x), axis=(-2, -1))


def build_cf_dataset(
    case: CaseConfig,
    models: list[Model],
    skip_days: int,
    days: int,
    steps_per_day: int,
    half_grid_shift: bool,
) -> xr.Dataset:
    lon, lat = lon_lat(case, half_grid_shift)
    data_vars: dict[str, tuple[tuple[str, ...], np.ndarray]] = {}
    steps_by_model: list[list[int]] = []
    source_cases: dict[str, str] = {}
    height_candidates: dict[str, np.ndarray] = {}

    for model in models:
        if model == "VVM":
            rain, height, steps = read_vvm(case, skip_days, days, steps_per_day)
            source_cases[model] = str(case.vvm_case)
        elif model == "VVMex":
            rain, height, steps = read_vvmex(case, skip_days, days, steps_per_day)
            source_cases[model] = str(case.vvmex_case)
        else:
            raise ValueError(f"Unknown model: {model}")
        if rain.shape != (case.ny, case.nx):
            raise ValueError(f"{model} rain shape {rain.shape}; expected {(case.ny, case.nx)}")
        if height.shape != (case.ny, case.nx):
            raise ValueError(f"{model} height shape {height.shape}; expected {(case.ny, case.nx)}")
        rain = roll_large_domain(rain, case)
        height = roll_large_domain(height, case)
        height_candidates[model] = height.astype(np.float32)
        suffix = model.lower()
        data_vars[f"rain_{suffix}"] = (
            ("time", "lev", "lat", "lon"),
            rain.astype(np.float32)[None, None, :, :],
        )
        steps_by_model.append(steps)

    if not height_candidates:
        raise RuntimeError("No model data were read")
    common_height_model = "VVM" if "VVM" in height_candidates else models[0]
    common_height = height_candidates[common_height_model]
    for model, height in height_candidates.items():
        if model == common_height_model:
            continue
        if not np.allclose(common_height, height, rtol=0.0, atol=1.0):
            max_abs_diff = float(np.max(np.abs(common_height.astype(np.float64) - height.astype(np.float64))))
            print(
                f"  warning: {model} height differs from {common_height_model} height; "
                f"max abs diff = {max_abs_diff:.3f} m",
                flush=True,
            )
    first_steps = steps_by_model[0]
    for model, steps in zip(models[1:], steps_by_model[1:]):
        if steps != first_steps:
            raise ValueError(f"{model} averaged steps differ from {models[0]} averaged steps")

    time_seconds = float(np.mean(first_steps) * 10.0 * 60.0)
    roll_x, roll_y = roll_offsets(case)
    data_vars["height"] = (("time", "lev", "lat", "lon"), common_height[None, None, :, :])
    data_vars["averaged_steps"] = (("sample",), np.asarray(first_steps, dtype=np.int32))
    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "lon": lon,
            "lat": lat,
            "lev": np.asarray([0.0], dtype=np.float64),
            "time": np.asarray([time_seconds], dtype=np.float64),
            "sample": np.arange(len(first_steps), dtype=np.int32),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": f"{case.exp_name} daily-mean rainfall and terrain height",
            "case": case.exp_name,
            "resolution": case.resolution,
            "models": ", ".join(models),
            "source_cases": "; ".join(f"{model}: {source_cases[model]}" for model in models),
            "height_source_model": common_height_model,
            "skip_days": skip_days,
            "averaged_days": days,
            "steps_per_day": steps_per_day,
            "half_grid_shift": int(half_grid_shift),
            "data_roll_x_grid_cells": roll_x,
            "data_roll_y_grid_cells": roll_y,
            "data_roll_x_fraction_of_domain": case.roll_x_fraction,
            "data_roll_y_fraction_of_domain": case.roll_y_fraction,
            "data_roll_definition": "Positive x roll moves data right/east; positive y roll moves data up/north. Wrapped data are assigned extended monotonic lon/lat coordinates, so coordinate axes are not cyclic.",
            "rain_definition": "Mean precipitation rate over averaged_steps multiplied by 86400.",
            "history": "Created by scripts/exp_taiwanvvm/plot_daily_rain.py",
        },
    )
    add_cf_attrs(ds)
    return ds


def add_cf_attrs(ds: xr.Dataset) -> None:
    ds["lon"].attrs.update(
        standard_name="longitude",
        long_name="longitude",
        units="degrees_east",
        axis="X",
    )
    ds["lat"].attrs.update(
        standard_name="latitude",
        long_name="latitude",
        units="degrees_north",
        axis="Y",
    )
    ds["time"].attrs.update(
        standard_name="time",
        long_name="midpoint of daily-mean averaging period",
        units="seconds since 1998-01-01 00:00:00",
        calendar="standard",
        axis="T",
    )
    ds["lev"].attrs.update(
        standard_name="height",
        long_name="surface level",
        units="m",
        positive="up",
        axis="Z",
    )
    for name in ds.data_vars:
        if name.startswith("rain_"):
            model = name.removeprefix("rain_")
            ds[name].attrs.update(
                long_name=f"{model} daily-mean precipitation rate",
                units="mm day-1",
            )
        elif name == "height":
            ds[name].attrs.update(
                standard_name="surface_altitude",
                long_name="terrain height above mean sea level",
                units="m",
            )
    ds["averaged_steps"].attrs.update(long_name="model output steps included in the daily mean")


def write_dataset(ds: xr.Dataset, path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        print(f"  exists, skip: {path}", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = {
        name: {"zlib": True, "complevel": 4, "shuffle": True}
        for name in ds.data_vars
        if ds[name].ndim > 0
    }
    ds.to_netcdf(path, engine="netcdf4", encoding=encoding)
    print(f"  wrote NetCDF: {path}", flush=True)


def main() -> None:
    args = parse_args()
    half_grid_shift = not args.no_half_grid_shift
    for case in selected_cases(args.case):
        models = selected_models(args.model)
        output = output_path(args.output_dir.expanduser().resolve(), case, models, args.skip_days, args.days, half_grid_shift)
        if output.exists() and not args.overwrite:
            print(f"  exists, skip: {output}", flush=True)
            continue
        ds = build_cf_dataset(case, models, args.skip_days, args.days, args.steps_per_day, half_grid_shift)
        try:
            write_dataset(ds, output, args.overwrite)
        finally:
            ds.close()


if __name__ == "__main__":
    main()
