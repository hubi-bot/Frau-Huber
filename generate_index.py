# Baut die Internetseite automatisch aus den Ordnern.
# Dieses Skript läuft bei jeder Änderung von selbst auf GitHub – du musst nichts daran ändern.
#
# Was dabei entsteht:
#   …/Frau-Huber/                     -> neutrale Startseite ohne Materialliste
#   …/Frau-Huber/<kurzname>.html      -> jede Lernumgebung unter einem kurzen Link (für die Klasse)
#   …/Frau-Huber/<UEBERSICHT>/        -> die Übersicht aller Materialien (nur für Lehrkräfte)
#
# Wer einen Link zu einer einzelnen Lernumgebung bekommt, kommt von dort nicht zur Übersicht:
# Die Startseite zeigt keine Liste, und die Ordner selbst werden nicht veröffentlicht.
#
#   Ordner auf oberster Ebene   -> eine Gruppe (z. B. "Mathematik 5", "Chemie Oberstufe")
#   Anfang des Ordnernamens     -> das Fach    ("Mathe…" = Mathematik, "Chemie…" = Chemie, sonst "Weitere Fächer")
#   Unterordner darin           -> ein Thema   (z. B. "Mathematik 6/Bruchrechnung")
#   Dateien                     -> Einträge (HTML, PDF, Word, PowerPoint, Excel, Bilder)
#   links.txt                   -> Links ins Internet, eine Zeile pro Link:  Titel | https://...
#                                  Beginnt die Zeile mit einem Ausrufezeichen (! Titel | https://...),
#                                  steht der Link ganz oben im Bereich statt unten unter "Links".
#   kurzlinks.txt               -> Kurznamen, eine Zeile pro Datei:  kurzname | Ordner/Dateiname
#                                  Fehlt eine Datei dort, wird der Kurzname aus dem Dateinamen gebildet.
#   titel.txt                   -> Überschriften, eine Zeile pro Eintrag:  Ordner/Dateiname | Neuer Titel
#                                  So lässt sich ein Titel ändern, ohne die Datei umzubenennen (der Link bleibt gleich).
#
# Eine Zahl vorne im Namen bestimmt die Reihenfolge und wird nicht angezeigt:
#   "1 Natürliche Zahlen", "2 Geometrie"  ->  "Natürliche Zahlen", "Geometrie"
#
# Weiterleitungen: Eine HTML-Datei, die <meta name="weiterleitung" ...> enthält, leitet nur auf eine
# neuere Fassung um. Sie bleibt unter ihrer alten Adresse erreichbar, erscheint aber nicht in der Übersicht.
# Auch alle bisherigen langen Adressen (…/Mathematik 6/Bruchheft ….html) leiten auf den Kurzlink weiter.

import html
import json
import os
import re
import shutil
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

SEITENTITEL = "Unterrichtsmaterialien"
UNTERTITEL = "Übersicht für Lehrkräfte – bitte nur einzelne Kurzlinks an die Klasse weitergeben"
# Auf GitHub wird der Name des Repositorys automatisch erkannt (auch nach einem Umbenennen).
REPO = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "hubi-bot/Frau-Huber")
UEBERSICHT = "uebersicht-x4brac"  # Ordnername der Übersicht; nicht an Schüler weitergeben
AUSGABE = "_site"

# Fächer in der Reihenfolge des Umschalters: (Kürzel, Name, Symbol, Ordner-Anfänge in Kleinbuchstaben)
FAECHER = [
    ("mathematik", "Mathematik", "📐", ("mathe",)),
    ("chemie", "Chemie", "🧪", ("chemie",)),
    ("forensik", "Forensik", "🔬", ("forensik",)),
    ("informatik", "Informatik", "💻", ("informatik",)),
    ("weitere", "Weitere", "🗂️", ()),  # alles andere
]

AUSGESCHLOSSEN = {".git", ".github", AUSGABE}
NICHT_VEROEFFENTLICHEN = {"generate_index.py", "README.md", "kurzlinks.txt", "titel.txt", "index.html", ".gitignore"}
TYPEN = {
    ".html": "Ansehen", ".htm": "Ansehen",
    ".pdf": "PDF",
    ".docx": "Word", ".doc": "Word", ".odt": "Text",
    ".pptx": "PowerPoint", ".ppt": "PowerPoint", ".odp": "Präsentation",
    ".xlsx": "Excel", ".xls": "Excel", ".ods": "Tabelle",
    ".png": "Bild", ".jpg": "Bild", ".jpeg": "Bild", ".gif": "Bild",
    ".ggb": "GeoGebra", ".mp4": "Video", ".mp3": "Audio", ".zip": "ZIP",
}
SYMBOL = {
    "Ansehen": "🖥️", "PDF": "📄", "Bild": "🖼️", "Video": "🎬", "Audio": "🎧",
    "GeoGebra": "📐", "Word": "📝", "Text": "📝", "PowerPoint": "📊", "Präsentation": "📊",
    "Excel": "📈", "Tabelle": "📈", "ZIP": "🗜️",
}
# Diese Typen öffnet der Browser direkt – alles andere wird heruntergeladen.
IM_BROWSER = {"Ansehen", "PDF", "Bild", "Video", "Audio"}


def ist_download(e):
    return e["typ"] != "Link" and e["typ"] not in IM_BROWSER


def sortierschluessel(name):
    """Natürliche Sortierung: 'Mathematik 5' vor 'Mathematik 10'."""
    return [(0, int(t)) if t.isdigit() else (1, t.lower()) for t in re.split(r"(\d+)", name) if t != ""]


def gruppenschluessel(name):
    """Gruppen eines Fachs nach Klassenstufe ordnen: 5, 6, 8, 10, 12 … und Namen ohne Zahl ans Ende."""
    zahl = re.search(r"\d+", name)
    return (int(zahl.group()) if zahl else 999, name.lower())


def fach_von(ordnername):
    klein = ordnername.lower()
    for kuerzel, _, _, anfaenge in FAECHER:
        if any(klein.startswith(a) for a in anfaenge):
            return kuerzel
    return FAECHER[-1][0]


def anzeigename(name):
    """'2_Brüche-kürzen.pdf' -> 'Brüche kürzen'"""
    name = os.path.splitext(name)[0] if os.path.splitext(name)[1].lower() in TYPEN else name
    name = re.sub(r"^\d+[\s_.\-]+(?=\D)", "", name)  # führende Ordnungsnummer entfernen
    name = name.lstrip("-_ ")
    return re.sub(r"[_]+", " ", name).replace(" - ", " – ").strip()


