"""M1: fixed-point Python model of the free-evolution recurrence, for the Q-format
sweep required by CLAUDE.md section 7 ("swept over Q1.15 / Q2.14 / Q4.12 with fidelity
... reported for each") before any format is committed to RTL in M2.

This is a rounding-accurate emulation of the per-step complex-multiply recurrence a
Verilog datapath would run (CLAUDE.md section 3 fact 1: free evolution is a per-level
phase rotation, O(N), driven by ROM-stored sqrt(n)/phase-increment constants) — it
quantizes both the ROM constant and the product at every step, so quantization noise
accumulates the way it would in fixed-point hardware. It is a software estimate of
infidelity only, not a substitute for the RTL cosim in M2 (V5); DSP/LUT/f_max cost is
a synthesis result and stays TBD until M2 actually runs through Vivado.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# int_bits includes the sign bit, matching CLAUDE.md section 7's Q1.15/Q2.14/Q4.12 naming
# (Qm.f = m integer bits incl. sign, f fractional bits), all 16 bits total.
Q_FORMATS: dict[str, tuple[int, int]] = {
    "Q1.15": (1, 15),
    "Q2.14": (2, 14),
    "Q4.12": (4, 12),
}


def quantize(x: np.ndarray, int_bits: int, frac_bits: int) -> np.ndarray:
    """Round-to-nearest, saturate to the representable range of a signed Q(int_bits).
    (frac_bits) fixed-point format.
    """
    scale = 2.0**frac_bits
    lo = -(2.0 ** (int_bits - 1))
    hi = 2.0 ** (int_bits - 1) - 2.0**-frac_bits
    return np.clip(np.round(x * scale) / scale, lo, hi)


@dataclass
class SweepResult:
    format_name: str
    int_bits: int
    frac_bits: int
    n_steps: int
    infidelity: float


def fixed_point_free_evolution(
    psi0: np.ndarray, N: int, w01: float, dt: float, n_steps: int, int_bits: int, frac_bits: int
) -> np.ndarray:
    """Step the free-evolution phase rotation n_steps times, quantizing the per-level
    rotator (cos/sin ROM entries) and the state after every complex multiply.
    """
    n = np.arange(N, dtype=float)
    theta = w01 * (n + 0.5) * dt
    rot_re = quantize(np.cos(theta), int_bits, frac_bits)
    rot_im = quantize(np.sin(theta), int_bits, frac_bits)

    re = quantize(psi0.real, int_bits, frac_bits)
    im = quantize(psi0.imag, int_bits, frac_bits)

    for _ in range(n_steps):
        # (re + i*im) * (rot_re - i*rot_im): phase advances by -theta per step, matching
        # propagate_free's exp(-i*w01*(n+1/2)*t) convention.
        new_re = re * rot_re + im * rot_im
        new_im = im * rot_re - re * rot_im
        re = quantize(new_re, int_bits, frac_bits)
        im = quantize(new_im, int_bits, frac_bits)

    return re + 1j * im


def infidelity(psi_a: np.ndarray, psi_b: np.ndarray) -> float:
    """1 - |<a|b>|^2 / (|a|^2 |b|^2), scale-invariant so unnormalized fixed-point drift
    doesn't get conflated with phase/population error."""
    overlap = np.vdot(psi_a, psi_b)
    norm_a = np.vdot(psi_a, psi_a).real
    norm_b = np.vdot(psi_b, psi_b).real
    fidelity = (np.abs(overlap) ** 2) / (norm_a * norm_b)
    # fidelity is in [0, 1] by Cauchy-Schwarz; clip away floating-point noise at the
    # boundary (e.g. exactly-representable states giving fidelity = 1 + eps).
    return float(max(0.0, 1.0 - fidelity))


def sweep_q_formats(
    psi0: np.ndarray, N: int, w01: float, dt: float, n_steps: int
) -> list[SweepResult]:
    from physics.propagator import propagate_free

    exact = propagate_free(psi0, N, w01, np.array([n_steps * dt]))[0]

    results = []
    for name, (int_bits, frac_bits) in Q_FORMATS.items():
        psi_fixed = fixed_point_free_evolution(psi0, N, w01, dt, n_steps, int_bits, frac_bits)
        results.append(
            SweepResult(
                format_name=name,
                int_bits=int_bits,
                frac_bits=frac_bits,
                n_steps=n_steps,
                infidelity=infidelity(psi_fixed, exact),
            )
        )
    return results
