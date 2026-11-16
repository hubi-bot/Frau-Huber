# Baut die Startseite (index.html) automatisch aus den Ordnern.
# Dieses Skript läuft bei jeder Änderung von selbst auf GitHub – du musst nichts daran ändern.
# Aufbau und Aussehen wie bei https://mathe-materialien.github.io/Unterrichtsmaterialien/,
# erweitert um den Fach-Umschalter (Mathematik / Chemie / Weitere Fächer).
#
#   Ordner auf oberster Ebene   -> eine Gruppe (z. B. "Mathematik 5", "Chemie Oberstufe")
#   Anfang des Ordnernamens     -> das Fach    ("Mathe…" = Mathematik, "Chemie…" = Chemie, sonst "Weitere Fächer")
#   Unterordner darin           -> ein Thema   (z. B. "Mathematik 6/Bruchrechnung")
#   Dateien                     -> Einträge (HTML, PDF, Word, PowerPoint, Excel, Bilder)
#   links.txt                   -> Links ins Internet, eine Zeile pro Link:  Titel | https://...
#
# Dateien, die der Browser nicht selbst anzeigen kann (GeoGebra, Word, PowerPoint, Excel, ZIP …),
# bekommen einen Knopf "Herunterladen". Liegen sie direkt im Gruppen-Ordner, stehen sie
# gesammelt im Abschnitt "Downloads" (vor den Links).
#
# Eine Zahl vorne im Namen bestimmt die Reihenfolge und wird nicht angezeigt:
#   "1 Natürliche Zahlen", "2 Geometrie"  ->  "Natürliche Zahlen", "Geometrie"
#
# Weiterleitungen: Eine HTML-Datei, die <meta name="weiterleitung" ...> enthält, leitet nur auf eine
# neuere Fassung um. Sie bleibt erreichbar (alte Links und QR-Codes funktionieren weiter),
# erscheint aber nicht in der Übersicht.

import html
import json
import os
import re
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

SEITENTITEL = "Unterrichtsmaterialien"
UNTERTITEL = "Arbeitsblätter, Lernumgebungen und Links"
REPO = "https://github.com/hubi-bot/Unterrichtsmaterial"

# Fächer in der Reihenfolge des Umschalters: (Kürzel, Name, Symbol, Ordner-Anfänge in Kleinbuchstaben)
FAECHER = [
    ("mathematik", "Mathematik", "📐", ("mathe",)),
    ("chemie", "Chemie", "🧪", ("chemie",)),
    ("weitere", "Weitere Fächer", "🗂️", ()),  # alles andere
]

AUSGESCHLOSSEN = {".git", ".github"}
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


def ordner_lesen(ordner):
    """Liefert (eintraege, themen, links) für einen Ordner."""
    eintraege, themen, links = [], [], []
    for name in sorted(os.listdir(ordner), key=lambda n: sortierschluessel(os.path.splitext(n)[0])):
        pfad = os.path.join(ordner, name)
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
                continue
            url = quote(pfad.replace(os.sep, "/").removeprefix("./"))
            nummer = kennnummer(name)
            if nummer:
                id_karte.setdefault(nummer, url)
            eintraege.append({"titel": anzeigename(name), "url": url, "typ": TYPEN[endung], "extern": False, "id": nummer})
    return eintraege, themen, links


def eintrag_html(e):
    symbol = "🔗" if e["typ"] == "Link" else SYMBOL.get(e["typ"], "📎")
    if e["typ"] == "Link":
        knopf, farbe, ziel = "Öffnen", "text-bg-success", 'target="_blank" rel="noopener"'
    elif ist_download(e):
        knopf, farbe, ziel = f"⬇ {e['typ']}", "text-bg-warning", "download"
    else:
        knopf, farbe, ziel = "Ansehen", "text-bg-primary", 'target="_blank" rel="noopener"'
    nummer = f'<span class="badge text-bg-secondary me-1">ID {html.escape(e["id"])}</span>' if e.get("id") else ""
    return f"""
          <a href="{html.escape(e['url'])}" {ziel} class="list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-3 eintrag" data-id="{html.escape(e.get('id') or '')}">
            <span>{nummer}{symbol} {html.escape(e['titel'])}</span>
            <span class="badge rounded-pill {farbe}">{html.escape(knopf)}</span>
          </a>"""


