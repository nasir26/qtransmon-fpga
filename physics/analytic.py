"""Closed-form references, independent of the propagator, for cross-checking the golden
model. Implements CLAUDE.md section 2.
"""
from __future__ import annotations

import numpy as np
from scipy.constants import hbar


def spectrum_lc(N: int, w01: float) -> np.ndarray:
    """E_n = hbar*w01*(n + 1/2), CLAUDE.md section 2. Used by V1."""
    return hbar * w01 * (np.arange(N, dtype=float) + 0.5)


def classical_alpha_free(alpha0: complex, w01: float, t: np.ndarray) -> np.ndarray:
    """alpha(t) = alpha0*exp(-i*w01*t): for the harmonic oscillator a coherent state's
    <a> follows the classical LC trajectory exactly (not an approximation). Used by V3.
    """
    return alpha0 * np.exp(-1j * w01 * t)


def resonant_drive_alpha(Omega: float, t: np.ndarray) -> np.ndarray:
    """On resonance (delta=0), starting from |0>, |alpha(t)| = Omega*t/2, CLAUDE.md
    section 6 V4."""
    return Omega * t / 2.0
