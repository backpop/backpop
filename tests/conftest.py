import os
import pytest
from backpop import BackPop

TEST_INI = os.path.join(os.path.dirname(__file__), "data", "test.ini")


@pytest.fixture(scope="module")
def bp():
    return BackPop(config_file=TEST_INI)