# ---------- Ordner einlesen ----------
gruppen = []  # (fach, anzeigename, eintraege, themen)
for name in os.listdir("."):
    if os.path.isdir(name) and name not in AUSGESCHLOSSEN and not name.startswith("."):
        eintraege, themen, links = ordner_lesen(name)
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

seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(SEITENTITEL)}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <script>
    /* Kurzlinks wie bisher: index.html?id=12 öffnet direkt die Datei, die mit "12-" beginnt. */
    (function () {{
      const ids = {id_json};
      const id = new URLSearchParams(location.search).get("id");
      if (id && ids[id]) location.replace(ids[id]);
    }})();
  </script>
  <style>
    body {{ background-color: #f8f9fa; padding: 2rem 0; }}
    .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1.5rem; scroll-margin-top: 1rem; }}
    .gruppen-titel {{ border-bottom: 2px solid #0d6efd; padding-bottom: .5rem; color: #495057; margin-bottom: 1rem; }}
    .thema {{ margin-top: 1rem; }}
    .thema-titel {{ color: #0d6efd; text-transform: uppercase; letter-spacing: .04em; font-size: .8rem; font-weight: 700; margin-bottom: .25rem; }}
    .list-group-item:hover {{ background-color: #f1f3f5; }}
    .fach-leiste {{ display: flex; flex-wrap: wrap; justify-content: center; gap: .5rem; margin-bottom: 1.25rem; }}
    .fach-knopf {{ font-size: 1.1rem; font-weight: 600; padding: .55rem 1.3rem; border-width: 2px; border-radius: 999px; background: #fff; }}
    .fach-knopf[aria-selected="true"] {{ background: #0d6efd; color: #fff; }}
    #qr-knopf {{ cursor: pointer; }}
    #qr-fenster {{ border: none; border-radius: 1rem; padding: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,.25); text-align: center; }}
    #qr-fenster::backdrop {{ background: rgba(0,0,0,.5); }}
    #qr-bild img, #qr-bild canvas {{ margin: 0 auto; width: min(70vw, 320px); height: auto; }}
  </style>
</head>
<body>
  <div class="container" style="max-width: 900px">
    <header class="text-center mb-4">
      <h1 class="display-6 fw-bold"><span id="qr-knopf" title="QR-Code zu dieser Seite zeigen">📚</span> {html.escape(SEITENTITEL)}</h1>
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

  <!-- Verstecktes Extra: Klick auf 📚 öffnet einen QR-Code zu dieser Seite (mit dem gewählten Fach) -->
  <dialog id="qr-fenster">
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
            const text = gruppe + " " + (thema ? thema.querySelector(".thema-titel").textContent.toLowerCase() : "") + " " + e.textContent.toLowerCase();
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

      /* QR-Code */
      const fenster = document.getElementById("qr-fenster");
      function zeigen() {{
        const adresse = location.origin + location.pathname.replace(/index\\.html$/, "") + "#" + fach;
        const bild = document.getElementById("qr-bild");
        bild.innerHTML = "";
        new QRCode(bild, {{ text: adresse, width: 512, height: 512, correctLevel: QRCode.CorrectLevel.M }});
        document.getElementById("qr-adresse").textContent = adresse;
        fenster.showModal();
      }}
      document.getElementById("qr-knopf").addEventListener("click", function () {{
        if (window.QRCode) return zeigen();
        const skript = document.createElement("script");
        skript.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
        skript.onload = zeigen;
        document.head.appendChild(skript);
      }});
      document.getElementById("qr-schliessen").addEventListener("click", function () {{ fenster.close(); }});
      fenster.addEventListener("click", function (e) {{ if (e.target === fenster) fenster.close(); }});
    }})();
  </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(seite)
print(f"index.html erstellt: {len(gruppen)} Gruppen in {len(belegte_faecher)} Fächern.")
