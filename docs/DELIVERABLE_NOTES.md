# qtransmon-fpga — delivery notes

Snapshot of the `main` branch at commit `60d45dd` (2026-08-20). Live repo, with full
history:

    https://github.com/nasir26/qtransmon-fpga

## What's actually done (verified by executed runs)

- **M0** — golden model (`physics/`), `lc` (harmonic oscillator) mode + RWA drive.
  Gates V1-V4 (CLAUDE.md section 6): **PASS**, `physics/tests/`.
- **M1** — fixed-point Q1.15/Q2.14/Q4.12 sweep (`physics/fixed_point.py`,
  `bench/quantization/`). Real infidelity numbers, committed log at
  `bench/quantization/results_quantization_sweep.json`.
- **M2, partial** — a real synthesizable free-evolution kernel
  (`rtl/src/free_evolution_engine.v`), its ROM generated from config
  (`rtl/rom/gen_roms.py`, never hand-typed), and a working Verilator cosim harness
  (`cosim/run_v5_cosim.py`) comparing RTL against the M0 golden model, RTL-swept over
  all three configured formats. **V5 (free evolution only; the RWA drive term is not
  built yet) at N=32, 10,000 steps:**

      Q1.15  infidelity = 6.3e-6   PASS
      Q2.14  infidelity = 3.6e-4   FAIL  <- CLAUDE.md section 7's stated default
      Q4.12  infidelity = 2.1e-2   FAIL

  History: the first attempt failed at *every* format because the rotator ROM's
  quantized angle carries a small systematic per-step frequency error that compounds
  over 10,000 steps. Fix (validated in Python before touching RTL, then confirmed by
  the RTL cosim above): store the ROM at wider internal precision (32-bit, decoupled
  from the state's own width) — cheap, it's a fixed 32-entry table. That fixed the
  ROM's own contribution; Q2.14 and Q4.12 still fail because their *state* storage
  width alone is too coarse at this step count, independent of ROM precision. Full
  account, including this history, in `docs/validation.md`.

  **Flagged, not silently decided:** the contract (`CLAUDE.md` section 7) names Q2.14
  as the default, and that format measurably fails this gate. `config/default.yaml` is
  left unchanged; the recommendation to switch the default to Q1.15 (or accept Q2.14
  needs a wider state) is recorded in `docs/validation.md` for the project owner to
  decide, per `CLAUDE.md`'s own instruction to flag conflicts rather than silently
  resolve them.

- `paper/main.tex` (Journal of Supercomputing, Springer, class `svjour3`) has all of
  this filled in honestly, including the format-dependent V5 result. Everything else
  in its Results section is still `TBD`.

## What's not done, and why

The RWA drive-term RTL, the rest of M2-M12 (NN-in-RTL, full FPGA integration, the real
crossover study), and `transmon`/`duffing` physics (explicitly gated to M11 by
`CLAUDE.md` section 5) haven't been started. Full synthesis/timing numbers and any real
hardware numbers need Vivado/Vitis and eventually an Alveo U55C — **neither exists in
any environment this project has run in so far**; Verilator (already installed) covers
functional cosim only, not resource/timing closure. See `docs/validation.md` for the
gate-by-gate status.

**The paper is not submittable as-is.** Its own header says so, and that's still true —
most result tables remain `TBD`, and the one RTL gate that has run in full, V5, is
format-dependent (passes at Q1.15, fails at the documented default). Filling any TBD
cell from anything other than an executed run would be fabrication (see `CLAUDE.md`
section 10).

Compiling the PDF also needs `pdflatex`/`bibtex` and Springer's `svjour3.cls` (not
included here — licensed content; download it from the Springer author portal), neither
of which was available in the environment this was drafted in.

## Reproduce

    python3 -m venv venv
    venv/bin/pip install numpy scipy pyyaml pytest matplotlib
    venv/bin/pytest -v                                              # 8 pass, 1 xfail
    PYTHONPATH=. venv/bin/python bench/quantization/sweep_precision.py
    PYTHONPATH=. venv/bin/python cosim/run_v5_cosim.py               # needs verilator + g++

## To pick this up

1. Decide the format question flagged above: adopt Q1.15 as the committed default (it's
   the only one of the three named formats that clears V5 at this step count), or widen
   Q2.14's state storage, or accept the gap. Update `config/default.yaml` and
   `CLAUDE.md` section 7 together once decided — they currently agree with each other
   (both say Q2.14) but that shared default is the one that fails.
2. Build the RWA drive-term RTL (bidiagonal complex arithmetic, boundary levels n=0 and
   n=N-1 need care) to complete the actual M2 Trotter datapath.
3. Get access to Vivado/Vitis (and ideally an Alveo U55C, or at least xsim) for
   synthesis/timing and everything past M2.
4. Follow the build order in `CLAUDE.md` section 5 — it's gated for a reason.
5. Fold real numbers into `paper/main.tex` as each milestone actually produces them.
