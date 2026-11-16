# Baut die Internetseite automatisch aus den Ordnern.
# Dieses Skript läuft bei jeder Änderung von selbst auf GitHub – du musst nichts daran ändern.
#
# Was dabei entsteht:
#   …/Unterrichtsmaterial/                     -> neutrale Startseite ohne Materialliste
#   …/Unterrichtsmaterial/<kurzname>.html      -> jede Lernumgebung unter einem kurzen Link (für die Klasse)
#   …/Unterrichtsmaterial/<UEBERSICHT>/        -> die Übersicht aller Materialien (nur für Lehrkräfte)
#
# Wer einen Link zu einer einzelnen Lernumgebung bekommt, kommt von dort nicht zur Übersicht:
# Die Startseite zeigt keine Liste, und die Ordner selbst werden nicht veröffentlicht.
#
#   Ordner auf oberster Ebene   -> eine Gruppe (z. B. "Mathematik 5", "Chemie Oberstufe")
#   Anfang des Ordnernamens     -> das Fach    ("Mathe…" = Mathematik, "Chemie…" = Chemie, sonst "Weitere Fächer")
#   Unterordner darin           -> ein Thema   (z. B. "Mathematik 6/Bruchrechnung")
#   Dateien                     -> Einträge (HTML, PDF, Word, PowerPoint, Excel, Bilder)
#   links.txt                   -> Links ins Internet, eine Zeile pro Link:  Titel | https://...
#   kurzlinks.txt               -> Kurznamen, eine Zeile pro Datei:  kurzname | Ordner/Dateiname
#                                  Fehlt eine Datei dort, wird der Kurzname aus dem Dateinamen gebildet.
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
REPO = "https://github.com/hubi-bot/Unterrichtsmaterial"
UEBERSICHT = "uebersicht-x4brac"  # Ordnername der Übersicht; nicht an Schüler weitergeben
AUSGABE = "_site"

# Fächer in der Reihenfolge des Umschalters: (Kürzel, Name, Symbol, Ordner-Anfänge in Kleinbuchstaben)
FAECHER = [
    ("mathematik", "Mathematik", "📐", ("mathe",)),
    ("chemie", "Chemie", "🧪", ("chemie",)),
    ("weitere", "Weitere Fächer", "🗂️", ()),  # alles andere
]

AUSGESCHLOSSEN = {".git", ".github", AUSGABE}
NICHT_VEROEFFENTLICHEN = {"generate_index.py", "README.md", "kurzlinks.txt", "index.html", ".gitignore"}
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
            if "|" in zeile:
                titel, url = (t.strip() for t in zeile.split("|", 1))
            else:
                titel, url = zeile, zeile
            if url.startswith(("http://", "https://")):
                eintraege.append({"titel": titel, "url": url, "typ": "Link", "extern": True})
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
            for unter_name, unter_e in t:  # tiefere Ebenen unter dem Thema einsortieren
                e += unter_e
            e += l  # Links eines Themas stehen am Ende des Themas
            if e:
                themen.append((anzeigename(name), e))
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
            eintraege.append({"titel": anzeigename(name), "kurz": kurz, "quelle": pfad, "typ": TYPEN[endung], "extern": False, "id": nummer})
    return eintraege, themen, links


