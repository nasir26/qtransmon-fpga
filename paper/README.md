# Manuscript

Target: The Journal of Supercomputing (Springer).

Compile:

    pdflatex main && bibtex main && pdflatex main && pdflatex main

`svjour3.cls` is not redistributed here. Download it from the Springer author portal
and place it in this directory.

**This manuscript is not submittable in its current state.** The methodology sections
are complete. In the results section, V1-V4 (Table `validation`) and the fixed-point
infidelity column (Table `fixedpoint`) are filled from executed runs (M0, M1); every
other cell — resource/timing numbers, V5 onward, the crossover table — is still `TBD`
because it depends on the RTL/hardware toolchain (Vivado, Alveo U55C access), which
this project has not yet had access to. Submitting before those cells are filled from
executed runs would constitute fabrication.
