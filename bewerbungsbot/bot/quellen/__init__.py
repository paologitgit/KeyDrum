"""Verzeichnis der verfuegbaren Stellenquellen."""

from __future__ import annotations

from ..konfig import Profil
from .basis import Quelle, entdoppeln
from .jobs_ch import JobsCh
from .manuell import Manuell

VERFUEGBAR: dict[str, type[Quelle]] = {
    JobsCh.name: JobsCh,
    Manuell.name: Manuell,
}


def bauen(namen: list[str], profil: Profil, **kwargs) -> list[Quelle]:
    """Erzeugt die gewuenschten Quellen. Unbekannte Namen melden sich deutlich."""
    unbekannt = [n for n in namen if n not in VERFUEGBAR]
    if unbekannt:
        raise ValueError(
            f"Unbekannte Quelle(n): {', '.join(unbekannt)}. "
            f"Verfuegbar: {', '.join(VERFUEGBAR)}"
        )
    pause = float(profil.grenzen.get("pause_sekunden", 4))
    return [VERFUEGBAR[n](profil, pause=pause, **(kwargs if n == JobsCh.name else {})) for n in namen]


__all__ = ["VERFUEGBAR", "bauen", "Quelle", "JobsCh", "Manuell", "entdoppeln"]
