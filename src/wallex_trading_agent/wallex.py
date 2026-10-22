from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

import httpx

from wallex_trading_agent.models import Candle, MarketSnapshot


class WallexAPIError(RuntimeError):
    pass


class WallexClient:
    """Small REST client kept separate from the agent so orders stay auditable."""

    base_url = "https://api.wallex.ir"

    def __init__(self, api_key: str | None = None) -> None:
        self._headers = {"x-api-key": api_key} if api_key else {}

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, headers=self._headers, timeout=15.0) as client:
            response = client.request(method, path, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is False:
            raise WallexAPIError(payload.get("message", "Wallex rejected the request"))
        return payload

    def market_snapshot(self, symbol: str, resolution: str, candle_count: int) -> MarketSnapshot:
        depth = self._request("GET", "/v1/depth", params={"symbol": symbol})["result"]
        bids, asks = depth.get("bid", []), depth.get("ask", [])
        if not bids or not asks:
            raise WallexAPIError(f"No bid/ask available for {symbol}")

        now = int(time.time())
        history = self._request(
            "GET",
            "/v1/udf/history",
            params={
                "symbol": symbol,
                "resolution": resolution,
                "from": now - (candle_count * 60 * int(resolution)),
                "to": now,
            },
        )
        if history.get("s") != "ok":
            raise WallexAPIError(
                f"Candle history unavailable: {history.get('errmsg', 'unknown error')}"
            )
        candles = [
            Candle(
                timestamp=int(timestamp),
                open=Decimal(str(open_)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal(str(volume)),
            )
            for timestamp, open_, high, low, close, volume in zip(
                history["t"],
                history["o"],
                history["h"],
                history["l"],
                history["c"],
                history["v"],
                strict=True,
            )
        ]
        return MarketSnapshot(
            symbol=symbol,
            best_bid=Decimal(str(bids[0]["price"])),
            best_ask=Decimal(str(asks[0]["price"])),
            candles=candles,
        )

    def balances(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/balances").get("result", {}).get("balances", {})

    def create_limit_order(
        self, *, symbol: str, side: str, price: Decimal, quantity: Decimal
    ) -> dict[str, Any]:
        client_id = f"agent-{uuid.uuid4()}"
        return self._request(
            "POST",
            "/v1/account/orders",
            json={
                "symbol": symbol,
                "type": "LIMIT",
                "side": side,
                "price": format(price, "f"),
                "quantity": format(quantity, "f"),
                "client_id": client_id,
            },
        )
