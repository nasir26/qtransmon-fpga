"""M1 gate: Q1.15/Q2.14/Q4.12 sweep, infidelity of the fixed-point free-evolution
recurrence against the M0 golden model, at the table configuration cited in the paper
(paper/main.tex Table "fixedpoint": N=32, 10^4 steps). CLAUDE.md section 10: every
number here comes from this script actually running; DSP/LUT/f_max are left out because
they require Vivado synthesis (M2), not a Python run.

Run: venv/bin/python bench/quantization/sweep_precision.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from physics.fixed_point import sweep_q_formats
from physics.hamiltonians import load_config

RESULTS_PATH = Path(__file__).resolve().parent / "results_quantization_sweep.json"


def main() -> None:
    cfg = load_config()
    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    dt = cfg["numerics"]["dt_s"]
    n_steps = 10_000

    rng = np.random.default_rng(0)
    raw = rng.normal(size=N) + 1j * rng.normal(size=N)
    psi0 = raw / np.linalg.norm(raw)

    results = sweep_q_formats(psi0, N, w01, dt, n_steps)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"N": N, "w01_rad_s": w01, "dt_s": dt, "n_steps": n_steps},
        "note": (
            "Infidelity is from a Python bit-rounding emulation of the free-evolution "
            "phase-rotation recurrence (CLAUDE.md section 3 fact 1), not the RTL cosim "
            "(that is V5/M2). DSP/LUT/f_max are not measured here; they require Vivado "
            "synthesis."
        ),
        "results": [
            {
                "format": r.format_name,
                "int_bits": r.int_bits,
                "frac_bits": r.frac_bits,
                "n_steps": r.n_steps,
                "infidelity": r.infidelity,
            }
            for r in results
        ],
    }

    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"{'Format':<8} {'Infidelity':>14}")
    for r in results:
        print(f"{r.format_name:<8} {r.infidelity:>14.3e}")
    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
