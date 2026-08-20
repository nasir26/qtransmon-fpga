"""Time evolution. Implements CLAUDE.md section 2.

This is the M0 golden reference, so exact evolution (diagonal phases for free evolution,
scipy.linalg.expm for the RWA-driven case) is the correct choice — it is the ground
truth that the M1 fixed-point model and M2 RTL datapath get compared against, not an
implementation to be costed in hardware terms. Trotter-splitting and the
numerics.integrator config knob (trotter1/trotter2/rk4) belong to that later fixed-point
model; requesting them here raises NotImplementedError rather than silently returning an
approximate "golden" trajectory.
"""
from __future__ import annotations

import numpy as np
from scipy.constants import hbar
from scipy.linalg import expm

from physics.hamiltonians import drive_hamiltonian_rwa


def propagate_free(psi0: np.ndarray, N: int, w01: float, times: np.ndarray) -> np.ndarray:
    """Exact free evolution under H = hbar*w01*(a_dag*a + 1/2): a pure per-level phase
    rotation, O(N) per step (CLAUDE.md section 3 facts 1-2), not a dense matrix exponential.

    Returns an array of shape (len(times), N).
    """
    n = np.arange(N, dtype=float)
    phases = np.exp(-1j * w01 * np.outer(times, n + 0.5))
    return phases * psi0[None, :]


def propagate_driven_rwa(
    psi0: np.ndarray,
    N: int,
    Omega: float,
    delta: float,
    times: np.ndarray,
    method: str = "exact",
) -> np.ndarray:
    """Evolve under the time-independent RWA drive Hamiltonian (CLAUDE.md section 2) via
    exact diagonalization/matrix exponential. Returns an array of shape (len(times), N).
    """
    if method != "exact":
        raise NotImplementedError(
            f"method={method!r}: the M0 golden model only supports exact evolution; "
            "trotter1/trotter2/rk4 belong to the M1 fixed-point model."
        )

    H = drive_hamiltonian_rwa(N, Omega, delta)
    states = np.empty((len(times), N), dtype=complex)
    for i, t in enumerate(times):
        U = expm(-1j * H * t / hbar)
        states[i] = U @ psi0
    return states
