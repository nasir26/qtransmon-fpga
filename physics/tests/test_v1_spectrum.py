"""V1 (CLAUDE.md section 6): truncated spectrum matches hbar*w01*(n + 1/2) to 1e-10 for
n < N-2.
"""
import numpy as np

from physics.analytic import spectrum_lc
from physics.hamiltonians import lc_hamiltonian, load_config


def test_v1_spectrum_matches_analytic():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]

    H_diag = lc_hamiltonian(N, w01)
    E_analytic = spectrum_lc(N, w01)

    # lc_hamiltonian is exactly diagonal (CLAUDE.md section 3 fact 1), so its
    # eigenvalues are the diagonal entries themselves, already sorted ascending.
    eigenvalues = np.sort(H_diag)

    interior = slice(0, N - 2)
    assert np.max(np.abs(eigenvalues[interior] - E_analytic[interior])) < 1e-10


def test_v1_energy_spacing_is_hbar_w01():
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]

    H_diag = lc_hamiltonian(N, w01)
    spacing = np.diff(H_diag)

    from scipy.constants import hbar

    assert np.allclose(spacing, hbar * w01, atol=0, rtol=1e-12)
