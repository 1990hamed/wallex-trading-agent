from decimal import Decimal

from wallex_trading_agent.wallex import WallexClient


def test_stop_limit_order_uses_wallex_stop_price_field(monkeypatch):
    client = WallexClient("test-key")
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(method=method, path=path, **kwargs)
        return {"success": True, "result": {"clientId": "stop-1"}}

    monkeypatch.setattr(client, "_request", fake_request)
    client.create_stop_limit_order(
        symbol="BTCTMN",
        side="SELL",
        stop_price=Decimal("3000000000"),
        price=Decimal("2990000000"),
        quantity=Decimal("0.01"),
    )

    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/account/orders"
    assert captured["json"]["type"] == "STOP_LIMIT"
    assert captured["json"]["stop_Price"] == "3000000000"
    assert captured["json"]["side"] == "SELL"


def test_idempotency_key_is_stable_and_distinguishes_intents():
    kwargs = {
        "symbol": "BTCTMN",
        "side": "BUY",
        "price": Decimal("3000000000"),
        "quantity": Decimal("0.01"),
    }
    first = WallexClient.idempotency_key(purpose="entry", **kwargs)
    second = WallexClient.idempotency_key(purpose="entry", **kwargs)
    different = WallexClient.idempotency_key(purpose="take-profit", **kwargs)

    assert first == second
    assert first != different
    assert first.startswith("agent-")


def test_account_order_management_endpoints(monkeypatch):
    client = WallexClient("test-key")
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path.endswith("openOrders"):
            return {"result": {"orders": [{"clientId": "x"}]}}
        return {"result": {"clientId": "x"}}

    monkeypatch.setattr(client, "_request", fake_request)
    assert client.open_orders("BTCTMN")[0]["clientId"] == "x"
    client.order_detail("x")
    client.cancel_order("x")
    assert [method for method, _, _ in calls] == ["GET", "GET", "DELETE"]

