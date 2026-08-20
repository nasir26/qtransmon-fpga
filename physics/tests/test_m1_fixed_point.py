"""M1 sanity check: fixed-point free evolution vs the M0 golden model. Not a numbered
CLAUDE.md gate (M1 has no V-number in section 6, unlike V1-V4/V5); this just verifies
the sweep is internally consistent before its numbers go in the paper.
"""
import numpy as np

from physics.fixed_point import fixed_point_free_evolution, infidelity, sweep_q_formats
from physics.hamiltonians import load_config
from physics.propagator import propagate_free


def test_fixed_point_converges_to_golden_as_precision_increases():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    dt = cfg["numerics"]["dt_s"]

    rng = np.random.default_rng(1)
    raw = rng.normal(size=N) + 1j * rng.normal(size=N)
    psi0 = raw / np.linalg.norm(raw)

    n_steps = 500
    exact = propagate_free(psi0, N, w01, np.array([n_steps * dt]))[0]

    coarse = fixed_point_free_evolution(psi0, N, w01, dt, n_steps, int_bits=2, frac_bits=6)
    fine = fixed_point_free_evolution(psi0, N, w01, dt, n_steps, int_bits=2, frac_bits=20)

    assert infidelity(fine, exact) < infidelity(coarse, exact)
    assert infidelity(fine, exact) < 1e-6


def test_sweep_q_formats_runs_and_orders_by_fractional_precision():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    dt = cfg["numerics"]["dt_s"]

    psi0 = np.zeros(N, dtype=complex)
    psi0[1] = 1.0

    results = sweep_q_formats(psi0, N, w01, dt, n_steps=1000)
    by_format = {r.format_name: r.infidelity for r in results}

    assert set(by_format) == {"Q1.15", "Q2.14", "Q4.12"}
    assert all(np.isfinite(v) and v >= 0.0 for v in by_format.values())
    # more fractional bits -> finer rotator resolution -> lower infidelity
    assert by_format["Q1.15"] <= by_format["Q2.14"] <= by_format["Q4.12"]