def kennnummer(name):
    """Dateien, die mit 'ZAHL-' beginnen, sind über ?id=ZAHL direkt erreichbar (wie bisher)."""
    teile = name.split("-", 1)
    return teile[0] if len(teile) == 2 and teile[0].isdigit() else None


def ist_weiterleitung(pfad):
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            return 'name="weiterleitung"' in f.read(1500)
    except OSError:
        return False


# ---------- Überschriften aus titel.txt ----------
def titel_lesen():
    karte = {}
    if os.path.isfile("titel.txt"):
        with open("titel.txt", encoding="utf-8-sig") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#") or "|" not in zeile:
                    continue
                was, titel = (t.strip() for t in zeile.split("|", 1))
                if was and titel:
                    karte[was.replace("\\", "/").rstrip("/")] = titel
    return karte


TITEL = titel_lesen()
SEITENTITEL = TITEL.get("Seitentitel", SEITENTITEL)
UNTERTITEL = TITEL.get("Untertitel", UNTERTITEL)
START_TITEL = TITEL.get("Startseite", "Lernmaterial von Frau Huber")
START_TEXT = TITEL.get("Startseite-Text", "Öffne bitte den Link oder scanne den QR-Code, den du im Unterricht bekommen hast.")


def titel_fuer(pfad):
    """Titel aus titel.txt, sonst aus dem Datei- oder Ordnernamen."""
    return TITEL.get(pfad) or anzeigename(os.path.basename(pfad))


# ---------- Kurznamen ----------
def kurzform(text):
    """'Bruchheft - Brüche multiplizieren' -> 'bruchheft-brueche-multiplizieren'"""
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "material"


def kurzlinks_lesen():
    karte = {}
    if os.path.isfile("kurzlinks.txt"):
        with open("kurzlinks.txt", encoding="utf-8-sig") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#") or "|" not in zeile:
                    continue
                kurz, pfad = (t.strip() for t in zeile.split("|", 1))
                if kurz and pfad:
                    karte[pfad.replace("\\", "/")] = kurzform(kurz)
    return karte


KURZLINKS = kurzlinks_lesen()
vergeben = {}  # Kurzdateiname -> Quellpfad
# Namen, die im Hauptordner schon belegt sind (lose Dateien, Startseite, Übersicht)
belegt = {n.lower() for n in os.listdir(".")} | {"index.html", UEBERSICHT}


def kurzname_fuer(pfad):
    """Liefert den Dateinamen des Kurzlinks, z. B. 'bruch-mal.html'."""
    endung = os.path.splitext(pfad)[1].lower()
    basis = KURZLINKS.get(pfad) or kurzform(anzeigename(os.path.basename(pfad)))
    name, nr = f"{basis}{endung}", 2
    while name in vergeben or name in belegt:
        name, nr = f"{basis}-{nr}{endung}", nr + 1
    vergeben[name] = pfad
    return name


def links_lesen(pfad):
    eintraege = []
    with open(pfad, encoding="utf-8-sig") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#"):
                continue
            oben = zeile.startswith("!")  # "! Titel | Adresse" steht ganz oben im Bereich
            zeile = zeile.lstrip("! ").strip()
            if "|" in zeile:
                titel, url = (t.strip() for t in zeile.split("|", 1))
            else:
                titel, url = zeile, zeile
            if url.startswith(("http://", "https://")):
                eintraege.append({"titel": titel, "url": url, "typ": "Link", "extern": True, "oben": oben})
    return eintraege


id_karte = {}
weiterleitungen = []  # vorhandene Weiterleitungs-Dateien: unverändert unter alter Adresse veröffentlichen


def ordner_lesen(ordner):
    """Liefert (eintraege, themen, links) für einen Ordner."""
    eintraege, themen, links = [], [], []
    for name in sorted(os.listdir(ordner), key=lambda n: sortierschluessel(os.path.splitext(n)[0])):
        pfad = os.path.join(ordner, name).replace(os.sep, "/")
        if name.startswith("."):
            continue
        if os.path.isdir(pfad):
            if name in AUSGESCHLOSSEN:
                continue
            e, t, l = ordner_lesen(pfad)
            for unter_name, unter_e, _ in t:  # tiefere Ebenen unter dem Thema einsortieren
                e += unter_e
            e += l  # Links eines Themas stehen am Ende des Themas
            if e:
                themen.append((titel_fuer(pfad), e, pfad))
        elif name.lower() == "links.txt":
            links += links_lesen(pfad)
        else:
            endung = os.path.splitext(name)[1].lower()
            if endung not in TYPEN:
                continue
            if endung in (".html", ".htm") and ist_weiterleitung(pfad):
                weiterleitungen.append(pfad)
                continue
            kurz = kurzname_fuer(pfad)
            nummer = kennnummer(name)
            if nummer:
                id_karte.setdefault(nummer, quote(kurz))
            eintraege.append({"titel": titel_fuer(pfad), "kurz": kurz, "quelle": pfad, "typ": TYPEN[endung], "extern": False, "id": nummer})
    return eintraege, themen, links


def eintrag_html(e):
    symbol = ("📌" if e.get("oben") else "🔗") if e["typ"] == "Link" else SYMBOL.get(e["typ"], "📎")
    titel = html.escape(e["titel"])
    titel_html = titel if e["typ"] == "Link" else f'<span class="edit" data-key="{html.escape(e["quelle"])}">{titel}</span>'
    if e["typ"] == "Link":
        url, knopf, farbe, ziel, extras = e["url"], "Öffnen", "text-bg-success", 'target="_blank" rel="noopener"', ""
    else:
        url = "../" + quote(e["kurz"])
        if ist_download(e):
            knopf, farbe, ziel = f"⬇ {e['typ']}", "text-bg-warning", "download"
        else:
            knopf, farbe, ziel = "Ansehen", "text-bg-primary", 'target="_blank" rel="noopener"'
        teilen = re.sub(r"\.html?$", "", url)  # zum Weitergeben reicht der Name ohne ".html"
        extras = (
            f'<button type="button" class="btn btn-sm btn-outline-secondary kopieren" data-url="{html.escape(teilen)}" title="Kurzlink kopieren" aria-label="Kurzlink zu {titel} kopieren">🔗 Link</button>'
            f'<button type="button" class="btn btn-sm btn-outline-secondary qr" data-url="{html.escape(teilen)}" data-titel="{titel}" title="QR-Code zeigen" aria-label="QR-Code zu {titel} zeigen">QR</button>'
        )
    nummer = f'<span class="badge text-bg-secondary me-1">ID {html.escape(e["id"])}</span>' if e.get("id") else ""
    return f"""
          <div class="list-group-item d-flex flex-wrap justify-content-between align-items-center gap-2 eintrag" data-id="{html.escape(e.get('id') or '')}">
            <a href="{html.escape(url)}" {ziel} class="flex-grow-1 text-decoration-none text-body titel">{nummer}{symbol} {titel_html}</a>
            <span class="d-flex align-items-center gap-2">{extras}<a href="{html.escape(url)}" {ziel} class="badge rounded-pill {farbe} text-decoration-none">{html.escape(knopf)}</a></span>
          </div>"""


