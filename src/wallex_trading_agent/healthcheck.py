"""Read-only connectivity checks for deployment and pre-live verification."""

from wallex_trading_agent.config import Settings
from wallex_trading_agent.wallex import WallexClient


def main() -> None:
    """Check Wallex read access without creating or changing an order."""
    settings = Settings()
    api_key = settings.wallex_api_key.get_secret_value() if settings.wallex_api_key else None
    client = WallexClient(api_key)
    snapshot = client.market_snapshot(
        settings.symbol, settings.candle_resolution, settings.candle_count
    )
    balances = client.balances()
    open_orders = client.open_orders(settings.symbol)
    rules = client.market_rules(settings.symbol)
    print("Wallex health check: OK")
    print(f"Symbol: {settings.symbol}")
    print(f"Best bid/ask: {snapshot.best_bid}/{snapshot.best_ask}")
    print(f"Market rules found: {bool(rules)}")
    print(f"Balance assets visible: {len(balances)}")
    print(f"Open orders: {len(open_orders)}")

