"""Calcule les prochains créneaux à surveiller sur les jours cibles."""
from __future__ import annotations

import datetime as dt

# datetime.weekday(): lundi=0, mardi=1, mercredi=2, jeudi=3, vendredi=4, samedi=5, dimanche=6
TARGET_WEEKDAYS = {0, 1, 3, 4}


def get_target_datetimes(
    target_time: dt.time,
    window_days: int = 10,
    now: dt.datetime | None = None,
) -> list[dt.datetime]:
    """Retourne les prochains lundi/mardi/jeudi/vendredi à target_time, triés du plus proche au plus loin.

    Si aujourd'hui est un jour cible mais que target_time est déjà passé,
    ce jour est ignoré. Si aujourd'hui n'est pas un jour cible (mercredi,
    samedi, dimanche), on passe naturellement au prochain jour cible.
    """
    now = now or dt.datetime.now()
    today = now.date()

    results = []
    for offset in range(window_days):
        day = today + dt.timedelta(days=offset)
        if day.weekday() not in TARGET_WEEKDAYS:
            continue
        candidate = dt.datetime.combine(day, target_time)
        if candidate <= now:
            continue
        results.append(candidate)
    return results
