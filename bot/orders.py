"""
Order placement logic — translates validated user input into Binance API calls
and formats the response for display.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceAPIError, BinanceNetworkError

logger = logging.getLogger("trading_bot.orders")


class OrderResult:
    """Structured container for an order response."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.symbol: str = raw.get("symbol", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.status: str = raw.get("status", "")
        self.orig_qty: str = raw.get("origQty", "0")
        self.executed_qty: str = raw.get("executedQty", "0")
        self.avg_price: str = raw.get("avgPrice", "0")
        self.price: str = raw.get("price", "0")
        self.stop_price: str = raw.get("stopPrice", "0")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.update_time: int = raw.get("updateTime", 0)

    def summary(self) -> str:
        """Return a human-readable summary of the order result."""
        lines = [
            "",
            "═" * 52,
            "  ORDER RESPONSE",
            "═" * 52,
            f"  Order ID      : {self.order_id}",
            f"  Symbol        : {self.symbol}",
            f"  Side          : {self.side}",
            f"  Type          : {self.order_type}",
            f"  Status        : {self.status}",
            f"  Orig Qty      : {self.orig_qty}",
            f"  Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and self.avg_price != "0":
            lines.append(f"  Avg Price     : {self.avg_price}")
        if self.price and self.price != "0":
            lines.append(f"  Limit Price   : {self.price}")
        if self.stop_price and self.stop_price != "0":
            lines.append(f"  Stop Price    : {self.stop_price}")
        if self.time_in_force:
            lines.append(f"  Time-in-Force : {self.time_in_force}")
        lines.append("═" * 52)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public order helpers
# ---------------------------------------------------------------------------


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> OrderResult:
    """
    Place a MARKET order.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.

    Returns:
        OrderResult with Binance's response.

    Raises:
        BinanceAPIError: On API-level failures.
        BinanceNetworkError: On connectivity issues.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": str(quantity),
    }
    logger.info(
        "MARKET order | symbol=%s | side=%s | qty=%s", symbol, side, quantity
    )
    raw = client.place_order(**params)
    result = OrderResult(raw)
    logger.info(
        "MARKET order placed | orderId=%s | status=%s | executedQty=%s | avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a LIMIT order.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.
        price: Limit price.
        time_in_force: 'GTC' (default), 'IOC', or 'FOK'.

    Returns:
        OrderResult with Binance's response.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": str(quantity),
        "price": str(price),
        "timeInForce": time_in_force,
    }
    logger.info(
        "LIMIT order | symbol=%s | side=%s | qty=%s | price=%s | tif=%s",
        symbol, side, quantity, price, time_in_force,
    )
    raw = client.place_order(**params)
    result = OrderResult(raw)
    logger.info(
        "LIMIT order placed | orderId=%s | status=%s | price=%s",
        result.order_id,
        result.status,
        result.price,
    )
    return result


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> OrderResult:
    """
    Place a STOP_MARKET order (bonus order type).

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.
        stop_price: The trigger price.

    Returns:
        OrderResult with Binance's response.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": str(quantity),
        "stopPrice": str(stop_price),
    }
    logger.info(
        "STOP_MARKET order | symbol=%s | side=%s | qty=%s | stopPrice=%s",
        symbol, side, quantity, stop_price,
    )
    raw = client.place_order(**params)
    result = OrderResult(raw)
    logger.info(
        "STOP_MARKET order placed | orderId=%s | status=%s | stopPrice=%s",
        result.order_id,
        result.status,
        result.stop_price,
    )
    return result


def dispatch_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Route to the correct order function based on order_type.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair.
        side: 'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity: Order quantity.
        price: Limit / stop price (required for LIMIT and STOP_MARKET).
        time_in_force: Time-in-force for LIMIT orders.

    Returns:
        OrderResult.

    Raises:
        ValueError: If order_type is unsupported.
    """
    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)
    elif order_type == "LIMIT":
        return place_limit_order(client, symbol, side, quantity, price, time_in_force)
    elif order_type == "STOP_MARKET":
        return place_stop_market_order(client, symbol, side, quantity, price)
    else:
        raise ValueError(f"Unsupported order type: {order_type}")
