#!/usr/bin/env python3
"""Bot de réservation automatique BasicFit.

Cherche en continu un créneau à l'heure cible (par défaut 5h30) sur les
jours cibles (lundi, mardi, jeudi, vendredi), réserve dès qu'un créneau est
disponible, envoie une notification Telegram, puis s'arrête.

Toutes les erreurs sont logguées et le bot continue de réessayer
indéfiniment tant qu'aucune réservation n'a abouti.
"""
from __future__ import annotations

import random
import sys
import time

from basicfit_client import BasicFitAuthError, BasicFitClient, find_slot_at_time
from config import load_config
from logger_setup import setup_logging
from scheduling import get_target_datetimes
from telegram_notifier import send_message

logger = setup_logging()


def run() -> None:
    config = load_config()
    client = BasicFitClient(config.email, config.password)

    while True:
        try:
            if client.club_id is None:
                client.login()

            targets = get_target_datetimes(config.target_time, config.window_days)
            for target_dt in targets:
                slots = client.get_availability(target_dt.date())
                slot = find_slot_at_time(slots, config.target_time)
                if slot is not None:
                    logger.info("Créneau disponible le %s, réservation en cours...", target_dt)
                    client.book(slot)

                    message = (
                        "Réservation BasicFit confirmée : "
                        f"{target_dt.strftime('%A %d/%m/%Y')} à "
                        f"{config.target_time.strftime('%H:%M')}."
                    )
                    logger.info(message)
                    send_message(config.telegram_token, config.telegram_chat_id, message)
                    return

        except BasicFitAuthError as exc:
            logger.warning("Session invalide (%s), ré-authentification au prochain cycle.", exc)
            client.club_id = None
        except Exception:
            logger.exception("Erreur inattendue pendant le cycle de scraping, on continue.")

        time.sleep(config.scrape_interval_seconds + random.uniform(0, 3))


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Arrêt manuel du bot.")
        sys.exit(0)
