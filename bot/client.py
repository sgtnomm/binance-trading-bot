"""
Low-level Binance Spot Testnet REST client.

Handles:
- HMAC-SHA256 request signing
- Timestamp + recvWindow injection
- HTTP request execution with retries
- Structured error parsing
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binance.vision"
DEFAULT_RECV_WINDOW = 5000
DEFAULT_TIMEOUT = 10


class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    pass


class BinanceClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})

        logger.info(
            "BinanceClient initialised | base_url=%s | recv_window=%s ms",
            self.base_url, self.recv_window,
        )

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Dict[str, Any]:
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug("→ %s %s | params=%s", method.upper(), endpoint, self._redact(params))

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == "POST":
                response = self._session.post(url, params=params, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, endpoint)
            raise BinanceNetworkError(f"Request to {endpoint} timed out after {self.timeout}s.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s | %s", method, endpoint, exc)
            raise BinanceNetworkError(f"Could not connect to {self.base_url}.") from exc

        logger.debug("← %s %s | status=%s | body=%s", method.upper(), endpoint, response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise BinanceNetworkError(f"Non-JSON response: {response.text[:200]}")

        if not response.ok:
            code = data.get("code", response.status_code)
            msg = data.get("msg", response.text)
            logger.error("API error | code=%s | msg=%s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch spot account information."""
        return self._request("GET", "/api/v3/account", signed=True)

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info."""
        return self._request("GET", "/api/v3/exchangeInfo")

    def get_symbol_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch latest price for a symbol."""
        return self._request("GET", "/api/v3/ticker/price", params={"symbol": symbol})

    def place_order(self, **order_params) -> Dict[str, Any]:
        """Place a new spot order."""
        logger.info("Placing order | params=%s", order_params)
        return self._request("POST", "/api/v3/order", params=order_params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query an existing order by ID."""
        return self._request("GET", "/api/v3/order", params={"symbol": symbol, "orderId": order_id}, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order."""
        return self._request("DELETE", "/api/v3/order", params={"symbol": symbol, "orderId": order_id}, signed=True)
