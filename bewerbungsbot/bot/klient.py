"""Zugang zur Claude API - eine einzige Stelle, an der Modellaufrufe stattfinden."""

from __future__ import annotations

import json
from typing import Any

import anthropic

# Serverseitige Ersatzmodelle: Lehnt ein Sicherheitsfilter eine Anfrage ab,
# beantwortet sie ein anderes Modell, statt dass der Lauf abbricht.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ModellFehler(RuntimeError):
    """Das Modell hat keine verwertbare Antwort geliefert."""


def klient(api_key: str | None = None) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def antwort_text(
    client: anthropic.Anthropic,
    modell: str,
    system: str,
    nachricht: str,
    max_tokens: int = 8000,
    schema: dict[str, Any] | None = None,
    aufwand: str | None = None,
) -> str:
    """Stellt eine Frage und gibt den Text der Antwort zurueck.

    Mit `schema` erzwingt der Aufruf gueltiges JSON nach diesem Schema; der
    Rueckgabewert ist dann direkt mit json.loads lesbar.
    """
    ausgabe: dict[str, Any] = {}
    if aufwand:
        ausgabe["effort"] = aufwand
    if schema:
        ausgabe["format"] = {"type": "json_schema", "schema": schema}

    anfrage: dict[str, Any] = {
        "model": modell,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": nachricht}],
        "thinking": {"type": "adaptive"},
    }
    if ausgabe:
        anfrage["output_config"] = ausgabe

    antwort = _senden(client, anfrage)

    if getattr(antwort, "stop_reason", None) == "refusal":
        grund = getattr(getattr(antwort, "stop_details", None), "explanation", "") or ""
        raise ModellFehler(f"Das Modell hat die Anfrage abgelehnt. {grund}".strip())

    texte = [block.text for block in antwort.content if getattr(block, "type", "") == "text"]
    if not texte:
        raise ModellFehler("Die Antwort enthielt keinen Text.")
    return "\n".join(texte).strip()


def antwort_json(
    client: anthropic.Anthropic,
    modell: str,
    system: str,
    nachricht: str,
    schema: dict[str, Any],
    max_tokens: int = 4000,
    aufwand: str | None = None,
) -> dict[str, Any]:
    """Wie antwort_text, gibt aber das bereits gelesene JSON-Objekt zurueck."""
    roh = antwort_text(client, modell, system, nachricht, max_tokens, schema, aufwand)
    try:
        return json.loads(roh)
    except json.JSONDecodeError as fehler:
        raise ModellFehler(f"Antwort war kein gueltiges JSON: {roh[:200]}") from fehler


def _senden(client: anthropic.Anthropic, anfrage: dict[str, Any]) -> Any:
    """Bevorzugt den Aufruf mit Ersatzmodellen, faellt sonst auf den einfachen zurueck."""
    try:
        return client.beta.messages.create(
            betas=[FALLBACK_BETA], fallbacks="default", **anfrage
        )
    except (TypeError, AttributeError, anthropic.BadRequestError):
        # Aeltere SDK-Version oder das Konto kennt die Beta nicht - beides
        # kein Grund, den Lauf abzubrechen.
        return client.messages.create(**anfrage)
