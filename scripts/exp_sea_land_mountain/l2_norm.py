"""L2 metrics with optional atmospheric mass weighting."""

from __future__ import annotations

import numpy as np


def layer_thickness(z_mid: np.ndarray) -> np.ndarray:
    """Derive layer thicknesses from monotonically increasing layer centers."""
    z_mid = np.asarray(z_mid, dtype=np.float64)
    if z_mid.ndim != 1 or z_mid.size < 2:
        raise ValueError("z_mid must be a one-dimensional array with at least 2 levels")
    if not np.all(np.diff(z_mid) > 0.0):
        raise ValueError("z_mid must be strictly increasing")

    edges = np.empty(z_mid.size + 1, dtype=np.float64)
    edges[1:-1] = 0.5 * (z_mid[:-1] + z_mid[1:])
    edges[0] = z_mid[0] - 0.5 * (z_mid[1] - z_mid[0])
    edges[-1] = z_mid[-1] + 0.5 * (z_mid[-1] - z_mid[-2])
    dz = np.diff(edges)
    if not np.all(dz > 0.0):
        raise ValueError("Derived layer thickness contains non-positive values")
    return dz


def atmospheric_mask(topo_indices: np.ndarray, nz: int) -> np.ndarray:
    """Return (z, y, x) mask, including the selected near-surface layer."""
    topo_indices = np.asarray(topo_indices)
    if topo_indices.ndim != 2:
        raise ValueError("topo_indices must have shape (y, x)")
    if topo_indices.min() < 0 or topo_indices.max() >= nz:
        raise IndexError("topography index is outside the vertical domain")
    return np.arange(nz)[:, None, None] >= topo_indices[None, :, :]


def weighted_l2_norm(
    error: np.ndarray,
    rho: np.ndarray,
    dz: np.ndarray,
    mask: np.ndarray | None = None,
    *,
    normalize: bool = True,
) -> float:
    """Compute sqrt(sum(rho*dz*error^2) / sum(rho*dz)).

    Set ``normalize=False`` to return the non-normalized discrete weighted norm
    ``sqrt(sum(rho*dz*error^2))``.
    """
    error = np.asarray(error, dtype=np.float64)
    rho = np.asarray(rho, dtype=np.float64)
    dz = np.asarray(dz, dtype=np.float64)
    if error.ndim != 3:
        raise ValueError(f"error must have shape (z, y, x), got {error.shape}")
    if rho.shape != (error.shape[0],) or dz.shape != (error.shape[0],):
        raise ValueError(
            f"rho and dz must have shape ({error.shape[0]},), got "
            f"{rho.shape} and {dz.shape}"
        )
    if np.any(rho <= 0.0) or np.any(dz <= 0.0):
        raise ValueError("rho and dz must be positive")

    valid = np.isfinite(error)
    if mask is not None:
        if mask.shape != error.shape:
            raise ValueError(f"mask shape {mask.shape} does not match {error.shape}")
        valid &= mask
    if not np.any(valid):
        raise ValueError("No valid cells are available for the weighted L2 norm")

    weights = np.broadcast_to((rho * dz)[:, None, None], error.shape)
    weighted_square_sum = np.sum(weights[valid] * error[valid] ** 2)
    if not normalize:
        return float(np.sqrt(weighted_square_sum))
    return float(np.sqrt(weighted_square_sum / np.sum(weights[valid])))


def relative_weighted_l2_norm(
    error: np.ndarray,
    reference: np.ndarray,
    rho: np.ndarray,
    dz: np.ndarray,
    mask: np.ndarray | None = None,
) -> float:
    """Compute sqrt(sum(w*error^2) / sum(w*reference^2)), w=rho*dz."""
    error = np.asarray(error, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if reference.shape != error.shape:
        raise ValueError(
            f"reference shape {reference.shape} does not match error shape {error.shape}"
        )

    valid = np.isfinite(error) & np.isfinite(reference)
    if mask is not None:
        if mask.shape != error.shape:
            raise ValueError(f"mask shape {mask.shape} does not match {error.shape}")
        valid &= mask
    if not np.any(valid):
        raise ValueError("No valid cells are available for the relative L2 norm")

    weights = np.broadcast_to(
        (np.asarray(rho, dtype=np.float64) * np.asarray(dz, dtype=np.float64))[
            :, None, None
        ],
        error.shape,
    )
    numerator = np.sum(weights[valid] * error[valid] ** 2)
    denominator = np.sum(weights[valid] * reference[valid] ** 2)
    return float(np.sqrt(numerator / denominator)) if denominator > 0.0 else np.nan
