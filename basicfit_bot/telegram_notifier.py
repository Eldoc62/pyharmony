"""Envoi de notifications via un bot Telegram."""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger("basicfit_bot")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(token: str, chat_id: str, text: str) -> bool:
    """Envoie un message Telegram. Retourne False en cas d'échec (jamais d'exception)."""
    try:
        response = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Échec de l'envoi de la notification Telegram")
        return False
