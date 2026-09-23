"""Erzeugt aus index.html, css/ und js/ eine einzige, eigenständige HTML-Datei.

Aufruf (im Ordner mathe-tool):  python3 werkzeuge/einzeldatei.py
"""
import pathlib
import re

basis = pathlib.Path(__file__).resolve().parent.parent
html = (basis / 'index.html').read_text(encoding='utf-8')


def css_einbetten(m):
    inhalt = (basis / m.group(1)).read_text(encoding='utf-8')
    return '<style>\n' + inhalt + '</style>'


def js_einbetten(m):
    inhalt = (basis / m.group(1)).read_text(encoding='utf-8')
    return '<script>\n' + inhalt + '</script>'


html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', css_einbetten, html)
html = re.sub(r'<script src="([^"]+)"></script>', js_einbetten, html)
# Der Hinweis auf fehlende Dateien ist in der Einzeldatei überflüssig.
html = re.sub(r'\s*<!-- ladehinweis -->.*?<!-- /ladehinweis -->', '', html, flags=re.S)

ziel = basis / 'Mathe-1-Sek.html'
ziel.write_text(html, encoding='utf-8')
print('Geschrieben:', ziel)
