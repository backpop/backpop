"""
Tests for BackPop initialization and likelihood.

Tiers:
  - init / early-exit tests: zero COSMIC calls, < 1 s
  - valid likelihood test: one COSMIC binary evolution, ~ 1-5 s
"""
import numpy as np
import pytest
from backpop.main import KICK_SHAPE, EXTRA_PHASE_TABLE_COLS

# params that satisfy all constraints in the test ini and will still be on the
# main sequence after 10 Myr (10 Msun MS lifetime ~ 35 Myr, 5 Msun ~ 200 Myr)
VALID_PARAMS = {"m1": 10.0, "m2": 5.0, "tb": 100.0, "e": 0.2}


# --- initialization ---

def test_prior_has_correct_parameters(bp):
    assert set(bp.prior.keys) == {"m1", "m2", "tb", "e"}


def test_rv_mean_matches_obs(bp):
    np.testing.assert_allclose(bp.rv.mean, [10.0, 5.0, 100.0, 0.2])


def test_rv_cov_diagonal(bp):
    cov = bp.rv.cov
    off_diag = cov - np.diag(np.diag(cov))
    assert np.allclose(off_diag, 0.0)


def test_config_values_set(bp):
    assert bp.config["n_threads"] == 1
    assert bp.config["n_live"] == 50
    assert bp.config["verbose"] is False


# --- likelihood: early-exit paths (no COSMIC call) ---

def test_m1_lt_m2_returns_neg_inf(bp):
    x = {"m1": 3.0, "m2": 5.0, "tb": 100.0, "e": 0.2}
    ll, blob = bp.likelihood(x)
    assert ll == -np.inf
    assert np.all(np.isnan(blob))


def test_m1_out_of_bounds_returns_neg_inf(bp):
    x = {"m1": 100.0, "m2": 5.0, "tb": 100.0, "e": 0.2}
    ll, blob = bp.likelihood(x)
    assert ll == -np.inf
    assert np.all(np.isnan(blob))


def test_m2_out_of_bounds_returns_neg_inf(bp):
    x = {"m1": 10.0, "m2": 50.0, "tb": 100.0, "e": 0.2}
    ll, blob = bp.likelihood(x)
    assert ll == -np.inf


# --- likelihood: full evaluation (one COSMIC call, ~ 1-5 s) ---

def test_valid_likelihood_is_finite(bp):
    ll, blob = bp.likelihood(VALID_PARAMS.copy())
    assert np.isfinite(ll)


def test_valid_likelihood_blob_shape(bp):
    ll, blob = bp.likelihood(VALID_PARAMS.copy())
    expected_len = (
        bp.config["n_bpp_rows"] * len(bp.config["bpp_columns"])
        + int(np.prod(KICK_SHAPE))
        + len(bp.config["bcm_columns"]) + len(EXTRA_PHASE_TABLE_COLS)
    )
    assert blob.shape == (expected_len,)


def test_valid_likelihood_blob_not_all_nan(bp):
    ll, blob = bp.likelihood(VALID_PARAMS.copy())
    assert not np.all(np.isnan(blob))
