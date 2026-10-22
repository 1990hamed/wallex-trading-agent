from __future__ import annotations

import hashlib
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

        candles = self.historical_candles(symbol, resolution, candle_count)
        return MarketSnapshot(
            symbol=symbol,
            best_bid=Decimal(str(bids[0]["price"])),
            best_ask=Decimal(str(asks[0]["price"])),
            candles=candles,
        )

    def historical_candles(self, symbol: str, resolution: str, candle_count: int) -> list[Candle]:
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
        return [
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

    def balances(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/balances").get("result", {}).get("balances", {})

    def open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {"symbol": symbol} if symbol else None
        result = self._request("GET", "/v1/account/openOrders", params=params).get("result", {})
        return result.get("orders", result if isinstance(result, list) else [])

    def order_detail(self, client_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/account/orders/{client_id}").get("result", {})

    def cancel_order(self, client_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/account/orders/{client_id}")

    def market_rules(self, symbol: str) -> dict[str, Any]:
        markets = self._request("GET", "/hector/web/v1/markets").get("result", {})
        items = markets.get("symbols", markets if isinstance(markets, list) else [])
        return next((item for item in items if item.get("symbol") == symbol), {})

    def create_limit_order(
        self, *, symbol: str, side: str, price: Decimal, quantity: Decimal,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        return self._create_order(
            symbol=symbol, side=side, order_type="LIMIT", price=price, quantity=quantity,
            client_id=client_id,
        )

    def create_stop_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        stop_price: Decimal,
        price: Decimal,
        quantity: Decimal,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Spot stop-limit order using Wallex's documented stop_Price field."""
        return self._create_order(
            symbol=symbol,
            side=side,
            order_type="STOP_LIMIT",
            price=price,
            quantity=quantity,
            stop_price=stop_price,
            client_id=client_id,
        )

    def _create_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        price: Decimal,
        quantity: Decimal,
        stop_price: Decimal | None = None,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        client_id = client_id or f"agent-{uuid.uuid4()}"
        body: dict[str, Any] = {
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "price": format(price, "f"),
            "quantity": format(quantity, "f"),
            "client_id": client_id,
        }
        if stop_price is not None:
            # Wallex's Spot API spells this field with a capital P.
            body["stop_Price"] = format(stop_price, "f")
        return self._request(
            "POST",
            "/v1/account/orders",
            json=body,
        )

    @staticmethod
    def idempotency_key(*, purpose: str, symbol: str, side: str, price: Decimal,
                        quantity: Decimal, stop_price: Decimal | None = None) -> str:
        """Return a stable Wallex client_id for an identical order intent."""
        raw = "|".join(
            [purpose, symbol, side, format(price, "f"), format(quantity, "f"),
             format(stop_price, "f") if stop_price is not None else ""]
        )
        return f"agent-{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
