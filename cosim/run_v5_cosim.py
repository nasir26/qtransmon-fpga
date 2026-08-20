"""M2 cosim harness (V5, CLAUDE.md section 6, partial scope: free evolution only --
the RWA drive term is not implemented in RTL yet, see rtl/src/free_evolution_engine.v).
Builds the engine with Verilator, runs it for 10,000 steps from a random initial state,
and compares the final state to the M0 golden model, for every format in Q_FORMATS (not
just the config default) so the real, RTL-verified picture of which formats actually
clear the gate is on record, not just the software prediction from physics/fixed_point.py.

Verilator stands in for Vivado xsim, which has not been available in any environment
this project has run in -- CLAUDE.md section 4 names "Verilator/xsim" as the intended
cosim harness, so this is not a silent substitution. See docs/validation.md.

Run: PYTHONPATH=. venv/bin/python cosim/run_v5_cosim.py
"""
from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from physics.fixed_point import Q_FORMATS, infidelity, quantize
from physics.hamiltonians import load_config
from physics.propagator import propagate_free
from rtl.rom.gen_roms import generate_free_evolution_roms
from rtl.rom.hexio import read_hex_file_as_real, write_hex_file

REPO_ROOT = Path(__file__).resolve().parent.parent
COSIM_DIR = Path(__file__).resolve().parent
BUILD_DIR = COSIM_DIR / "obj_dir"
RESULTS_PATH = COSIM_DIR / "results_v5_free_evolution.json"

N_STEPS = 10_000
V5_INFIDELITY_THRESHOLD = 1e-4


def build_sim() -> Path:
    # Verilator 4.028 (installed here) predates the single-shot --build flag, so the
    # generate and make steps are run separately.
    subprocess.run(
        [
            "verilator",
            "--cc",
            "--exe",
            "-Wno-fatal",
            "-I" + str(REPO_ROOT / "rtl" / "rom"),
            str(REPO_ROOT / "rtl" / "src" / "free_evolution_engine.v"),
            str(COSIM_DIR / "tb_free_evolution.cpp"),
            "--top-module",
            "free_evolution_engine",
            "-Mdir",
            str(BUILD_DIR),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        ["make", "-C", str(BUILD_DIR), "-f", "Vfree_evolution_engine.mk"],
        check=True,
    )
    return BUILD_DIR / "Vfree_evolution_engine"


def run_cosim(format_name: str | None = None) -> dict[str, Any]:
    """format_name overrides cfg['fixed_point']['format'] for sweeping; None uses the
    config default (Q2.14)."""
    cfg = load_config()
    if format_name is not None:
        cfg = copy.deepcopy(cfg)
        cfg["fixed_point"]["format"] = format_name

    N = cfg["numerics"]["fock_levels"]
    w01 = cfg["oscillator"]["w01"]
    dt = cfg["numerics"]["dt_s"]
    format_name = cfg["fixed_point"]["format"]
    int_bits, frac_bits = Q_FORMATS[format_name]
    data_width = int_bits + frac_bits

    rom_params = generate_free_evolution_roms(cfg)
    assert (rom_params["DATA_WIDTH"], rom_params["FRAC_BITS"]) == (data_width, frac_bits)

    sim_path = build_sim()

    rng = np.random.default_rng(0)
    raw = rng.normal(size=N) + 1j * rng.normal(size=N)
    psi0 = raw / np.linalg.norm(raw)

    psi0_re_q = quantize(psi0.real, int_bits, frac_bits)
    psi0_im_q = quantize(psi0.imag, int_bits, frac_bits)

    in_re_path = COSIM_DIR / "state_in_re.hex"
    in_im_path = COSIM_DIR / "state_in_im.hex"
    out_re_path = COSIM_DIR / "state_out_re.hex"
    out_im_path = COSIM_DIR / "state_out_im.hex"
    write_hex_file(in_re_path, psi0_re_q, frac_bits, data_width)
    write_hex_file(in_im_path, psi0_im_q, frac_bits, data_width)

    subprocess.run(
        [
            str(sim_path),
            str(in_re_path),
            str(in_im_path),
            str(N_STEPS),
            str(out_re_path),
            str(out_im_path),
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    rtl_re = read_hex_file_as_real(out_re_path, frac_bits, data_width)
    rtl_im = read_hex_file_as_real(out_im_path, frac_bits, data_width)
    psi_rtl = rtl_re + 1j * rtl_im

    psi_golden = propagate_free(psi0, N, w01, np.array([N_STEPS * dt]))[0]

    infid = infidelity(psi_rtl, psi_golden)

    return {
        "n_steps": N_STEPS,
        "format": format_name,
        "N": N,
        "rom_data_width": rom_params["ROM_DATA_WIDTH"],
        "rom_frac_bits": rom_params["ROM_FRAC_BITS"],
        "infidelity": infid,
        "threshold": V5_INFIDELITY_THRESHOLD,
        "pass": infid < V5_INFIDELITY_THRESHOLD,
    }


def main() -> None:
    results = [run_cosim(format_name=name) for name in Q_FORMATS]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "free evolution only -- RWA drive term not yet in RTL",
        "note": (
            "V5 (CLAUDE.md section 6): RTL vs golden model, run via Verilator (not "
            "Vivado xsim -- unavailable in this environment; see docs/validation.md). "
            "ROM widened to rom_data_width bits (decoupled from the state format) after "
            "the first V5 attempt found the dominant error source was the ROM's "
            "quantized rotation angle, not per-step state rounding."
        ),
        "config_default_format": load_config()["fixed_point"]["format"],
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"{'Format':<8} {'Infidelity':>14} {'Status':>6}")
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"{r['format']:<8} {r['infidelity']:>14.3e} {status:>6}")
    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
