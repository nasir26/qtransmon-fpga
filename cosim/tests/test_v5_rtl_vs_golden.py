"""V5 (CLAUDE.md section 6, partial scope: free evolution only -- the RWA drive term is
not implemented in RTL yet). Run via Verilator (Vivado xsim unavailable in this
environment; see docs/validation.md). Log: cosim/results_v5_free_evolution.json.

RTL-verified result: of the three formats CLAUDE.md section 7 names, only Q1.15 clears
the < 1e-4 gate at N=32/1e4 steps (6.3e-6); Q2.14 -- the config default -- and Q4.12 do
not (3.6e-4, 2.1e-2). Root cause: the per-step ROM-quantized rotator carries a small
systematic angular error that compounds close to linearly over 10,000 steps; the ROM was
since widened to 32-bit internal precision (rtl/rom/gen_roms.py, ROM_DATA_WIDTH), which
fixes the ROM's own contribution, but Q2.14/Q4.12 still fail because their *state*
storage width alone is too coarse at this step count, independent of ROM precision.
"""
import shutil

import pytest

from cosim.run_v5_cosim import V5_INFIDELITY_THRESHOLD, run_cosim

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")


def test_v5_passes_at_q1_15():
    result = run_cosim(format_name="Q1.15")
    assert result["infidelity"] < V5_INFIDELITY_THRESHOLD


@pytest.mark.xfail(
    reason="Q2.14 (CLAUDE.md section 7's stated default) fails V5 at this step count -- "
    "state width itself is the limit, not ROM precision. See docs/validation.md for the "
    "recommendation to reconsider the default in favor of Q1.15.",
    strict=False,
)
def test_v5_fails_at_config_default_q2_14():
    result = run_cosim(format_name="Q2.14")
    assert result["infidelity"] < V5_INFIDELITY_THRESHOLD
