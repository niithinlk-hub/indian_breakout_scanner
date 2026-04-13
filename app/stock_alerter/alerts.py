from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from app.stock_alerter.config import StockAlerterConfig


def format_telegram_message(signal: dict[str, Any], universe_name: str) -> str:
    """Format a Telegram alert message for a breakout signal."""

    return "\n".join(
        [
            "🚨 Bullish Breakout Alert",
            f"{signal.get('company_name', signal['symbol'])} ({signal['symbol']})",
            f"Universe: {universe_name}",
            f"Pattern: {signal['pattern_name']}",
            f"Breakout level: {signal.get('breakout_level')}",
            f"Current price: {signal.get('current_price')}",
            f"Volume ratio: {signal.get('volume_ratio')}",
            f"RSI: {signal.get('rsi')}",
            f"ADX: {signal.get('adx')}",
            f"Score: {signal.get('score')} | {signal.get('category')}",
            f"BOS: {signal.get('bos_status')}",
            f"FVG: {signal.get('fvg_status')}",
            f"Retest: {signal.get('retest_status')}",
            f"Stop / invalidation: {signal.get('invalidation_level')}",
            f"Timestamp: {signal.get('scan_timestamp', datetime.utcnow().isoformat())}",
        ],
    )


def send_telegram_alert(message: str, config: StockAlerterConfig) -> tuple[bool, str]:
    """Send a Telegram alert when bot credentials are configured."""

    if not config.telegram_bot_token or not config.telegram_chat_id:
        return False, "Telegram bot token or chat id is missing."

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": config.telegram_chat_id, "text": message},
            timeout=20,
        )
        response.raise_for_status()
    except Exception as exc:
        return False, str(exc)
    return True, "Sent"
