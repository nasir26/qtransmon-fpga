Validation gates V1-V13 are specified in CLAUDE.md section 6. They are implemented
as pytest cases under physics/, cosim/, and circuit/ as each milestone closes.
CI runs the full suite on every commit.

## Status

- V1-V4: **PASS**, `physics/tests/`. M0 golden model (`lc` mode).
- M1 (fixed-point Q-format sweep, no assigned V-number): infidelity measured and
  committed at `bench/quantization/results_quantization_sweep.json`; sanity-checked by
  `physics/tests/test_m1_fixed_point.py`.
- V5 (partial scope: free evolution only, the RWA drive term is not in RTL yet):
  **measured, RTL-verified.** `rtl/src/free_evolution_engine.v` (the M2 free-evolution
  phase-rotation kernel), `rtl/rom/gen_roms.py` (ROMs generated from
  `config/default.yaml`, never hand-typed), and `cosim/run_v5_cosim.py` (a Verilator
  cosim harness — CLAUDE.md section 4 names "Verilator/xsim" as the intended tool here;
  Vivado xsim itself has not been available in any environment this project has run in)
  are real and working. At 10,000 steps, N=32, against the golden model:

      Q1.15  infidelity = 6.3e-6   PASS
      Q2.14  infidelity = 3.6e-4   FAIL  (this is CLAUDE.md section 7's stated default)
      Q4.12  infidelity = 2.1e-2   FAIL

  Log: `cosim/results_v5_free_evolution.json`. Tests:
  `cosim/tests/test_v5_rtl_vs_golden.py` — `test_v5_passes_at_q1_15` is a real pass;
  `test_v5_fails_at_config_default_q2_14` is `xfail` (tracked, not hidden).

  **History and root cause.** The first attempt (state and ROM sharing one 16-bit
  width) failed at *every* format, including Q1.15 (5.4e-3). Diagnosis: the per-step
  ROM-quantized rotator carries a small systematic angular error that compounds close
  to linearly over 10,000 steps — a frequency error, not just per-step rounding noise
  (confirmed in Python before touching RTL: widening only the ROM's precision, keeping
  state rounding fixed, collapsed the error; widening only the state rounding did not).
  Fix, now in `rtl/src/free_evolution_engine.v`: the rotator ROM is stored at
  `ROM_DATA_WIDTH=32` bits (`rtl/rom/gen_roms.py`), decoupled from the state's own
  `DATA_WIDTH` — cheap, since it's a fixed N_LEVELS-entry table, not something that
  scales with anything. That fixed the ROM's own contribution; what was left is each
  format's *state* storage width, which is a separate, harder floor — Q2.14 and Q4.12
  fail regardless of ROM precision because 14 (or 12) fractional bits alone can't hold
  10,000 steps of accumulated rounding within the 1e-4 budget, only Q1.15's 15 does.

  **Flagging, not silently deciding:** CLAUDE.md section 7 states "default Q2.14 for
  amplitudes" in the contract text itself, and that format measurably fails this gate.
  This document and `config/default.yaml` are left as-is; **recommend the project owner
  either changes the committed default to Q1.15, or accepts Q2.14 needs a wider state
  than 16 bits, or accepts V5 with a caveat** — that's a call for whoever owns the
  contract, not something to silently overwrite here (CLAUDE.md's own opening
  paragraph: "if an instruction here conflicts ... say so explicitly").

- V5 (full scope, with the drive term), V6, V8-V13: **blocked or not started.** They
  require either RTL/hardware not built yet (the drive term, V9, V11), Vivado xsim
  specifically (V10's exponent fit needs a real synthesis/timing run), or the external
  `fpga_rtl` backend (V9, V11) and eventual Alveo U55C access — none of which have been
  available so far. Per CLAUDE.md section 10, these stay TBD rather than estimated.
