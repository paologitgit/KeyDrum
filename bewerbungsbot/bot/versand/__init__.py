"""Versandwege. Derzeit ist der E-Mail-Versand umgesetzt."""

from .email_versand import VersandFehler, versenden, nachricht_bauen

__all__ = ["versenden", "nachricht_bauen", "VersandFehler"]
