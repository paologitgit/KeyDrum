"""Bewerbungsversand per E-Mail, mit Probelauf als Standardeinstellung."""

from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from ..konfig import WURZEL, Profil, Zugang

POSTAUSGANG = WURZEL / "ausgabe" / "postausgang"


class VersandFehler(RuntimeError):
    """Die Bewerbung konnte nicht verschickt werden."""


def nachricht_bauen(
    profil: Profil,
    zugang: Zugang,
    empfaenger: str,
    betreff: str,
    brieftext: str,
    anhaenge: list[Path],
) -> EmailMessage:
    """Setzt die vollstaendige Bewerbungsmail zusammen."""
    nachricht = EmailMessage()
    nachricht["From"] = formataddr((profil.voller_name, zugang.smtp_absender or ""))
    nachricht["To"] = empfaenger
    nachricht["Subject"] = betreff
    if profil.versand.get("kopie_an_mich") and profil.person.get("email"):
        nachricht["Bcc"] = profil.person["email"]
    if profil.person.get("email"):
        nachricht["Reply-To"] = profil.person["email"]

    koerper = brieftext.rstrip()
    signatur = profil.signatur().strip()
    if signatur and signatur not in koerper:
        koerper = f"{koerper}\n\n{signatur}"
    nachricht.set_content(koerper)

    for pfad in anhaenge:
        _anhaengen(nachricht, pfad)
    return nachricht


def versenden(
    profil: Profil,
    zugang: Zugang,
    empfaenger: str,
    betreff: str,
    brieftext: str,
    anhaenge: list[Path],
) -> tuple[bool, str]:
    """Verschickt die Bewerbung. Rueckgabe: (wirklich_versendet, Meldung).

    Im Probelauf (TROCKENLAUF=1) wird die fertige Mail nur als Datei abgelegt.
    So sehen Sie exakt, was hinausgehen wuerde, ohne dass es hinausgeht.
    """
    if not empfaenger or "@" not in empfaenger:
        raise VersandFehler(f"Keine brauchbare Empfaengeradresse: '{empfaenger}'")

    fehlend = [p for p in anhaenge if not p.exists()]
    if fehlend:
        raise VersandFehler(
            "Diese Anhaenge fehlen: " + ", ".join(str(p) for p in fehlend)
        )

    nachricht = nachricht_bauen(profil, zugang, empfaenger, betreff, brieftext, anhaenge)

    if zugang.trockenlauf:
        pfad = _ablegen(nachricht, empfaenger)
        return False, f"Probelauf - Mail abgelegt unter {pfad}"

    if not zugang.smtp_bereit():
        raise VersandFehler(
            "Die SMTP-Zugangsdaten in der .env sind unvollstaendig "
            "(SMTP_HOST, SMTP_BENUTZER, SMTP_PASSWORT, SMTP_ABSENDER)."
        )

    try:
        with smtplib.SMTP(zugang.smtp_host, zugang.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(zugang.smtp_benutzer, zugang.smtp_passwort)
            server.send_message(nachricht)
    except smtplib.SMTPException as fehler:
        raise VersandFehler(f"SMTP-Fehler: {fehler}") from fehler

    _ablegen(nachricht, empfaenger)  # Beleg fuer die eigenen Unterlagen
    return True, f"Versendet an {empfaenger}"


def _anhaengen(nachricht: EmailMessage, pfad: Path) -> None:
    typ, _ = mimetypes.guess_type(pfad.name)
    haupt, unter = (typ or "application/octet-stream").split("/", 1)
    nachricht.add_attachment(
        pfad.read_bytes(), maintype=haupt, subtype=unter, filename=pfad.name
    )


def _ablegen(nachricht: EmailMessage, empfaenger: str) -> Path:
    POSTAUSGANG.mkdir(parents=True, exist_ok=True)
    sauber = "".join(z if z.isalnum() or z in "@.-_" else "_" for z in empfaenger)
    ziel = POSTAUSGANG / f"{sauber}_{abs(hash(nachricht['Subject'])) % 10**6}.eml"
    ziel.write_bytes(bytes(nachricht))
    return ziel
