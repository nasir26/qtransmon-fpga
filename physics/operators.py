"""Truncated Fock-space operators. Implements CLAUDE.md section 2 (LC quantization) and
embodies structural fact 1 of section 3: a and a_dag are strictly bidiagonal, so every
operator built from them stays O(N) to apply even though we store them densely here for
readability in the golden model.
"""
from __future__ import annotations

import numpy as np
from scipy.special import gammaln


def annihilation(N: int) -> np.ndarray:
    """a|n> = sqrt(n)|n-1>, CLAUDE.md section 3 fact 1."""
    return np.diag(np.sqrt(np.arange(1, N)), k=1)


def creation(N: int) -> np.ndarray:
    """a_dag|n> = sqrt(n+1)|n+1>, CLAUDE.md section 3 fact 1."""
    return annihilation(N).conj().T


def number_op(N: int) -> np.ndarray:
    """a_dag @ a, diagonal 0..N-1."""
    return np.diag(np.arange(N, dtype=float))


def identity(N: int) -> np.ndarray:
    return np.eye(N)


def charge_operator(N: int, hbar: float, Z0: float) -> np.ndarray:
    """Q = i*sqrt(hbar/(2*Z0))*(a_dag - a), CLAUDE.md section 2."""
    a = annihilation(N)
    a_dag = creation(N)
    return 1j * np.sqrt(hbar / (2.0 * Z0)) * (a_dag - a)


def flux_operator(N: int, hbar: float, Z0: float) -> np.ndarray:
    """Phi = sqrt(hbar*Z0/2)*(a_dag + a), CLAUDE.md section 2."""
    a = annihilation(N)
    a_dag = creation(N)
    return np.sqrt(hbar * Z0 / 2.0) * (a_dag + a)


def coherent_state(N: int, alpha: complex) -> np.ndarray:
    """Normalized truncated Fock-basis coherent state |alpha> = e^{-|a|^2/2} sum a^n/sqrt(n!) |n>.

    log(n!) is computed via lgamma(n+1) to avoid overflow at the N ~ 32-64 truncations
    used here; the |alpha|=0 term (n=0) is handled by log(0+eps) staying finite while its
    coefficient magnitude e^{-|a|^2/2} is unaffected.
    """
    n = np.arange(N)
    log_terms = n * np.log(np.abs(alpha) + 1e-300) - 0.5 * gammaln(n + 1.0) - 0.5 * np.abs(alpha) ** 2
    coeffs = np.exp(log_terms) * np.exp(1j * np.angle(alpha) * n)
    return coeffs / np.linalg.norm(coeffs)


def populations(psi: np.ndarray) -> np.ndarray:
    return np.abs(psi) ** 2


def expectation(psi: np.ndarray, op: np.ndarray) -> complex:
    return complex(np.vdot(psi, op @ psi))


def mandel_q(psi: np.ndarray, N: int) -> float:
    """Q = (<n^2> - <n>^2)/<n> - 1. Q=0 for a coherent state (Poissonian statistics)."""
    n_op = number_op(N)
    n_mean = expectation(psi, n_op).real
    n2_mean = expectation(psi, n_op @ n_op).real
    if n_mean <= 0:
        return 0.0
    return (n2_mean - n_mean**2) / n_mean - 1.0
