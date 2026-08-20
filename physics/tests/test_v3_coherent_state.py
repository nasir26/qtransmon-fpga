"""V3 (CLAUDE.md section 6): coherent state traces the classical LC trajectory, Mandel
Q = 0.
"""
import numpy as np
from scipy.constants import hbar

from physics.analytic import classical_alpha_free
from physics.hamiltonians import load_config
from physics.operators import coherent_state, expectation, mandel_q, populations
from physics.propagator import propagate_driven_rwa


def test_v3_coherent_state_traces_classical_trajectory_and_mandel_q_zero():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    Z0 = cfg["oscillator"]["Z0_ohm"]
    dt = cfg["numerics"]["dt_s"]
    guard = cfg["numerics"]["truncation_guard"]

    alpha0 = 2.0 + 0.5j
    psi0 = coherent_state(N, alpha0)

    pops0 = populations(psi0)
    assert pops0[-2:].sum() < guard, "coherent state amplitude too large for N; violates truncation guard"

    n_steps = 100
    times = np.arange(n_steps) * dt
    # Omega=0, delta=0 reduces drive_hamiltonian_rwa to pure free evolution under
    # hbar*w01*a_dag*a (up to the constant offset the RWA form omits), which is exactly
    # what CLAUDE.md section 2's classical_alpha_free reference tracks.
    states = propagate_driven_rwa(psi0, N, Omega=0.0, delta=w01, times=times)

    n_idx = np.arange(N, dtype=float)
    a = np.diag(np.sqrt(n_idx[1:]), k=1)
    a_dag = a.conj().T
    Q_op = 1j * np.sqrt(hbar / (2.0 * Z0)) * (a_dag - a)
    Phi_op = np.sqrt(hbar * Z0 / 2.0) * (a_dag + a)

    alpha_t = classical_alpha_free(alpha0, w01, times)
    Q_classical = 1j * np.sqrt(hbar / (2.0 * Z0)) * (np.conj(alpha_t) - alpha_t)
    Phi_classical = np.sqrt(hbar * Z0 / 2.0) * (alpha_t + np.conj(alpha_t))

    Q_quantum = np.array([expectation(psi, Q_op) for psi in states])
    Phi_quantum = np.array([expectation(psi, Phi_op) for psi in states])

    assert np.allclose(Q_quantum.real, Q_classical.real, atol=1e-30, rtol=1e-6)
    assert np.allclose(Phi_quantum.real, Phi_classical.real, atol=1e-30, rtol=1e-6)

    mandel = np.array([mandel_q(psi, N) for psi in states])
    assert np.allclose(mandel, 0.0, atol=1e-6)
