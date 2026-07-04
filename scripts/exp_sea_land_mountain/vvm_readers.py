"""Readers that expose CPU NetCDF and GPU HDF5 VVM output consistently."""

from __future__ import annotations

import re
from pathlib import Path

import h5py
import numpy as np
import xarray as xr
from vvmtools.analyze import DataRetriever


_STEP_RE = re.compile(r"-(\d{6})\.nc$")
_GPU_STEP_RE = re.compile(r"vvm_output_(\d{6})\.h5$")


class CPUReader:
    """Read the legacy CPU VVM NetCDF output through VVMTools."""

    def __init__(self, case_path: str | Path) -> None:
        self.case_path = Path(case_path).expanduser().resolve()
        if not self.case_path.is_dir():
            raise FileNotFoundError(f"CPU case directory not found: {self.case_path}")

        self._dynamic_files = self._index_dynamic_files()
        if not self._dynamic_files:
            raise FileNotFoundError(
                f"No *.L.Dynamic-XXXXXX.nc files found below {self.case_path}"
            )

        self.retriever = DataRetriever(case_path=str(self.case_path))

    def _index_dynamic_files(self) -> dict[int, Path]:
        files: dict[int, Path] = {}
        for path in self.case_path.rglob("*.L.Dynamic-*.nc"):
            match = _STEP_RE.search(path.name)
            if match:
                files[int(match.group(1))] = path
        return files

    @property
    def steps(self) -> tuple[int, ...]:
        return tuple(sorted(self._dynamic_files))

    @property
    def x(self) -> np.ndarray:
        return np.asarray(self.retriever.DIM["xc"], dtype=np.float64)

    @property
    def y(self) -> np.ndarray:
        return np.asarray(self.retriever.DIM["yc"], dtype=np.float64)

    @property
    def z(self) -> np.ndarray:
        """The 99 common model levels after dropping the CPU bottom level."""
        first_path = self._dynamic_files[self.steps[0]]
        with xr.open_dataset(first_path, decode_times=False) as dataset:
            return np.asarray(dataset["zc"], dtype=np.float64)[1:]

    def read_topo(self) -> np.ndarray:
        """Return CPU topography as the integer near-surface level index."""
        topo = self.retriever.get_var("topo", 0)
        if topo is None:
            raise KeyError("Variable 'topo' was not found in CPU TOPO.nc")
        return np.asarray(topo, dtype=np.float64)

    def read_3d(self, variable: str, step: int) -> np.ndarray:
        """Return (z, y, x), dropping CPU level zero when 100 levels exist."""
        if step not in self._dynamic_files:
            raise KeyError(f"CPU step {step:06d} is unavailable")

        data = self.retriever.get_var(variable, step, numpy=True)
        if data is None:
            raise KeyError(f"CPU variable {variable!r} is unavailable at step {step:06d}")

        data = np.asarray(data)
        if data.ndim != 3:
            raise ValueError(
                f"CPU {variable!r} at step {step:06d} has shape {data.shape}; "
                "expected a 3-D field"
            )
        if data.shape[0] == 100:
            data = data[1:, :, :]
        if data.shape[0] != 99:
            raise ValueError(
                f"CPU {variable!r} has {data.shape[0]} levels after normalization; "
                "expected 99"
            )
        return data

    def time_minutes(self, step: int) -> float:
        path = self._dynamic_files[step]
        with xr.open_dataset(path, decode_times=False) as dataset:
            return float(np.asarray(dataset["time"]).squeeze())


class GPUReader:
    """Read one-timestep-per-file GPU VVM HDF5 output."""

    def __init__(self, case_path: str | Path) -> None:
        self.case_path = Path(case_path).expanduser().resolve()
        if not self.case_path.is_dir():
            raise FileNotFoundError(f"GPU case directory not found: {self.case_path}")

        self._files = self._index_files()
        if not self._files:
            raise FileNotFoundError(
                f"No vvm_output_XXXXXX.h5 files found in {self.case_path}"
            )

    def _index_files(self) -> dict[int, Path]:
        files: dict[int, Path] = {}
        for path in self.case_path.glob("vvm_output_*.h5"):
            match = _GPU_STEP_RE.fullmatch(path.name)
            if match:
                files[int(match.group(1))] = path
        return files

    @property
    def steps(self) -> tuple[int, ...]:
        return tuple(sorted(self._files))

    def _read_coordinate(self, name: str) -> np.ndarray:
        first_step = self.steps[0]
        with h5py.File(self._files[first_step], "r") as handle:
            return np.asarray(handle[f"Step0/coordinates/{name}"][:], dtype=np.float64)

    @property
    def x(self) -> np.ndarray:
        return self._read_coordinate("x")

    @property
    def y(self) -> np.ndarray:
        return self._read_coordinate("y")

    @property
    def z(self) -> np.ndarray:
        return self._read_coordinate("z_mid")

    def read_2d(self, variable: str, step: int) -> np.ndarray:
        with h5py.File(self._files[step], "r") as handle:
            data = np.asarray(handle[f"Step0/{variable}"][:])
        if data.ndim != 2:
            raise ValueError(
                f"GPU {variable!r} at step {step:06d} has shape {data.shape}; "
                "expected a 2-D field"
            )
        return data

    def read_profile(self, variable: str, step: int | None = None) -> np.ndarray:
        """Read a one-dimensional profile from Step0."""
        selected_step = self.steps[0] if step is None else step
        with h5py.File(self._files[selected_step], "r") as handle:
            data = np.asarray(handle[f"Step0/{variable}"][:], dtype=np.float64)
        if data.ndim != 1:
            raise ValueError(
                f"GPU {variable!r} at step {selected_step:06d} has shape "
                f"{data.shape}; expected a 1-D profile"
            )
        return data

    def read_3d(self, variable: str, step: int) -> np.ndarray:
        if step not in self._files:
            raise KeyError(f"GPU step {step:06d} is unavailable")
        with h5py.File(self._files[step], "r") as handle:
            data = np.asarray(handle[f"Step0/{variable}"][:])
        if data.ndim != 3 or data.shape[0] != 99:
            raise ValueError(
                f"GPU {variable!r} at step {step:06d} has shape {data.shape}; "
                "expected (99, y, x)"
            )
        return data

    def time_minutes(self, step: int) -> float:
        with h5py.File(self._files[step], "r") as handle:
            time_seconds = float(handle["Step0/time"][()])
        return time_seconds / 60.0
