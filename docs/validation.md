Validation gates V1-V13 are specified in CLAUDE.md section 6. They are implemented
as pytest cases under physics/, cosim/, and circuit/ as each milestone closes.
CI runs the full suite on every commit.

## Status

- V1-V4: **PASS**, `physics/tests/`. M0 golden model (`lc` mode).
- M1 (fixed-point Q-format sweep, no assigned V-number): infidelity measured and
  committed at `bench/quantization/results_quantization_sweep.json`; sanity-checked by
  `physics/tests/test_m1_fixed_point.py`.
- V5 onward: **blocked**. They require Vivado xsim (V5, V10), eventually the Alveo U55C
  itself (V11, resource/crossover numbers), and the external `fpga_rtl` backend (V9,
  V11) — none of which have been available in the environments this project has run in
  so far. Per CLAUDE.md section 10, these stay TBD rather than estimated.
