"""
Input validation helpers for CLI arguments.
All functions raise ValueError with a clear message on invalid input.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """
    Ensure the symbol is a non-empty uppercase alphanumeric string.

    Args:
        symbol: Trading pair, e.g. 'BTCUSDT'.

    Returns:
        Uppercased symbol string.

    Raises:
        ValueError: If the symbol is invalid.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Use alphanumeric characters only (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Validate the order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Uppercased side string.

    Raises:
        ValueError: If the side is not BUY or SELL.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate the order type.

    Args:
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET' (case-insensitive).

    Returns:
        Uppercased order type string.

    Raises:
        ValueError: If the order type is unsupported.
    """
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str) -> Decimal:
    """
    Parse and validate order quantity.

    Args:
        quantity: String representation of quantity.

    Returns:
        Positive Decimal quantity.

    Raises:
        ValueError: If quantity is not a positive number.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Parse and validate price, enforcing that LIMIT orders require a price.

    Args:
        price: String representation of price, or None.
        order_type: Validated order type string.

    Returns:
        Positive Decimal price, or None for MARKET orders.

    Raises:
        ValueError: If price is required but missing, or invalid.
    """
    if order_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders (--price <value>).")
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be greater than 0, got {p}.")
        return p

    if order_type == "STOP_MARKET":
        if price is None:
            raise ValueError(
                "Stop price is required for STOP_MARKET orders (--price <value>)."
            )
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Stop price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Stop price must be greater than 0, got {p}.")
        return p

    # MARKET order — price not needed
    if price is not None:
        # Warn but don't fail — just ignore it
        pass
    return None
