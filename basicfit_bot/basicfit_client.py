"""Client HTTP pour l'API membre de BasicFit.

ATTENTION — ENDPOINTS NON VÉRIFIÉS :
Les URLs ci-dessous sont reconstruites à partir d'un projet open-source de
2021 (domaine my.basic-fit.com). L'interface actuelle utilise désormais
member.basic-fit.com/booking, donc ces chemins ont probablement changé.

Avant de déployer le bot en continu, lance test_connection.py pour vérifier
que login()/get_availability() fonctionnent, et ajuste les constantes et le
format de réponse dans ce fichier si besoin (capture réseau depuis les
DevTools du navigateur sur member.basic-fit.com/booking/fr-FR).
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import requests

logger = logging.getLogger("basicfit_bot")

LOGIN_URL = "https://bfa-login.basic-fit.com/login"
SSO_URL = "https://member.basic-fit.com/sso"
MEMBER_INFO_URL = "https://member.basic-fit.com/member/get-member"
AVAILABILITY_URL = "https://member.basic-fit.com/door-policy/get-availability"
BOOK_URL = "https://member.basic-fit.com/door-policy/book-door-policy"

USER_AGENT = "Basic Fit App/1.3.1.0 (iOS)"
REQUEST_TIMEOUT = 15


class BasicFitAuthError(Exception):
    """Levée quand le login échoue ou que la session a expiré."""


class BasicFitClient:
    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self.club_id: str | None = None

    def login(self) -> None:
        """Authentifie et récupère le club favori du membre."""
        response = self._session.post(
            LOGIN_URL,
            json={"email": self._email, "password": self._password},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise BasicFitAuthError(f"Login refusé : HTTP {response.status_code}")

        token = response.json().get("accessToken")
        if not token:
            raise BasicFitAuthError("Réponse de login sans accessToken")

        sso_response = self._session.post(
            SSO_URL,
            json={},
            headers={"Authorization": f"bearer {token}"},
            timeout=REQUEST_TIMEOUT,
        )
        if sso_response.status_code != 200:
            raise BasicFitAuthError(f"Échange SSO refusé : HTTP {sso_response.status_code}")

        member = self._get_member_info()
        self.club_id = member.get("favorite_club") or member.get("favoriteClub")
        if not self.club_id:
            raise BasicFitAuthError(
                "Impossible de déterminer le club favori depuis le profil membre "
                "(vérifie que Petite Synthe est bien ton club favori dans l'app)"
            )
        logger.info("Connexion réussie, club_id=%s", self.club_id)

    def _get_member_info(self) -> dict[str, Any]:
        response = self._session.get(MEMBER_INFO_URL, timeout=REQUEST_TIMEOUT)
        if response.status_code == 401:
            raise BasicFitAuthError("Session expirée pendant get-member")
        response.raise_for_status()
        return response.json()

    def get_availability(self, date: dt.date) -> list[dict[str, Any]]:
        """Retourne la liste des créneaux (bruts) pour une date donnée."""
        response = self._session.post(
            AVAILABILITY_URL,
            json={"clubId": self.club_id, "dateTime": date.isoformat()},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 401:
            raise BasicFitAuthError("Session expirée pendant get-availability")
        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict):
            return data.get("data", [])
        return data

    def book(self, slot: dict[str, Any]) -> dict[str, Any]:
        """Réserve le créneau donné (tel que retourné par get_availability)."""
        response = self._session.post(
            BOOK_URL,
            json={
                "clubOfChoice": self.club_id,
                "doorPolicy": slot.get("id") or slot.get("policyId"),
                "duration": slot.get("duration", 60),
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 401:
            raise BasicFitAuthError("Session expirée pendant book-door-policy")
        response.raise_for_status()
        return response.json()


def find_slot_at_time(
    slots: list[dict[str, Any]], target_time: dt.time
) -> dict[str, Any] | None:
    """Cherche un créneau disponible à target_time dans la liste retournée par l'API.

    Les noms de champs (time/available) sont une hypothèse à confirmer avec
    une vraie réponse de l'API (voir test_connection.py).
    """
    target_str = target_time.strftime("%H:%M")
    for slot in slots or []:
        slot_time = str(slot.get("time") or slot.get("startTime") or slot.get("hour") or "")
        is_available = bool(slot.get("available", slot.get("isAvailable", False)))
        if is_available and slot_time.startswith(target_str):
            return slot
    return None
