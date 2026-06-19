from house_price_tool.llm import FakeLLMClient, LLMClient


def test_fake_client_returns_scripted_and_records_calls():
    c = FakeLLMClient(["first", "second"])
    assert isinstance(c, LLMClient) or hasattr(c, "complete")
    assert c.complete("sys", "p1") == "first"
    assert c.complete("sys", "p2", temperature=0.0) == "second"
    assert len(c.calls) == 2 and c.calls[0]["prompt"] == "p1"


def test_fake_client_single_string_repeats():
    c = FakeLLMClient("only")
    assert c.complete("s", "a") == "only" and c.complete("s", "b") == "only"
