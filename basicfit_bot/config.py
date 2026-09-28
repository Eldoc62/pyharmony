"""Chargement de la configuration depuis un fichier texte clé=valeur."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "credentials.txt"

REQUIRED_KEYS = {
    "BASICFIT_EMAIL",
    "BASICFIT_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
}


@dataclass
class Config:
    email: str
    password: str
    telegram_token: str
    telegram_chat_id: str
    target_time: dt.time
    scrape_interval_seconds: int
    window_days: int


def _parse_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}\n"
            f"Copie config.example.txt vers {path} et remplis les valeurs."
        )

    values = _parse_key_values(path)

    missing = REQUIRED_KEYS - values.keys()
    if missing:
        raise ValueError(f"Clés manquantes dans {path} : {', '.join(sorted(missing))}")

    hour_str, _, minute_str = values.get("TARGET_TIME", "05:30").partition(":")
    target_time = dt.time(int(hour_str), int(minute_str))

    return Config(
        email=values["BASICFIT_EMAIL"],
        password=values["BASICFIT_PASSWORD"],
        telegram_token=values["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=values["TELEGRAM_CHAT_ID"],
        target_time=target_time,
        scrape_interval_seconds=int(values.get("SCRAPE_INTERVAL_SECONDS", "30")),
        window_days=int(values.get("WINDOW_DAYS", "10")),
    )
