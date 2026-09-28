#!/usr/bin/env python3
"""Script de validation manuelle, à lancer une fois via SSH avant de déployer
le bot en continu.

Fait un login + récupère le planning brut du prochain jour cible, sans rien
réserver. Sert à vérifier que les endpoints BasicFit dans basicfit_client.py
fonctionnent encore, et à voir le format exact des créneaux renvoyés (pour
ajuster find_slot_at_time si besoin).
"""
from __future__ import annotations

import json

from basicfit_client import BasicFitClient
from config import load_config
from scheduling import get_target_datetimes


def main() -> None:
    config = load_config()
    client = BasicFitClient(config.email, config.password)

    print("Connexion à BasicFit...")
    client.login()
    print(f"OK — club_id = {client.club_id}")

    target = get_target_datetimes(config.target_time, config.window_days)[0]
    print(f"Récupération du planning pour {target.date()} (cherche {config.target_time})...")
    slots = client.get_availability(target.date())
    print(json.dumps(slots, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
