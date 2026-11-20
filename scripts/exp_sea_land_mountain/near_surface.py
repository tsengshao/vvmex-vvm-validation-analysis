"""Topography indices and extraction for periodic VVM staggered grids."""

from __future__ import annotations

import numpy as np


def build_topography(topo: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return complete u/v/w sampling indices without a vertical offset.

    Unlike the C++ conditional topou/topov flags, these arrays already include
    the fallback to the current cell's topo. Both horizontal axes are periodic.
    """
    topo = np.asarray(topo)
    if topo.ndim != 2:
        raise ValueError(f"Topography must be 2-D, got shape {topo.shape}")
    topou = np.maximum(topo, np.roll(topo, -1, axis=1))
    topov = np.maximum(topo, np.roll(topo, -1, axis=0))
    topow = topo.copy()
    return topou, topov, topow


def topography_for_variable(topo: np.ndarray, variable: str) -> np.ndarray:
    """Select staggered wind topography; other fields use the cell topography."""
    topou, topov, topow = build_topography(topo)
    return {"u": topou, "v": topov, "w": topow}.get(variable, topow)


def validate_topography(topo: np.ndarray, field_shape: tuple[int, ...]) -> np.ndarray:
    """Validate and return integer indices into a (z, y, x) field."""
    if topo.shape != field_shape[1:]:
        raise ValueError(
            f"Topography shape {topo.shape} does not match field y/x shape "
            f"{field_shape[1:]}"
        )
    if not np.all(np.isfinite(topo)) or not np.allclose(topo, np.rint(topo)):
        raise ValueError("Topography must contain finite integer level indices")
    indices = np.rint(topo).astype(np.intp)
    if indices.min() < 0 or indices.max() >= field_shape[0]:
        raise IndexError(
            f"Topography indices [{indices.min()}, {indices.max()}] exceed "
            f"available z indices [0, {field_shape[0] - 1}]"
        )
    return indices


def extract_near_surface(field: np.ndarray, topo_indices: np.ndarray) -> np.ndarray:
    """Select field[topo_indices[y, x], y, x] without a vertical offset.

    CPUReader already removes the CPU bottom level before this operation.
    """
    return np.take_along_axis(field, topo_indices[None, :, :], axis=0)[0]
