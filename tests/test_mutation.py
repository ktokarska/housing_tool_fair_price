import pytest
from house_price_tool.eval.mutation import mutation_check


@pytest.mark.contract
def test_all_mutations_are_caught():
    results = mutation_check()
    assert results == {"fabricated_number": True, "directional_on_low": True,
                       "inflated_estimate": True}