def weiterleitung_html(ziel, titel):
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="weiterleitung" content="{html.escape(ziel)}">
<meta http-equiv="refresh" content="0; url={html.escape(ziel)}">
<meta name="robots" content="noindex">
<title>Weiterleitung</title>
<script>location.replace("{ziel}"+location.hash);</script>
</head>
<body>
<p>Dieses Material hat eine neue Adresse: <a href="{html.escape(ziel)}">{html.escape(titel)}</a></p>
</body>
</html>
"""


# ---------- Ordner einlesen ----------
gruppen = []  # (fach, ordnername, eintraege, themen)
alle_dateien = []
for name in os.listdir("."):
    if os.path.isdir(name) and name not in AUSGESCHLOSSEN and not name.startswith("."):
        eintraege, themen, links = ordner_lesen(name)
        alle_dateien += [e for e in eintraege if not e["extern"]]
        for _, liste, _ in themen:
            alle_dateien += [e for e in liste if not e["extern"]]
        downloads = [e for e in eintraege if ist_download(e)]
        eintraege = [l for l in links if l.get("oben")] + [e for e in eintraege if not ist_download(e)]
        links = [l for l in links if not l.get("oben")]
        if downloads:  # Download-Dateien der Gruppe als eigener Abschnitt
            themen.append(("Downloads", downloads, None))
        if links:  # Links der Gruppe kommen als eigener Abschnitt ans Ende
            themen.append(("Links", links, None))
        gruppen.append((fach_von(name), name, eintraege, themen))

reihenfolge = {k: i for i, (k, _, _, _) in enumerate(FAECHER)}
gruppen.sort(key=lambda g: (reihenfolge[g[0]], gruppenschluessel(g[1])))
belegte_faecher = [f for f in FAECHER if any(g[0] == f[0] for g in gruppen)]

SPALTEN = [f for f in FAECHER if f[0] != "weitere"]  # von links: Mathematik, Chemie, Forensik, Informatik
bereiche = []  # (fach, id, ordnername, titel, anzahl)
karten = ""
for fach, ordnername, eintraege, themen in gruppen:
    gruppe = titel_fuer(ordnername)
    anker = "b-" + kurzform(ordnername)
    anzahl = len(eintraege) + sum(len(e) for _, e, _ in themen)
    bereiche.append((fach, anker, ordnername, gruppe, anzahl))
    inhalt = ""
    if eintraege:
        inhalt += '<div class="list-group list-group-flush mb-2">' + "".join(eintrag_html(e) for e in eintraege) + "</div>"
    for thema, e, schluessel in themen:
        thema_html = f'<span class="edit" data-key="{html.escape(schluessel)}">{html.escape(thema)}</span>' if schluessel else html.escape(thema)
        inhalt += f'<div class="thema"><h3 class="h6 thema-titel">{thema_html}</h3><div class="list-group list-group-flush">' + "".join(eintrag_html(x) for x in e) + "</div></div>"
    if not inhalt:
        inhalt = '<p class="text-muted mb-0">Noch keine Materialien.</p>'
    karten += f"""
    <section class="card gruppe" id="{anker}" hidden>
      <div class="card-body">
        <a class="btn btn-sm btn-outline-secondary mb-3 zurueck" href="#">← Zur Auswahl</a>
        <h2 class="h4 gruppen-titel">📂 <span class="edit" data-key="{html.escape(ordnername)}">{html.escape(gruppe)}</span></h2>
        {inhalt}
      </div>
    </section>"""


def bereich_knopf(b, klasse):
    fach, anker, ordnername, gruppe, anzahl = b
    return f'<a class="btn {klasse} bereich-knopf" href="#{anker}" data-b="{anker}"><span class="titel-kopie" data-key="{html.escape(ordnername)}">{html.escape(gruppe)}</span></a>'


# Startauswahl: drei Spalten. Was zu keinem der drei Fächer gehört, steht rechts unter "Weitere".
spalten = ""
for kuerzel, fachname, symbol, _ in SPALTEN:
    knopf_liste = "".join(bereich_knopf(b, "btn-lg btn-outline-primary") for b in bereiche if b[0] == kuerzel)
    if kuerzel == SPALTEN[-1][0]:
        weitere = "".join(bereich_knopf(b, "btn-outline-secondary") for b in bereiche if b[0] == "weitere")
        if weitere:
            knopf_liste += f'<h3 class="h6 text-muted mt-3 mb-0">Weitere</h3>{weitere}'
    spalten += f"""
      <div class="col-sm-6 col-lg-{12 // len(SPALTEN)}">
        <div class="card h-100 fach-spalte"><div class="card-body">
          <h2 class="h4 text-center mb-3">{symbol} {html.escape(fachname)}</h2>
          <div class="d-grid gap-2">{knopf_liste or '<p class="text-muted text-center mb-0">Noch keine Materialien.</p>'}</div>
        </div></div>
      </div>"""

stand = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y, %H:%M Uhr")
id_json = json.dumps(id_karte, ensure_ascii=False)
repo_name_json = json.dumps(REPO.split("github.com/", 1)[1])

uebersicht = f"""<!DOCTYPE html>
<html lang="de" data-bs-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>{html.escape(SEITENTITEL)}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background-color: #f8f9fa; padding: 2rem 0; }}
    .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1.5rem; scroll-margin-top: 1rem; }}
    .gruppen-titel {{ border-bottom: 2px solid #0d6efd; padding-bottom: .5rem; color: #495057; margin-bottom: 1rem; }}
    .thema {{ margin-top: 1rem; }}
    .thema-titel {{ color: #0d6efd; text-transform: uppercase; letter-spacing: .04em; font-size: .8rem; font-weight: 700; margin-bottom: .25rem; }}
    .list-group-item:hover {{ background-color: #f1f3f5; }}
    .eintrag .btn-sm {{ padding: .1rem .5rem; font-size: .78rem; }}
    input.edit-feld {{ display: inline-block; width: min(100%, 34rem); vertical-align: middle; }}
    .eintrag input.edit-feld {{ width: min(100%, 26rem); }}
    #edit-leiste {{ position: sticky; top: .5rem; z-index: 5; border: 2px solid #0d6efd; }}
    .fach-spalte h2 {{ border-bottom: 2px solid #0d6efd; padding-bottom: .5rem; color: #495057; }}
    .bereich-knopf[aria-current="page"] {{ background: #0d6efd; color: #fff; }}
    #qr-fenster {{ border: none; border-radius: 1rem; padding: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,.25); text-align: center; max-width: 92vw; }}
    #qr-fenster::backdrop {{ background: rgba(0,0,0,.5); }}
    #qr-bild img, #qr-bild canvas {{ margin: 0 auto; width: min(70vw, 320px); height: auto; }}
    #qr-adresse {{ overflow-wrap: anywhere; user-select: all; }}

    /* Dunkles Design wie in den Rechenheften, mit Pink als Akzentfarbe */
    :root {{
      --grund: #121620; --papier: #1c2232; --linie: #2e3a55; --schrift: #e7ebf3; --leise: #a4aec3;
      --pink: #ff6fb5; --pink-kraeftig: #d6267f; --pink-dunkel: #b81d6b;
      --bs-body-bg: var(--grund); --bs-body-color: var(--schrift); --bs-secondary-color: var(--leise);
      --bs-primary: var(--pink-kraeftig); --bs-primary-rgb: 214, 38, 127; --bs-border-color: var(--linie);
      --bs-link-color: var(--pink); --bs-link-color-rgb: 255, 111, 181; --bs-link-hover-color: #ffa3d0; --bs-link-hover-color-rgb: 255, 163, 208;
    }}
    body {{ background-color: var(--grund); color: var(--schrift);
      background-image: linear-gradient(rgba(46,58,85,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(46,58,85,.35) 1px, transparent 1px); background-size: 22px 22px; }}
    .card {{ background: var(--papier); box-shadow: 0 4px 14px rgba(0,0,0,.35); border-top: 4px solid var(--pink-kraeftig); }}
    h1, h2 {{ color: var(--schrift); }}
    .text-muted, .lead.text-muted {{ color: var(--leise) !important; }}
    .gruppen-titel, .fach-spalte h2 {{ border-bottom-color: var(--pink-kraeftig); color: var(--schrift); }}
    .thema-titel {{ color: var(--pink); }}
    .list-group-item {{ background: transparent; border-color: var(--linie); color: var(--schrift); }}
    .list-group-item:hover {{ background-color: #252d44; }}
    .btn-primary {{ --bs-btn-bg: var(--pink-kraeftig); --bs-btn-border-color: var(--pink-kraeftig); --bs-btn-hover-bg: var(--pink-dunkel); --bs-btn-hover-border-color: var(--pink-dunkel); --bs-btn-active-bg: var(--pink-dunkel); --bs-btn-active-border-color: var(--pink-dunkel); --bs-btn-color: #fff; --bs-btn-hover-color: #fff; --bs-btn-active-color: #fff; }}
    .btn-outline-primary {{ --bs-btn-color: var(--pink); --bs-btn-border-color: var(--pink-kraeftig); --bs-btn-hover-bg: var(--pink-kraeftig); --bs-btn-hover-border-color: var(--pink-kraeftig); --bs-btn-hover-color: #fff; --bs-btn-active-bg: var(--pink-dunkel); --bs-btn-active-border-color: var(--pink-dunkel); --bs-btn-active-color: #fff; }}
    .btn-outline-secondary {{ --bs-btn-color: var(--leise); --bs-btn-border-color: #4a5778; --bs-btn-hover-bg: #34405f; --bs-btn-hover-border-color: #4a5778; --bs-btn-hover-color: #fff; --bs-btn-active-bg: #34405f; --bs-btn-active-color: #fff; }}
    .bereich-knopf[aria-current="page"] {{ background: var(--pink-kraeftig); border-color: var(--pink-kraeftig); color: #fff; }}
    .form-control {{ background-color: #161b29; border-color: var(--linie); color: var(--schrift); }}
    .form-control:focus {{ background-color: #161b29; color: var(--schrift); border-color: var(--pink); box-shadow: 0 0 0 .2rem rgba(255,111,181,.25); }}
    .form-control::placeholder {{ color: var(--leise); }}
    #edit-leiste {{ border-color: var(--pink-kraeftig); }}
    #qr-fenster {{ background: var(--papier); color: var(--schrift); }}
    #qr-bild {{ background: #fff; padding: 12px; border-radius: 10px; display: inline-block; }}
    .alert-warning {{ background: #3a3115; border-color: #6b5a1f; color: #ffe9a6; }}
    footer .link-secondary {{ color: var(--leise) !important; }}
    :focus-visible {{ outline: 3px solid var(--pink); outline-offset: 2px; }}
  </style>
</head>
<body>
  <div class="container" style="max-width: 1100px">
    <header class="text-center mb-4 position-relative">
      <button type="button" class="btn btn-sm btn-outline-primary position-absolute top-0 start-0 qr" data-url="https://hubi-bot.github.io/Frau-Huber/{UEBERSICHT}/" data-titel="Diese Übersicht (fürs iPad)" title="QR-Code zu dieser Übersicht">📱 QR</button>
      <a class="btn btn-sm btn-outline-primary position-absolute top-0 end-0" href="https://hubi-bot.github.io/Frau-Huber/uebersicht-x4brac/codes.html" title="Alle Codes der Materialien (mit Passwort)">🔑 Codes</a>
      <h1 class="display-6 fw-bold">📚 <span class="edit" data-key="Seitentitel">{html.escape(SEITENTITEL)}</span></h1>
      <p class="lead text-muted"><span class="edit" data-key="Untertitel">{html.escape(UNTERTITEL)}</span></p>
      <button type="button" class="btn btn-sm btn-outline-secondary" id="bearbeiten">✏️ Überschriften bearbeiten</button>
      <p class="text-success small mt-2 mb-0" id="edit-fertig" hidden></p>
    </header>

    <section class="card" id="edit-leiste" hidden>
      <div class="card-body">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <strong class="me-auto">✏️ Überschriften bearbeiten</strong>
          <button type="button" class="btn btn-primary" id="speichern">Speichern</button>
          <button type="button" class="btn btn-outline-secondary" id="abbrechen">Abbrechen</button>
        </div>
        <p class="small mt-2" id="edit-meldung" aria-live="polite"></p>
        <div class="row g-2 mt-1">
          <div class="col-md-5"><label class="form-label small mb-1" for="start-titel">Überschrift der Startseite für Schüler</label><input type="text" class="form-control form-control-sm edit-feld edit-start" id="start-titel" data-key="Startseite" data-alt="{html.escape(START_TITEL)}"></div>
          <div class="col-md-7"><label class="form-label small mb-1" for="start-text">Satz darunter</label><input type="text" class="form-control form-control-sm edit-feld edit-start" id="start-text" data-key="Startseite-Text" data-alt="{html.escape(START_TEXT)}"></div>
        </div>
        <div id="einfuegen" class="alert alert-warning mt-3 mb-0" hidden>
          <p class="mb-2"><strong>Noch ein Schritt bei GitHub.</strong> <span id="einfuegen-hinweis"></span></p>
          <ol class="mb-2 ps-3">
            <li><a href="{REPO}/edit/main/titel.txt" target="_blank" rel="noopener">titel.txt bei GitHub öffnen</a></li>
            <li>Dort alles markieren (Strg + A, am Mac Cmd + A) und einfügen (Strg + V, am Mac Cmd + V).</li>
            <li>Auf „Commit changes…“ klicken und bestätigen.</li>
          </ol>
          <textarea class="form-control form-control-sm mb-2" id="einfuegen-text" rows="3" readonly aria-label="Neuer Inhalt von titel.txt"></textarea>
          <button type="button" class="btn btn-sm btn-outline-secondary" id="einfuegen-fertig">Erledigt</button>
        </div>
        <details class="mt-3" id="einrichten">
          <summary class="small fw-semibold">Einmal einrichten: danach speichert der Knopf „Speichern“ alles mit einem Klick</summary>
          <p class="small mt-2 mb-2" id="token-status"></p>
          <p class="small mb-2">Diese Seite darf nur dann für dich bei GitHub speichern, wenn du es ihr einmal erlaubst. Das dauert etwa eine Minute und ist nur einmal pro Gerät nötig:</p>
          <ol class="small ps-3 mb-2">
            <li><a href="https://github.com/settings/personal-access-tokens/new?name=Materialseite+Titel&amp;description=Titel+auf+der+Materialseite+speichern&amp;target_name={html.escape(REPO.split("github.com/", 1)[1].split("/")[0])}&amp;expires_in=none&amp;contents=write" target="_blank" rel="noopener"><strong>Diesen Link öffnen</strong></a>. Fast alles ist schon ausgefüllt. Falls GitHub nach deinem Passwort fragt, gib es ein.</li>
            <li>Nach unten zu <strong>Repository access</strong> gehen, <strong>Only select repositories</strong> anklicken und in der Liste <strong>{html.escape(REPO.rsplit("/", 1)[1])}</strong> auswählen.</li>
            <li>Ganz unten auf den grünen Knopf <strong>Generate token</strong> klicken und im kleinen Fenster noch einmal bestätigen.</li>
            <li>GitHub zeigt jetzt eine lange Zeichenfolge, die mit <code>github_pat_</code> beginnt. Daneben auf das Kopier-Symbol klicken.</li>
            <li>Hierher zurückkommen, die Zeichenfolge in das Feld einfügen und auf <strong>Übernehmen</strong> klicken.</li>
          </ol>
          <div class="input-group input-group-sm">
            <input type="password" class="form-control" id="token-feld" placeholder="Hier einfügen (beginnt mit github_pat_)" autocomplete="off" aria-label="Zeichenfolge von GitHub">
            <button type="button" class="btn btn-primary" id="token-ok">Übernehmen</button>
            <button type="button" class="btn btn-outline-danger" id="token-weg" hidden>Entfernen</button>
          </div>
          <p class="small text-muted mt-2 mb-0">Die Zeichenfolge bleibt nur in diesem Browser gespeichert und erlaubt nur Änderungen an diesem einen Repository. Richte das nur auf deinem eigenen Gerät ein, nicht auf einem Schulgerät, das andere mitbenutzen.</p>
        </details>
      </div>
    </section>

    <div class="mb-4">
      <input type="search" id="suche" class="form-control" placeholder="🔍 In allen Materialien suchen, z. B. Brüche, Redox …" aria-label="Materialien in allen Bereichen durchsuchen">
    </div>

    <section id="start" class="row g-3 mb-4" aria-label="Bereich auswählen">{spalten}
    </section>

    <main id="liste">{karten}
      <p id="nichts" class="text-center text-muted" hidden>Nichts gefunden.</p>
    </main>

    <footer class="text-center text-muted small mt-4">Stand: {stand} · <a class="link-secondary" href="{REPO}#readme">✏️ Seite bearbeiten</a></footer>
  </div>

  <!-- QR-Code zu einer einzelnen Lernumgebung -->
  <dialog id="qr-fenster">
    <h2 class="h5 mb-3" id="qr-titel"></h2>
    <div id="qr-bild"></div>
    <p class="text-muted small mt-3 mb-3" id="qr-adresse"></p>
    <button type="button" class="btn btn-primary" id="qr-schliessen">Schließen</button>
  </dialog>

  <script>
    (function () {{
      const suche = document.getElementById("suche");
      const karten = Array.prototype.slice.call(document.querySelectorAll(".gruppe"));

      /* Zeigt entweder die Startauswahl oder genau einen Bereich. Beim Suchen werden alle Bereiche durchsucht. */
      function anzeigen() {{
        const woerter = suche.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
        const sucht = woerter.length > 0;
        const gewaehlt = decodeURIComponent(location.hash.slice(1));
        const aktiv = sucht ? null : karten.find(function (k) {{ return k.id === gewaehlt; }}) || null;
        let gesamt = 0;
        document.getElementById("start").hidden = sucht || !!aktiv;
        karten.forEach(function (karte) {{
          const gruppe = karte.querySelector(".gruppen-titel").textContent.toLowerCase();
          let sichtbar = 0;
          karte.querySelectorAll(".eintrag").forEach(function (e) {{
            const thema = e.closest(".thema");
            const text = gruppe + " " + (thema ? thema.querySelector(".thema-titel").textContent.toLowerCase() : "") + " " + e.querySelector(".titel").textContent.toLowerCase();
            const passt = woerter.every(function (w) {{ return text.includes(w) || e.dataset.id === w; }});
            e.classList.toggle("d-none", !passt);
            if (passt) sichtbar++;
          }});
          karte.querySelectorAll(".thema").forEach(function (t) {{
            t.hidden = sucht && !t.querySelector(".eintrag:not(.d-none)");
          }});
          karte.querySelector(".zurueck").hidden = sucht;
          karte.hidden = sucht ? sichtbar === 0 : karte !== aktiv;
          if (!karte.hidden) gesamt += sichtbar;
        }});
        document.getElementById("nichts").hidden = !sucht || gesamt > 0;
      }}
      suche.addEventListener("input", anzeigen);
      window.addEventListener("hashchange", function () {{ suche.value = ""; anzeigen(); window.scrollTo(0, 0); }});
      anzeigen();

      /* Kurzlink kopieren */
      const voll = function (url) {{ return new URL(url, location.href).href; }};
      document.querySelectorAll(".kopieren").forEach(function (k) {{
        k.addEventListener("click", function () {{
          const adresse = voll(k.dataset.url), alt = k.textContent;
          const fertig = function () {{ k.textContent = "✓ kopiert"; setTimeout(function () {{ k.textContent = alt; }}, 1500); }};
          if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(adresse).then(fertig, function () {{ prompt("Kurzlink:", adresse); }});
          else prompt("Kurzlink:", adresse);
        }});
      }});

      /* QR-Code zu einer Lernumgebung */
      const fenster = document.getElementById("qr-fenster");
      function zeigen(adresse, titel) {{
        const bild = document.getElementById("qr-bild");
        bild.innerHTML = "";
        new QRCode(bild, {{ text: adresse, width: 512, height: 512, correctLevel: QRCode.CorrectLevel.M }});
        document.getElementById("qr-titel").textContent = titel;
        document.getElementById("qr-adresse").textContent = adresse;
        fenster.showModal();
      }}
      document.querySelectorAll(".qr").forEach(function (k) {{
        k.addEventListener("click", function () {{
          const adresse = voll(k.dataset.url), titel = k.dataset.titel;
          if (window.QRCode) return zeigen(adresse, titel);
          const skript = document.createElement("script");
          skript.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
          skript.onload = function () {{ zeigen(adresse, titel); }};
          document.head.appendChild(skript);
        }});
      }});
      document.getElementById("qr-schliessen").addEventListener("click", function () {{ fenster.close(); }});
      fenster.addEventListener("click", function (e) {{ if (e.target === fenster) fenster.close(); }});

      /* ---------- Überschriften direkt auf der Seite bearbeiten ---------- */
      const REPO_NAME = {repo_name_json}, DATEI = "titel.txt", API = "https://api.github.com/repos/" + REPO_NAME + "/contents/" + DATEI;
      const leiste = document.getElementById("edit-leiste"), meldung = document.getElementById("edit-meldung");
      const tokenLesen = function () {{ try {{ return localStorage.getItem("um-token") || ""; }} catch (e) {{ return ""; }} }};
      const tokenSetzen = function (t) {{ try {{ if (t) localStorage.setItem("um-token", t); else localStorage.removeItem("um-token"); }} catch (e) {{}} }};
      function melden(text, art) {{ meldung.textContent = text; meldung.className = "small mt-2 " + (art === "gut" ? "text-success" : art === "schlecht" ? "text-danger" : "text-muted"); }}
      function tokenAnzeige() {{
        const hat = !!tokenLesen();
        document.getElementById("token-status").textContent = hat ? "✓ Auf diesem Gerät eingerichtet: „Speichern“ erledigt alles mit einem Klick." : "Auf diesem Gerät noch nicht eingerichtet.";
        document.getElementById("einrichten").open = !hat;
        document.getElementById("token-weg").hidden = !hat;
      }}
      function felder() {{ return Array.prototype.slice.call(document.querySelectorAll("input.edit-feld")); }}
      function bearbeitenAn() {{
        suche.value = ""; anzeigen();
        document.querySelectorAll(".edit").forEach(function (s) {{
          const f = document.createElement("input");
          f.type = "text"; f.className = "form-control form-control-sm edit-feld"; f.value = s.textContent; f.dataset.key = s.dataset.key; f.dataset.alt = s.textContent;
          f.setAttribute("aria-label", "Überschrift für " + s.dataset.key);
          f.addEventListener("click", function (e) {{ e.preventDefault(); e.stopPropagation(); }});
          s.hidden = true; s.after(f);
        }});
        document.querySelectorAll(".edit-start").forEach(function (f) {{ f.value = f.dataset.alt; }});
        leiste.hidden = false; document.getElementById("bearbeiten").hidden = true; document.body.classList.add("edit-an");
        document.getElementById("einfuegen").hidden = true; tokenAnzeige();
        melden("Ändere die Überschriften direkt in den Feldern und klicke dann auf Speichern.");
      }}
      function bearbeitenAus(uebernehmen) {{
        document.querySelectorAll("input.edit-feld:not(.edit-start)").forEach(function (f) {{
          const s = f.previousElementSibling;
          if (uebernehmen && f.value.trim()) s.textContent = f.value.trim();
          s.hidden = false; f.remove();
        }});
        if (uebernehmen) document.querySelectorAll(".titel-kopie").forEach(function (k) {{
          const quelle = Array.prototype.slice.call(document.querySelectorAll(".edit")).find(function (s) {{ return s.dataset.key === k.dataset.key; }});
          if (quelle) k.textContent = quelle.textContent;
        }});
        if (uebernehmen) document.querySelectorAll(".edit-start").forEach(function (f) {{ if (f.value.trim()) f.dataset.alt = f.value.trim(); }});
        leiste.hidden = true; document.getElementById("bearbeiten").hidden = false; document.body.classList.remove("edit-an");
      }}
      function aenderungen() {{
        const liste = [];
        felder().forEach(function (f) {{ const v = f.value.trim().replace(/\\s+/g, " "); if (v && v !== f.dataset.alt) liste.push([f.dataset.key, v]); }});
        return liste;
      }}
      /* Trägt die neuen Titel in den Text von titel.txt ein. */
      function eintragen(text, liste) {{
        const zeilen = text.replace(/\\r/g, "").replace(/\\n+$/, "").split("\\n");
        liste.forEach(function (paar) {{
          const neu = paar[0] + " | " + paar[1];
          const i = zeilen.findIndex(function (z) {{ return !z.trim().startsWith("#") && z.indexOf("|") > 0 && z.split("|")[0].trim() === paar[0]; }});
          if (i >= 0) zeilen[i] = neu; else zeilen.push(neu);
        }});
        return zeilen.join("\\n") + "\\n";
      }}
      const zuBase64 = function (text) {{ const b = new TextEncoder().encode(text); let s = ""; for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, i + 8192)); return btoa(s); }};
      const vonBase64 = function (b64) {{ const s = atob(b64.replace(/\\s/g, "")); const b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return new TextDecoder().decode(b); }};

      async function speichern() {{
        const liste = aenderungen();
        if (!liste.length) {{ melden("Du hast nichts geändert."); return; }}
        const knopf = document.getElementById("speichern"); knopf.disabled = true;
        try {{
          const token = tokenLesen();
          if (token) {{
            melden("Speichere …");
            const kopf = {{ "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json" }};
            const a = await fetch(API + "?ref=main&t=" + Date.now(), {{ headers: kopf, cache: "no-store" }});
            if (a.status === 401 || a.status === 403) throw new Error("Der Zugangsschlüssel wird von GitHub nicht angenommen. Bitte richte das direkte Speichern neu ein.");
            if (!a.ok) throw new Error("GitHub antwortet mit Fehler " + a.status + ".");
            const daten = await a.json();
            const b = await fetch(API, {{ method: "PUT", headers: kopf, body: JSON.stringify({{ message: "Überschriften geändert (" + liste.length + ")", content: zuBase64(eintragen(vonBase64(daten.content), liste)), sha: daten.sha, branch: "main" }}) }});
            if (b.status === 401 || b.status === 403 || b.status === 404) throw new Error("Der Zugangsschlüssel darf nicht in dieses Repository schreiben. Er braucht das Recht „Contents: Read and write“.");
            if (!b.ok) throw new Error("Speichern fehlgeschlagen (Fehler " + b.status + "). Bitte versuche es noch einmal.");
            bearbeitenAus(true);
            document.getElementById("edit-fertig").textContent = "✓ Gespeichert (" + liste.length + (liste.length === 1 ? " Überschrift" : " Überschriften") + "). In etwa 2 Minuten ist die Änderung fest auf der Seite. Wenn du vorher neu lädst, siehst du kurz noch den alten Stand.";
            document.getElementById("edit-fertig").hidden = false;
          }} else {{
            melden("Bereite vor …");
            const a = await fetch("https://raw.githubusercontent.com/" + REPO_NAME + "/main/" + DATEI + "?t=" + Date.now(), {{ cache: "no-store" }});
            if (!a.ok) throw new Error("Die Datei titel.txt konnte nicht geladen werden (Fehler " + a.status + ").");
            const neu = eintragen(await a.text(), liste);
            document.getElementById("einfuegen-text").value = neu;
            let kopiert = false;
            try {{ await navigator.clipboard.writeText(neu); kopiert = true; }} catch (e) {{}}
            document.getElementById("einfuegen-hinweis").textContent = kopiert ? "Der neue Inhalt ist schon kopiert." : "Markiere den Text im Feld unten und kopiere ihn.";
            document.getElementById("einfuegen").hidden = false;
            melden("Noch ein Schritt bei GitHub, siehe unten. Nach der einmaligen Einrichtung weiter unten entfällt er.");
          }}
        }} catch (e) {{ melden(e.message || String(e), "schlecht"); }}
        knopf.disabled = false;
      }}
      document.getElementById("bearbeiten").addEventListener("click", function () {{ document.getElementById("edit-fertig").hidden = true; bearbeitenAn(); }});
      document.getElementById("abbrechen").addEventListener("click", function () {{ bearbeitenAus(false); }});
      document.getElementById("speichern").addEventListener("click", speichern);
      document.getElementById("einfuegen-fertig").addEventListener("click", function () {{ bearbeitenAus(true); }});
      document.getElementById("token-ok").addEventListener("click", function () {{
        const f = document.getElementById("token-feld"), t = f.value.trim();
        if (!t) return;
        if (!/^(github_pat_|ghp_)/.test(t)) {{ melden("Das sieht nicht nach der Zeichenfolge von GitHub aus. Sie beginnt mit github_pat_.", "schlecht"); return; }}
        tokenSetzen(t); f.value = ""; tokenAnzeige(); document.getElementById("einfuegen").hidden = true; melden("Eingerichtet. Ab jetzt speichert der Knopf „Speichern“ alles mit einem Klick.", "gut");
      }});
      document.getElementById("token-weg").addEventListener("click", function () {{ tokenSetzen(""); tokenAnzeige(); melden("Der Zugangsschlüssel wurde von diesem Gerät entfernt."); }});
    }})();
  </script>
</body>
</html>
"""

startseite = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>{html.escape(START_TITEL)}</title>
  <script>
    /* Kurzlinks wie bisher: ?id=12 öffnet direkt die Datei, die mit "12-" beginnt. */
    (function () {{
      const ids = {id_json};
      const id = new URLSearchParams(location.search).get("id");
      if (id && ids[id]) location.replace(ids[id]);
    }})();
  </script>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #121620; color: #e7ebf3; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; text-align: center; padding: 24px; }}
    h1 {{ font-size: 1.8rem; margin: 0 0 .5rem; color: #ff6fb5; }}
    p {{ font-size: 1.1rem; max-width: 34ch; margin: 0 auto; line-height: 1.5; }}
    .bild {{ font-size: 3.5rem; }}
  </style>
</head>
<body>
  <main>
    <div class="bild" aria-hidden="true">📚</div>
    <h1>{html.escape(START_TITEL)}</h1>
    <p>{html.escape(START_TEXT)}</p>
  </main>
</body>
</html>
"""


# ---------- Übersicht mit Passwort schützen ----------
# Die Übersicht wird verschlüsselt veröffentlicht. Zum Entschlüsseln braucht man das Passwort:
# Es entsperrt den privaten Schlüssel in .lehrkraft/schluessel.json (dort nur verschlüsselt gespeichert).
def uebersicht_verschluesseln(inhalt):
    pfad = os.path.join(".lehrkraft", "schluessel.json")
    if not os.path.isfile(pfad):
        return inhalt
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "cryptography"])
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    import base64
    with open(pfad, encoding="utf-8") as f:
        sch = json.load(f)
    oeffentlich = serialization.load_der_public_key(base64.b64decode(sch["pub"]))
    k = os.urandom(32)
    iv = os.urandom(12)
    geheim = AESGCM(k).encrypt(iv, inhalt.encode("utf-8"), None)
    ek = oeffentlich.encrypt(k, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b = lambda x: base64.b64encode(x).decode()
    daten = json.dumps({"salt": sch["salt"], "iv": sch["iv"], "priv": sch["priv"], "ek": b(ek), "iv2": b(iv), "ct": b(geheim)})
    return LOGIN_SEITE.replace("__DATEN__", daten)

LOGIN_SEITE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="robots" content="noindex, nofollow">
<title>Übersicht – Anmeldung</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#121620;color:#e7ebf3;
background-image:linear-gradient(rgba(46,58,85,.35) 1px,transparent 1px),linear-gradient(90deg,rgba(46,58,85,.35) 1px,transparent 1px);background-size:22px 22px}
form{background:#1c2232;border-top:4px solid #d6267f;border-radius:12px;padding:24px;box-shadow:0 4px 14px rgba(0,0,0,.35);width:min(92vw,360px)}
h1{font-size:1.3rem;margin:0 0 14px}input[type=password]{width:100%;box-sizing:border-box;font:inherit;padding:10px;border-radius:8px;border:1px solid #2e3a55;background:#161b29;color:#e7ebf3;margin-bottom:10px}
button{width:100%;font:inherit;font-weight:700;padding:10px;border-radius:8px;border:none;background:#d6267f;color:#fff;cursor:pointer}
label.m{display:flex;gap:8px;align-items:center;font-size:.9rem;color:#a4aec3;margin-bottom:12px}p.e{color:#ff8a84;min-height:1.2em;margin:10px 0 0}
</style></head><body>
<form id="f"><h1>🔒 Übersicht</h1><input type="password" id="pw" placeholder="Passwort" autocomplete="current-password" autofocus aria-label="Passwort">
<label class="m"><input type="checkbox" id="merk"> Auf diesem Gerät merken</label><button>Öffnen</button><p class="e" id="e" aria-live="polite"></p></form>
<script>
const D=__DATEN__;const b=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function auf(pw){const k0=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]);
 const w=await crypto.subtle.deriveKey({name:"PBKDF2",salt:b(D.salt),iterations:250000,hash:"SHA-256"},k0,{name:"AES-GCM",length:256},false,["decrypt"]);
 const priv=await crypto.subtle.decrypt({name:"AES-GCM",iv:b(D.iv)},w,b(D.priv));
 const rk=await crypto.subtle.importKey("pkcs8",priv,{name:"RSA-OAEP",hash:"SHA-256"},false,["decrypt"]);
 const k=await crypto.subtle.decrypt({name:"RSA-OAEP"},rk,b(D.ek));
 const ak=await crypto.subtle.importKey("raw",k,"AES-GCM",false,["decrypt"]);
 return new TextDecoder().decode(await crypto.subtle.decrypt({name:"AES-GCM",iv:b(D.iv2)},ak,b(D.ct)))}
async function los(pw,merken){let h;try{h=await auf(pw)}catch(x){document.getElementById("e").textContent="Das Passwort stimmt nicht.";try{localStorage.removeItem("ue-pw")}catch(y){}return}
 try{sessionStorage.setItem("ue-pw",pw);if(merken)localStorage.setItem("ue-pw",pw)}catch(y){}
 document.open();document.write(h);document.close()}
document.getElementById("f").onsubmit=e=>{e.preventDefault();los(document.getElementById("pw").value,document.getElementById("merk").checked)};
let g="";try{g=localStorage.getItem("ue-pw")||sessionStorage.getItem("ue-pw")||""}catch(x){}
if(g)los(g,false);
</script></body></html>"""

# ---------- Seite zusammenbauen ----------
shutil.rmtree(AUSGABE, ignore_errors=True)
os.makedirs(os.path.join(AUSGABE, UEBERSICHT))

with open(os.path.join(AUSGABE, "index.html"), "w", encoding="utf-8") as f:
    f.write(startseite)
with open(os.path.join(AUSGABE, UEBERSICHT, "index.html"), "w", encoding="utf-8") as f:
    f.write(uebersicht_verschluesseln(uebersicht))
# Codes-Dokument für Lehrkräfte (verschlüsselt, Passwort nötig) liegt neben der Übersicht.
if os.path.isfile(os.path.join(".lehrkraft", "codes.html")):
    shutil.copyfile(os.path.join(".lehrkraft", "codes.html"), os.path.join(AUSGABE, UEBERSICHT, "codes.html"))

# Lose Dateien im Hauptordner bleiben unter ihrer bisherigen Adresse erreichbar.
for name in os.listdir("."):
    if os.path.isfile(name) and not name.startswith(".") and name not in NICHT_VEROEFFENTLICHEN:
        shutil.copyfile(name, os.path.join(AUSGABE, name))

for e in alle_dateien:
    quelle = e["quelle"]
    shutil.copyfile(quelle, os.path.join(AUSGABE, e["kurz"]))  # Kurzlink

# Auf GitHub wird nur der Inhalt von _site veröffentlicht: Die Ordner mit den Originalen,
# dieses Skript und die Anleitung gehören nicht auf die Internetseite.
if os.environ.get("GITHUB_ACTIONS") == "true":
    for name in os.listdir("."):
        if name in (".git", ".github", AUSGABE):
            continue
        shutil.rmtree(name) if os.path.isdir(name) else os.remove(name)
    for name in os.listdir(AUSGABE):
        shutil.move(os.path.join(AUSGABE, name), name)
    os.rmdir(AUSGABE)

print(f"Seite erstellt: {len(alle_dateien)} Materialien mit Kurzlink, {len(gruppen)} Gruppen in {len(belegte_faecher)} Fächern.")
print(f"Übersicht: {UEBERSICHT}/")
