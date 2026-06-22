import numpy as np
import pandas as pd
import pytest
from backpop.phase import (
    select_phase,
    add_vsys_from_kicks,
    _parse_condition,
    _parse_conditions,
    Condition,
    ConditionGroup,
)


@pytest.fixture
def bpp():
    """Minimal BPP-like DataFrame covering several evolutionary states."""
    return pd.DataFrame(
        {
            "kstar_1": [1, 1, 2, 14, 14],
            "kstar_2": [1, 1, 1, 13, 13],
            "mass_1": [10.0, 9.9, 8.5, 8.0, 8.0],
            "mass_2": [5.0, 5.0, 5.0, 1.4, 1.4],
            "sep": [100.0, 90.0, 80.0, 60.0, -1.0],
            "ecc": [0.2, 0.2, 0.1, 0.0, 0.0],
            "evol_type": [1, 2, 3, 15, 3],
            "porb": [10.0, 9.5, 9.0, 8.0, 0.0],
        }
    )


# --- select_phase ---

def test_simple_equality(bpp):
    result = select_phase(bpp, "kstar_1 == 1")
    assert len(result) == 2
    assert (result["kstar_1"] == 1).all()


def test_and_condition(bpp):
    result = select_phase(bpp, "kstar_1 == 1 & kstar_2 == 1")
    assert len(result) == 2


def test_or_condition(bpp):
    result = select_phase(bpp, "kstar_1 == 14 | kstar_1 == 2")
    assert len(result) == 3


def test_in_condition(bpp):
    result = select_phase(bpp, "kstar_1 in [1, 2]")
    assert len(result) == 3


def test_not_condition(bpp):
    result = select_phase(bpp, "~(kstar_1 == 1)")
    assert len(result) == 3
    assert (result["kstar_1"] != 1).all()


def test_nested_condition(bpp):
    result = select_phase(bpp, "(kstar_1 == 14 & kstar_2 == 13 & sep > 0)")
    assert len(result) == 1
    assert result["sep"].iloc[0] > 0


def test_no_match_returns_empty(bpp):
    result = select_phase(bpp, "kstar_1 == 99")
    assert len(result) == 0


def test_default_phase_no_match(bpp):
    # our bpp has no BBH merger (both kstar==14 + evol_type==3)
    result = select_phase(bpp, "BBH_merger")
    assert len(result) == 0


def test_gt_condition(bpp):
    result = select_phase(bpp, "sep > 0")
    assert (result["sep"] > 0).all()


def test_not_equal(bpp):
    result = select_phase(bpp, "sep != 100.0")
    assert (100.0 not in result["sep"].values)


# --- _parse_condition / _parse_conditions errors ---

def test_invalid_op_raises():
    with pytest.raises(ValueError):
        _parse_condition("mass_1 ≈ 5")


def test_too_few_parts_raises():
    with pytest.raises(ValueError):
        _parse_condition("mass_1 ==")


def test_mismatched_parens_raises():
    with pytest.raises(ValueError):
        _parse_conditions("(kstar_1 == 1 & kstar_2 == 1")


# --- add_vsys_from_kicks ---

def test_no_sn_kicks_zero(bpp):
    kick_info = pd.DataFrame(
        {"star": [0, 0], "vsys_1_total": [0.0, 0.0], "vsys_2_total": [0.0, 0.0]}
    )
    result = add_vsys_from_kicks(bpp, kick_info)
    assert (result["vsys_1_total"] == 0.0).all()
    assert (result["vsys_2_total"] == 0.0).all()


def test_sn_kick_propagates(bpp):
    kick_info = pd.DataFrame(
        {
            "star": [1, 2],
            "vsys_1_total": [50.0, 0.0],
            "vsys_2_total": [0.0, 30.0],
        }
    )
    result = add_vsys_from_kicks(bpp, kick_info)
    # rows after evol_type==15 (SN1) should carry vsys_1_total=50
    sn1_idx = bpp[bpp["evol_type"] == 15].index[0]
    post_sn1 = result.loc[result.index >= sn1_idx]
    assert (post_sn1["vsys_1_total"] == 50.0).all()
