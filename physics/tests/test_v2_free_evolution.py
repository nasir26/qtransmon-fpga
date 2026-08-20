"""V2 (CLAUDE.md section 6): free evolution: |c_n|^2 exactly constant, phases linear in
t. This is the built-in correctness oracle from CLAUDE.md section 3 fact 2.
"""
import numpy as np

from physics.hamiltonians import load_config
from physics.operators import populations
from physics.propagator import propagate_free


def test_v2_populations_invariant_and_phases_linear():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    dt = cfg["numerics"]["dt_s"]

    rng = np.random.default_rng(0)
    raw = rng.normal(size=N) + 1j * rng.normal(size=N)
    psi0 = raw / np.linalg.norm(raw)

    n_steps = 200
    times = np.arange(n_steps) * dt
    states = propagate_free(psi0, N, w01, times)

    pops = populations(states)
    pops0 = populations(psi0)
    assert np.allclose(pops, pops0[None, :], atol=1e-12)

    n = np.arange(N, dtype=float)
    phase = np.angle(states) - np.angle(psi0)[None, :]
    phase_unwrapped = np.unwrap(phase, axis=0)
    # expected slope of level n's phase vs t is -w01*(n + 1/2), CLAUDE.md section 2
    expected_slope = -w01 * (n + 0.5)
    fitted_slope = np.polyfit(times, phase_unwrapped, 1)[0]

    populated = pops0 > 1e-8
    assert np.allclose(fitted_slope[populated], expected_slope[populated], rtol=1e-9)
