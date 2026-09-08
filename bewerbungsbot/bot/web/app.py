"""Lokales Dashboard: Treffer sichten, Anschreiben bearbeiten, Bewerbung freigeben.

Bewusst nur fuer den Betrieb auf dem eigenen Rechner gedacht - es gibt keine
Anmeldung, weil der Server ausschliesslich an 127.0.0.1 gebunden wird.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import anschreiben as anschreiben_modul
from .. import brief_pdf, pipeline
from ..db import Ablage
from ..klient import klient
from ..konfig import Profil, Zugang
from ..modelle import (
    ENTWURF, STATUS_BESCHRIFTUNG, STATUS_REIHENFOLGE, VERWORFEN,
)

VORLAGEN = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
_lauf_sperre = threading.Lock()


def _aus_json(wert: Any) -> list[str]:
    """Liest die als JSON abgelegten Listen (Staerken, Luecken) fuer die Anzeige."""
    if isinstance(wert, list):
        return [str(e) for e in wert]
    try:
        gelesen = json.loads(wert or "[]")
    except (TypeError, ValueError):
        return []
    return [str(e) for e in gelesen] if isinstance(gelesen, list) else []


VORLAGEN.env.filters["fromjson"] = _aus_json


def anwendung(profil: Profil, zugang: Zugang, ablage: Ablage) -> FastAPI:
    app = FastAPI(title="Bewerbungsbot")
    zustand: dict[str, Any] = {"meldung": "", "laeuft": False}

    def seite(request: Request, vorlage: str, **daten: Any) -> HTMLResponse:
        meldung = zustand.get("meldung", "")
        zustand["meldung"] = ""
        return VORLAGEN.TemplateResponse(
            request=request,
            name=vorlage,
            context={
                "beschriftung": STATUS_BESCHRIFTUNG,
                "meldung": meldung,
                "laeuft": zustand["laeuft"],
                "trockenlauf": zugang.trockenlauf,
                "profil": profil,
                **daten,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def liste(request: Request, status: str | None = None) -> HTMLResponse:
        zaehlung = ablage.zaehlung()
        if status is None:
            # Beim Aufruf ohne Reiter nicht stur auf die Freigabe zeigen: Wer nur
            # gesucht hat, saehe sonst eine leere Seite, obwohl Treffer vorliegen.
            status = next(
                (s for s in STATUS_REIHENFOLGE if zaehlung.get(s)), ENTWURF
            )
        zeilen = ablage.alle() if status == "alle" else ablage.nach_status(status)
        return seite(
            request, "liste.html",
            zeilen=zeilen, status=status,
            zaehlung=zaehlung,
            reihenfolge=STATUS_REIHENFOLGE,
            heute=ablage.heute_versendet(),
            tageslimit=int(profil.grenzen.get("max_bewerbungen_pro_tag", 5)),
        )

    @app.get("/stelle/{stelle_id}", response_class=HTMLResponse)
    def detail(request: Request, stelle_id: int) -> Any:
        zeile = ablage.holen(stelle_id)
        if zeile is None:
            return RedirectResponse("/", status_code=303)
        return seite(
            request, "detail.html",
            zeile=zeile, ereignisse=ablage.ereignisse(stelle_id),
        )

    @app.post("/stelle/{stelle_id}/speichern")
    def speichern(
        stelle_id: int,
        betreff: str = Form(""),
        anschreiben: str = Form(""),
        empfaenger: str = Form(""),
        notiz: str = Form(""),
    ) -> RedirectResponse:
        ablage.aktualisieren(
            stelle_id, betreff=betreff.strip(),
            anschreiben=anschreiben.strip(),
            empfaenger=empfaenger.strip(), notiz=notiz.strip(),
        )
        # Das PDF muss den bearbeiteten Text tragen, nicht mehr den erzeugten.
        zeile = ablage.holen(stelle_id)
        if zeile and anschreiben.strip():
            brief = anschreiben_modul.aus_text(anschreiben, profil)
            brief["betreff"] = betreff.strip() or (zeile["titel"] or "Bewerbung")
            pfad = brief_pdf.erzeugen(brief, pipeline.zeile_zu_stelle(zeile), profil)
            ablage.aktualisieren(stelle_id, anschreiben_pdf=str(pfad))
        ablage.ereignis(stelle_id, "bearbeitet", "Entwurf von Hand angepasst")
        zustand["meldung"] = "Gespeichert."
        return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)

    @app.post("/stelle/{stelle_id}/neu-verfassen")
    def neu_verfassen(stelle_id: int) -> RedirectResponse:
        try:
            pipeline.entwerfen(profil, ablage, klient(zugang.anthropic_key), stelle_id=stelle_id)
            zustand["meldung"] = "Neues Anschreiben verfasst."
        except Exception as fehler:
            zustand["meldung"] = f"Fehlgeschlagen: {fehler}"
        return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)

    @app.post("/stelle/{stelle_id}/senden")
    def senden(stelle_id: int) -> RedirectResponse:
        erfolg, meldung = pipeline.freigeben(profil, zugang, ablage, stelle_id)
        zustand["meldung"] = meldung if erfolg else f"Nicht versendet: {meldung}"
        return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)

    @app.post("/stelle/{stelle_id}/verwerfen")
    def verwerfen(stelle_id: int) -> RedirectResponse:
        ablage.aktualisieren(stelle_id, status=VERWORFEN)
        ablage.ereignis(stelle_id, "verworfen", "von Hand verworfen")
        zustand["meldung"] = "Stelle verworfen."
        return RedirectResponse("/", status_code=303)

    @app.post("/stelle/{stelle_id}/status")
    def status_setzen(stelle_id: int, status: str = Form(...)) -> RedirectResponse:
        if status in STATUS_BESCHRIFTUNG:
            ablage.aktualisieren(stelle_id, status=status)
            ablage.ereignis(stelle_id, "status", STATUS_BESCHRIFTUNG[status])
        return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)

    @app.get("/pdf/{stelle_id}")
    def pdf(stelle_id: int) -> Any:
        zeile = ablage.holen(stelle_id)
        if not zeile or not zeile["anschreiben_pdf"]:
            return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)
        pfad = Path(zeile["anschreiben_pdf"])
        if not pfad.exists():
            return RedirectResponse(f"/stelle/{stelle_id}", status_code=303)
        return FileResponse(pfad, media_type="application/pdf", filename=pfad.name)

    @app.post("/lauf")
    def lauf_starten(hintergrund: BackgroundTasks) -> RedirectResponse:
        if zustand["laeuft"]:
            zustand["meldung"] = "Es laeuft bereits eine Suche."
            return RedirectResponse("/", status_code=303)

        def arbeiten() -> None:
            # Die Sperre verhindert parallele Laeufe, die dieselbe Stelle doppelt anlegen.
            with _lauf_sperre:
                zustand["laeuft"] = True
                try:
                    ergebnis = pipeline.lauf(profil, ablage, client=klient(zugang.anthropic_key))
                    zustand["meldung"] = (
                        f"Lauf beendet: {ergebnis['suche']['neu']} neue Stellen, "
                        f"{ergebnis['entwuerfe']['entworfen']} Entwuerfe."
                    )
                except Exception as fehler:
                    zustand["meldung"] = f"Lauf abgebrochen: {fehler}"
                finally:
                    zustand["laeuft"] = False

        hintergrund.add_task(arbeiten)
        zustand["meldung"] = "Suche gestartet. Die Seite in ein bis zwei Minuten neu laden."
        return RedirectResponse("/", status_code=303)

    return app
