import os
import pytest
from backpop.files import parse_inifile

TEST_INI = os.path.join(os.path.dirname(__file__), "data", "test.ini")


@pytest.fixture(scope="module")
def parsed():
    return parse_inifile(TEST_INI)


def test_config_integer_types(parsed):
    config = parsed[0]
    assert isinstance(config["n_threads"], int)
    assert isinstance(config["n_eff"], int)
    assert isinstance(config["n_live"], int)


def test_config_bool_types(parsed):
    config = parsed[0]
    assert isinstance(config["verbose"], bool)
    assert isinstance(config["resume"], bool)
    assert isinstance(config["use_bcm"], bool)


def test_config_values(parsed):
    config = parsed[0]
    assert config["n_threads"] == 1
    assert config["n_eff"] == 50
    assert config["n_live"] == 50
    assert config["verbose"] is False
    assert config["use_bcm"] is False
    assert config["phase_condition"] == "kstar_1 == 1 & kstar_2 == 1"
    assert config["n_bpp_rows"] == 35  # default when blank


def test_obs_parsed(parsed):
    obs = parsed[3]
    assert obs["name"] == ["m1", "m2", "tb", "e"]
    assert obs["out_name"] == ["mass_1", "mass_2", "porb", "ecc"]
    assert obs["mean"] == pytest.approx([10.0, 5.0, 100.0, 0.2])
    assert obs["sigma"] == pytest.approx([1.0, 0.5, 10.0, 0.02])
    assert obs["log"] == [False, False, False, False]


def test_var_parsed(parsed):
    var = parsed[4]
    assert var["name"] == ["m1", "m2", "tb", "e"]
    assert var["min"] == pytest.approx([5.0, 2.0, 5.0, 0.0])
    assert var["max"] == pytest.approx([20.0, 8.0, 1000.0, 0.9])
    assert var["log"] == [False, False, False, False]


def test_fixed_parsed(parsed):
    fixed = parsed[5]
    assert fixed["metallicity"] == pytest.approx(0.001)
    assert fixed["tphys"] == pytest.approx(10.0)


def test_flags_numeric(parsed):
    flags = parsed[1]
    assert flags["windflag"] == 3
    assert flags["kickflag"] == 1
    assert flags["randomseed"] == 42


def test_flags_list(parsed):
    flags = parsed[1]
    assert flags["alpha1"] == [1.0, 1.0]
    assert len(flags["fprimc_array"]) == 16
    assert len(flags["qcrit_array"]) == 16


def test_sse_dict(parsed):
    SSEDict = parsed[2]
    assert SSEDict["stellar_engine"] == "sse"


def test_invalid_bpp_column_raises(tmp_path):
    ini_text = open(TEST_INI).read().replace(
        "bpp_columns =\n", 'bpp_columns = ["not_a_real_column"]\n'
    )
    bad_ini = tmp_path / "bad.ini"
    bad_ini.write_text(ini_text)
    with pytest.raises(ValueError, match="Invalid column name"):
        parse_inifile(str(bad_ini))
