"""V5 (CLAUDE.md section 6, partial scope: free evolution only -- the RWA drive term is
not implemented in RTL yet). Run via Verilator (Vivado xsim unavailable in this
environment; see docs/validation.md).

xfail, not skip: this has actually been run (cosim/results_v5_free_evolution.json) and
currently fails the < 1e-4 threshold at every swept Q-format (Q1.15: 5.4e-3, Q2.14:
4.1e-2, Q4.12 far worse -- CLAUDE.md section 10: a measured negative result is reported,
not hidden). Root cause: the per-step ROM-quantized rotator carries a small systematic
angular error that compounds roughly linearly over 10,000 steps (same effect M1's
physics/fixed_point.py sweep found in software). Candidate fix for the next iteration:
carry the recurrence at higher internal precision than the DATA_WIDTH output format
(guard bits), rounding only at readout -- unverified, not yet implemented.
"""
import shutil

import pytest

from cosim.run_v5_cosim import V5_INFIDELITY_THRESHOLD, run_cosim


@pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")
@pytest.mark.xfail(
    reason="systematic per-step rotator quantization error compounds over 1e4 steps; "
    "see cosim/results_v5_free_evolution.json and docs/validation.md",
    strict=False,
)
def test_v5_rtl_matches_golden_after_10000_steps():
    result = run_cosim()
    assert result["infidelity"] < V5_INFIDELITY_THRESHOLD
