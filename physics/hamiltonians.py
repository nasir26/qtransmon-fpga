"""Hamiltonian construction. Implements CLAUDE.md section 2.

Only `mode=lc` (and its RWA drive) is implemented: CLAUDE.md section 5 gates the
transmon Hamiltonian to M11 and duffing to the same milestone, so building them now
would be getting ahead of the build order. build_from_config raises NotImplementedError
for those modes rather than guessing at physics that hasn't been validated yet.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.constants import hbar

from physics.operators import annihilation, creation, number_op

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


def _coerce_numeric_strings(node: Any) -> Any:
    """PyYAML 1.1's implicit float resolver requires a signed exponent, so unsigned
    scientific notation like '5.0e9' (used throughout config/default.yaml) loads as a
    str instead of a float. Recursively coerce any string leaf that parses as a float,
    leaving genuine strings (mode names, shapes, formats) untouched.
    """
    if isinstance(node, dict):
        return {k: _coerce_numeric_strings(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_coerce_numeric_strings(v) for v in node]
    if isinstance(node, str):
        try:
            return float(node)
        except ValueError:
            return node
    return node


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Read config/default.yaml. Every constant in this repo traces back here (CLAUDE.md
    section 11)."""
    with open(path or DEFAULT_CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg = _coerce_numeric_strings(cfg)

    cfg["oscillator"]["w01"] = 2.0 * np.pi * cfg["oscillator"]["w01_over_2pi_Hz"]
    cfg["drive"]["Omega"] = 2.0 * np.pi * cfg["drive"]["Omega_over_2pi_Hz"]
    cfg["drive"]["detuning"] = 2.0 * np.pi * cfg["drive"]["detuning_over_2pi_Hz"]
    return cfg


def lc_hamiltonian(N: int, w01: float) -> np.ndarray:
    """H = hbar*w01*(a_dag*a + 1/2), CLAUDE.md section 2. Diagonal (section 3 fact 1)."""
    return hbar * w01 * (np.arange(N, dtype=float) + 0.5)


def drive_hamiltonian_rwa(N: int, Omega: float, delta: float) -> np.ndarray:
    """RWA drive form from CLAUDE.md section 2:

        H = hbar*delta*a_dag*a + (hbar*Omega/2)*(a + a_dag)

    delta = w01 - w_d. Bidiagonal plus a diagonal (section 3 fact 1).
    """
    a = annihilation(N)
    a_dag = creation(N)
    return hbar * delta * number_op(N) + (hbar * Omega / 2.0) * (a + a_dag)


def build_from_config(cfg: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    """Dispatch on cfg['mode']. Returns (H_free, params) for the implemented modes."""
    mode = cfg["mode"]
    N = cfg["numerics"]["fock_levels"]

    if mode == "lc":
        w01 = cfg["oscillator"]["w01"]
        return lc_hamiltonian(N, w01), {"N": N, "w01": w01}

    if mode in ("transmon", "duffing"):
        raise NotImplementedError(
            f"mode={mode!r} is gated to M11 (CLAUDE.md section 5); only 'lc' is "
            "implemented as of M0."
        )

    raise ValueError(f"unknown mode {mode!r}")
