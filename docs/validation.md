Validation gates V1-V13 are specified in CLAUDE.md section 6. They are implemented
as pytest cases under physics/, cosim/, and circuit/ as each milestone closes.
CI runs the full suite on every commit.

## Status

- V1-V4: **PASS**, `physics/tests/`. M0 golden model (`lc` mode).
- M1 (fixed-point Q-format sweep, no assigned V-number): infidelity measured and
  committed at `bench/quantization/results_quantization_sweep.json`; sanity-checked by
  `physics/tests/test_m1_fixed_point.py`.
- V5 (partial scope: free evolution only, the RWA drive term is not in RTL yet):
  **measured, currently FAILS.** `rtl/src/free_evolution_engine.v` (the M2 free-
  evolution phase-rotation kernel), `rtl/rom/gen_roms.py` (ROMs generated from
  `config/default.yaml`, never hand-typed), and `cosim/run_v5_cosim.py` (a Verilator
  cosim harness — CLAUDE.md section 4 names "Verilator/xsim" as the intended tool here;
  Vivado xsim itself has not been available in any environment this project has run in)
  are real and working. At 10,000 steps, N=32, infidelity against the golden model is
  **4.1e-2 at Q2.14** (the config default), **5.4e-3 at Q1.15**, far worse at Q4.12 —
  all well above the `< 1e-4` gate. Log: `cosim/results_v5_free_evolution.json`.
  Tracked as `xfail` (not silently skipped) in `cosim/tests/test_v5_rtl_vs_golden.py`.

  Root cause: the per-step ROM-quantized rotator carries a small systematic angular
  error that compounds close to linearly over 10,000 steps (the same effect M1's
  `physics/fixed_point.py` sweep found in software). A software-only re-sweep at wider
  fractional precision (same architecture, not yet built in RTL) found infidelity drops
  below the 1e-4 threshold around **20 fractional bits** (Q2.20, ~7.8e-6 measured) —
  none of the three formats CLAUDE.md section 7 names (Q1.15/Q2.14/Q4.12, all 16-bit)
  reach that. This is a real conflict between the stated format list and what V5 needs
  at a 10,000-step horizon with this recurrence structure, flagged here rather than
  silently worked around (CLAUDE.md's own instruction, header paragraph). Options for
  whoever picks this up: widen the committed format beyond 16 bits, or keep 16-bit
  output but carry extra internal guard bits through the recurrence and round only at
  readout (unverified, not yet implemented).

- V5 (full scope, with the drive term), V6, V8-V13: **blocked or not started.** They
  require either RTL/hardware not built yet (the drive term, V9, V11), Vivado xsim
  specifically (V10's exponent fit needs a real synthesis/timing run), or the external
  `fpga_rtl` backend (V9, V11) and eventual Alveo U55C access — none of which have been
  available so far. Per CLAUDE.md section 10, these stay TBD rather than estimated.
