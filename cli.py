#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples:
  python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.001
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.001 --price 95000
  python cli.py place --symbol BTCUSDT --side BUY  --type STOP_MARKET --quantity 0.001 --price 85000
  python cli.py account
  python cli.py price --symbol BTCUSDT
"""

import argparse
import json
import os
import sys
from decimal import Decimal

# ── allow running as `python cli.py` from repo root ──────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceAPIError, BinanceNetworkError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import dispatch_order
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

# ── colour helpers (degrade gracefully on Windows) ────────────────────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    GREEN  = Fore.GREEN
    RED    = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN   = Fore.CYAN
    RESET  = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = RESET = ""


def _banner():
    print(f"{CYAN}")
    print("╔══════════════════════════════════════════════════╗")
    print("║    Binance Futures Testnet — Trading Bot 🤖       ║")
    print("╚══════════════════════════════════════════════════╝")
    print(RESET)


def _ok(msg: str):
    print(f"{GREEN}✔  {msg}{RESET}")


def _err(msg: str):
    print(f"{RED}✘  {msg}{RESET}", file=sys.stderr)


def _warn(msg: str):
    print(f"{YELLOW}⚠  {msg}{RESET}")


def _get_client(args: argparse.Namespace) -> BinanceClient:
    """Build BinanceClient, preferring CLI flags then env vars."""
    api_key    = getattr(args, "api_key", None)    or os.getenv("BINANCE_API_KEY", "")
    api_secret = getattr(args, "api_secret", None) or os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        _err(
            "API credentials not found.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables, "
            "or pass --api-key / --api-secret."
        )
        sys.exit(1)

    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ── sub-command handlers ──────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace, logger):
    """Handle the 'place' sub-command."""
    # ── validate inputs ───────────────────────────────────────────────────────
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.type)
        quantity   = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
    except ValueError as exc:
        _err(f"Validation error: {exc}")
        logger.warning("Validation failed: %s", exc)
        sys.exit(1)

    tif = (args.time_in_force or "GTC").upper()

    # ── print request summary ─────────────────────────────────────────────────
    print()
    print("─" * 52)
    print("  ORDER REQUEST SUMMARY")
    print("─" * 52)
    print(f"  Symbol        : {symbol}")
    print(f"  Side          : {side}")
    print(f"  Type          : {order_type}")
    print(f"  Quantity      : {quantity}")
    if price is not None:
        label = "Stop Price" if order_type == "STOP_MARKET" else "Limit Price"
        print(f"  {label:<13} : {price}")
    if order_type == "LIMIT":
        print(f"  Time-in-Force : {tif}")
    print("─" * 52)
    print()

    logger.info(
        "Order request | symbol=%s | side=%s | type=%s | qty=%s | price=%s",
        symbol, side, order_type, quantity, price,
    )

    # ── send order ────────────────────────────────────────────────────────────
    client = _get_client(args)
    try:
        result = dispatch_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            time_in_force=tif,
        )
    except BinanceAPIError as exc:
        _err(f"API error [{exc.code}]: {exc.message}")
        logger.error("API error | code=%s | msg=%s", exc.code, exc.message)
        sys.exit(1)
    except BinanceNetworkError as exc:
        _err(f"Network error: {exc}")
        logger.error("Network error: %s", exc)
        sys.exit(1)

    print(result.summary())
    _ok(f"Order placed successfully! (orderId={result.order_id})")
    logger.info("Order SUCCESS | orderId=%s | status=%s", result.order_id, result.status)


def cmd_account(args: argparse.Namespace, logger):
    """Handle the 'account' sub-command."""
    client = _get_client(args)
    try:
        info = client.get_account_info()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        _err(str(exc))
        logger.error("account fetch failed: %s", exc)
        sys.exit(1)

    balances = {b["asset"]: b for b in info.get("balances", [])}
    usdt = balances.get("USDT", {})
    btc  = balances.get("BTC", {})
    print()
    print("-" * 52)
    print("  ACCOUNT SUMMARY (Spot Testnet)")
    print("-" * 52)
    if usdt:
        print(f"  USDT Free       : {usdt.get('free', 'N/A')}")
        print(f"  USDT Locked     : {usdt.get('locked', 'N/A')}")
    if btc:
        print(f"  BTC Free        : {btc.get('free', 'N/A')}")
        print(f"  BTC Locked      : {btc.get('locked', 'N/A')}")
    print(f"  Can Trade       : {info.get('canTrade', 'N/A')}")
    print("-" * 52)
    logger.info("Account info fetched successfully.")


def cmd_price(args: argparse.Namespace, logger):
    """Handle the 'price' sub-command."""
    try:
        symbol = validate_symbol(args.symbol)
    except ValueError as exc:
        _err(str(exc))
        sys.exit(1)

    client = _get_client(args)
    try:
        data = client.get_symbol_price(symbol)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        _err(str(exc))
        logger.error("price fetch failed: %s", exc)
        sys.exit(1)

    print()
    print(f"  {symbol} Price : {data.get('price', 'N/A')} USDT")
    logger.info("Price fetched | symbol=%s | price=%s", symbol, data.get("price"))


# ── argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    # shared credential flags
    cred_parent = argparse.ArgumentParser(add_help=False)
    cred_parent.add_argument("--api-key",    dest="api_key",    help="Binance API key (overrides env var)")
    cred_parent.add_argument("--api-secret", dest="api_secret", help="Binance API secret (overrides env var)")
    cred_parent.add_argument("--log-level",  default="INFO",    help="Logging level (default: INFO)")

    root = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Market buy
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit sell
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000

  # Stop-market buy (bonus)
  python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --price 85000

  # Check account
  python cli.py account

  # Get mark price
  python cli.py price --symbol BTCUSDT
        """,
    )

    sub = root.add_subparsers(dest="command", required=True)

    # ── place ──────────────────────────────────────────────────────────────────
    place_p = sub.add_parser(
        "place",
        help="Place a new futures order",
        parents=[cred_parent],
    )
    place_p.add_argument("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument("--side",     required=True, choices=["BUY", "SELL"], help="Order side")
    place_p.add_argument("--type",     required=True, choices=["MARKET", "LIMIT", "STOP_MARKET"],
                         dest="type",  help="Order type")
    place_p.add_argument("--quantity", required=True, help="Order quantity")
    place_p.add_argument("--price",    default=None,  help="Limit / stop price (required for LIMIT & STOP_MARKET)")
    place_p.add_argument("--time-in-force", default="GTC",
                         choices=["GTC", "IOC", "FOK"],
                         dest="time_in_force",
                         help="Time-in-force for LIMIT orders (default: GTC)")

    # ── account ────────────────────────────────────────────────────────────────
    sub.add_parser("account", help="Show account balance summary", parents=[cred_parent])

    # ── price ─────────────────────────────────────────────────────────────────
    price_p = sub.add_parser("price", help="Get mark price for a symbol", parents=[cred_parent])
    price_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")

    return root


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    _banner()
    parser = build_parser()
    args   = parser.parse_args()
    logger = setup_logging(getattr(args, "log_level", "INFO"))

    dispatch = {
        "place":   cmd_place,
        "account": cmd_account,
        "price":   cmd_price,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args, logger)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