def eintrag_html(e):
    symbol = "🔗" if e["typ"] == "Link" else SYMBOL.get(e["typ"], "📎")
    titel = html.escape(e["titel"])
    if e["typ"] == "Link":
        url, knopf, farbe, ziel, extras = e["url"], "Öffnen", "text-bg-success", 'target="_blank" rel="noopener"', ""
    else:
        url = "../" + quote(e["kurz"])
        if ist_download(e):
            knopf, farbe, ziel = f"⬇ {e['typ']}", "text-bg-warning", "download"
        else:
            knopf, farbe, ziel = "Ansehen", "text-bg-primary", 'target="_blank" rel="noopener"'
        extras = (
            f'<button type="button" class="btn btn-sm btn-outline-secondary kopieren" data-url="{html.escape(url)}" title="Kurzlink kopieren" aria-label="Kurzlink zu {titel} kopieren">🔗 Link</button>'
            f'<button type="button" class="btn btn-sm btn-outline-secondary qr" data-url="{html.escape(url)}" data-titel="{titel}" title="QR-Code zeigen" aria-label="QR-Code zu {titel} zeigen">QR</button>'
        )
    nummer = f'<span class="badge text-bg-secondary me-1">ID {html.escape(e["id"])}</span>' if e.get("id") else ""
    return f"""
          <div class="list-group-item d-flex flex-wrap justify-content-between align-items-center gap-2 eintrag" data-id="{html.escape(e.get('id') or '')}">
            <a href="{html.escape(url)}" {ziel} class="flex-grow-1 text-decoration-none text-body titel">{nummer}{symbol} {titel}</a>
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
        for _, liste in themen:
            alle_dateien += [e for e in liste if not e["extern"]]
        downloads = [e for e in eintraege if ist_download(e)]
        eintraege = [e for e in eintraege if not ist_download(e)]
        if downloads:  # Download-Dateien der Gruppe als eigener Abschnitt
            themen.append(("Downloads", downloads))
        if links:  # Links der Gruppe kommen als eigener Abschnitt ans Ende
            themen.append(("Links", links))
        gruppen.append((fach_von(name), name, eintraege, themen))

reihenfolge = {k: i for i, (k, _, _, _) in enumerate(FAECHER)}
gruppen.sort(key=lambda g: (reihenfolge[g[0]], gruppenschluessel(g[1])))
belegte_faecher = [f for f in FAECHER if any(g[0] == f[0] for g in gruppen)]

fachknoepfe = ""
for kuerzel, fachname, symbol, _ in belegte_faecher:
    anzahl = sum(1 for g in gruppen if g[0] == kuerzel)
    fachknoepfe += (
        f'<button type="button" class="btn btn-outline-primary fach-knopf" role="tab" data-fach="{kuerzel}" '
        f'aria-selected="false" title="{anzahl} Gruppen">{symbol} {html.escape(fachname)}</button>\n'
    )

karten = ""
knoepfe = ""
for nr, (fach, ordnername, eintraege, themen) in enumerate(gruppen):
    gruppe = anzeigename(ordnername)
    anker = f"g{nr}"
    knoepfe += f'<a class="btn btn-outline-primary btn-sm gruppen-knopf" data-fach="{fach}" href="#{anker}">{html.escape(gruppe)}</a>\n'
    inhalt = ""
    if eintraege:
        inhalt += '<div class="list-group list-group-flush mb-2">' + "".join(eintrag_html(e) for e in eintraege) + "</div>"
    for thema, e in themen:
        inhalt += f'<div class="thema"><h4 class="h6 thema-titel">{html.escape(thema)}</h4><div class="list-group list-group-flush">' + "".join(eintrag_html(x) for x in e) + "</div></div>"
    if not inhalt:
        inhalt = '<p class="text-muted mb-0">Noch keine Materialien.</p>'
    karten += f"""
    <section class="card gruppe" id="{anker}" data-fach="{fach}">
      <div class="card-body">
        <h2 class="h4 gruppen-titel">📂 {html.escape(gruppe)}</h2>
        {inhalt}
      </div>
    </section>"""

stand = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y, %H:%M Uhr")
faecher_json = json.dumps([f[0] for f in belegte_faecher])
id_json = json.dumps(id_karte, ensure_ascii=False)

uebersicht = f"""<!DOCTYPE html>
<html lang="de">
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
    .fach-leiste {{ display: flex; flex-wrap: wrap; justify-content: center; gap: .5rem; margin-bottom: 1.25rem; }}
    .fach-knopf {{ font-size: 1.1rem; font-weight: 600; padding: .55rem 1.3rem; border-width: 2px; border-radius: 999px; background: #fff; }}
    .fach-knopf[aria-selected="true"] {{ background: #0d6efd; color: #fff; }}
    #qr-fenster {{ border: none; border-radius: 1rem; padding: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,.25); text-align: center; max-width: 92vw; }}
    #qr-fenster::backdrop {{ background: rgba(0,0,0,.5); }}
    #qr-bild img, #qr-bild canvas {{ margin: 0 auto; width: min(70vw, 320px); height: auto; }}
    #qr-adresse {{ overflow-wrap: anywhere; user-select: all; }}
  </style>
</head>
<body>
  <div class="container" style="max-width: 900px">
    <header class="text-center mb-4">
      <h1 class="display-6 fw-bold">📚 {html.escape(SEITENTITEL)}</h1>
      <p class="lead text-muted">{html.escape(UNTERTITEL)}</p>
    </header>

    <div class="fach-leiste" role="tablist" aria-label="Fach wählen">
      {fachknoepfe}
    </div>

    <div class="mb-3">
      <input type="search" id="suche" class="form-control form-control-lg" placeholder="🔍 Suchen, z. B. Brüche, Redox, Klasse 10 …" aria-label="Materialien in allen Fächern durchsuchen">
    </div>
    <nav class="d-flex flex-wrap gap-2 justify-content-center mb-4" id="gruppen-leiste">
      {knoepfe}
    </nav>

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
      const faecher = {faecher_json};
      const suche = document.getElementById("suche");
      let fach = faecher[0];

      function merken(wert) {{ try {{ localStorage.setItem("um-fach", wert); }} catch (e) {{}} }}
      function gemerkt() {{ try {{ return localStorage.getItem("um-fach"); }} catch (e) {{ return null; }} }}

      /* Zeigt die Gruppen des gewählten Fachs. Beim Suchen werden alle Fächer durchsucht. */
      function anzeigen() {{
        const woerter = suche.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
        const sucht = woerter.length > 0;
        let gesamt = 0;
        document.querySelectorAll(".fach-knopf").forEach(function (k) {{
          k.setAttribute("aria-selected", !sucht && k.dataset.fach === fach ? "true" : "false");
        }});
        document.querySelectorAll(".gruppen-knopf").forEach(function (k) {{
          k.hidden = sucht || k.dataset.fach !== fach;
        }});
        document.querySelectorAll(".gruppe").forEach(function (karte) {{
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
          karte.hidden = sucht ? sichtbar === 0 : karte.dataset.fach !== fach;
          if (!karte.hidden) gesamt += sichtbar;
        }});
        document.getElementById("nichts").hidden = !sucht || gesamt > 0;
      }}

      function waehlen(neu, adresseAendern) {{
        if (!faecher.includes(neu)) return;
        fach = neu;
        merken(neu);
        if (adresseAendern) history.replaceState(null, "", "#" + neu);
        anzeigen();
      }}

      document.querySelectorAll(".fach-knopf").forEach(function (k) {{
        k.addEventListener("click", function () {{ suche.value = ""; waehlen(k.dataset.fach, true); }});
      }});
      suche.addEventListener("input", anzeigen);
      window.addEventListener("hashchange", function () {{ waehlen(location.hash.slice(1), false); }});

      /* Start: Fach aus der Adresse (z. B. …/#chemie), sonst das zuletzt gewählte, sonst das erste. */
      const ausAdresse = location.hash.slice(1);
      waehlen(faecher.includes(ausAdresse) ? ausAdresse : (faecher.includes(gemerkt()) ? gemerkt() : faecher[0]), false);

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
  <title>Lernmaterial von Frau Huber</title>
  <script>
    /* Kurzlinks wie bisher: ?id=12 öffnet direkt die Datei, die mit "12-" beginnt. */
    (function () {{
      const ids = {id_json};
      const id = new URLSearchParams(location.search).get("id");
      if (id && ids[id]) location.replace(ids[id]);
    }})();
  </script>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f8f9fa; color: #343a40; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; text-align: center; padding: 24px; }}
    h1 {{ font-size: 1.8rem; margin: 0 0 .5rem; }}
    p {{ font-size: 1.1rem; max-width: 34ch; margin: 0 auto; line-height: 1.5; }}
    .bild {{ font-size: 3.5rem; }}
  </style>
</head>
<body>
  <main>
    <div class="bild" aria-hidden="true">📚</div>
    <h1>Lernmaterial von Frau Huber</h1>
    <p>Öffne bitte den Link oder scanne den QR-Code, den du im Unterricht bekommen hast.</p>
  </main>
</body>
</html>
"""

# ---------- Seite zusammenbauen ----------
shutil.rmtree(AUSGABE, ignore_errors=True)
os.makedirs(os.path.join(AUSGABE, UEBERSICHT))

with open(os.path.join(AUSGABE, "index.html"), "w", encoding="utf-8") as f:
    f.write(startseite)
with open(os.path.join(AUSGABE, UEBERSICHT, "index.html"), "w", encoding="utf-8") as f:
    f.write(uebersicht)

# Lose Dateien im Hauptordner bleiben unter ihrer bisherigen Adresse erreichbar.
for name in os.listdir("."):
    if os.path.isfile(name) and not name.startswith(".") and name not in NICHT_VEROEFFENTLICHEN:
        shutil.copyfile(name, os.path.join(AUSGABE, name))

for e in alle_dateien:
    quelle = e["quelle"]
    shutil.copyfile(quelle, os.path.join(AUSGABE, e["kurz"]))  # Kurzlink
    alt = os.path.join(AUSGABE, quelle)  # bisherige lange Adresse
    os.makedirs(os.path.dirname(alt), exist_ok=True)
    if quelle.lower().endswith((".html", ".htm")):
        hoch = "../" * quelle.count("/")
        with open(alt, "w", encoding="utf-8") as f:
            f.write(weiterleitung_html(hoch + quote(e["kurz"]), e["titel"]))
    else:
        shutil.copyfile(quelle, alt)

for pfad in weiterleitungen:  # vorhandene Weiterleitungen unverändert übernehmen
    ziel = os.path.join(AUSGABE, pfad)
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    shutil.copyfile(pfad, ziel)

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
