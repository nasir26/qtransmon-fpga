# Manuscript

Target: The Journal of Supercomputing (Springer).

Compile:

    pdflatex main && bibtex main && pdflatex main && pdflatex main

`svjour3.cls` is not redistributed here. Download it from the Springer author portal
and place it in this directory.

**This manuscript is not submittable in its current state.** The methodology sections
are complete. In the results section, V1-V4, V5 (Table `validation`, reduced scope —
free evolution only, PASS at Q1.15 / FAIL at the Q2.14 default — see footnote in the
table and `docs/validation.md`), and the fixed-point infidelity column (Table
`fixedpoint`) are filled from executed runs (M0, M1, M2-partial); every other cell —
resource/timing numbers, the full V5 (with the drive term), V6 onward, the crossover
table — is still `TBD` because it depends on the RTL/hardware toolchain (Vivado, Alveo
U55C access), which this project has not yet had access to. Submitting before those
cells are filled from executed runs would constitute fabrication.
