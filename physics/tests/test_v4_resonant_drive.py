"""V4 (CLAUDE.md section 6): resonant drive on |0> gives |alpha(t)| = Omega*t/2.
"""
import numpy as np

from physics.analytic import resonant_drive_alpha
from physics.hamiltonians import load_config
from physics.operators import annihilation, expectation, populations
from physics.propagator import propagate_driven_rwa


def test_v4_resonant_drive_gives_rabi_alpha():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    Omega = cfg["drive"]["Omega"]
    guard = cfg["numerics"]["truncation_guard"]

    psi0 = np.zeros(N, dtype=complex)
    psi0[0] = 1.0

    # Stay well inside the region where |alpha(t)| = Omega*t/2 keeps the top-2-level
    # population under the truncation guard (CLAUDE.md section 6): pick t_max so the
    # expected mean photon number |alpha|^2 stays small relative to N.
    t_max = 0.3 * N**0.5 / Omega
    times = np.linspace(0.0, t_max, 50)

    states = propagate_driven_rwa(psi0, N, Omega=Omega, delta=0.0, times=times)

    pops = populations(states)
    assert np.all(pops[:, -2:].sum(axis=1) < guard), "truncation guard violated over the swept time range"

    a = annihilation(N)
    alpha_quantum = np.array([expectation(psi, a) for psi in states])
    alpha_reference = resonant_drive_alpha(Omega, times)

    assert np.allclose(np.abs(alpha_quantum), alpha_reference, atol=1e-6, rtol=1e-3)
