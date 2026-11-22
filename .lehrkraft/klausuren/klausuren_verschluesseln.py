#!/usr/bin/env python3
"""Klausuren verschlüsselt ablegen (Bereich „Klausuren“ auf der Materialseite).

Neu anlegen:   python3 klausuren_verschluesseln.py neu
Hinzufügen:    python3 klausuren_verschluesseln.py add DATEI --fach Mathematik --klasse 12 --titel "Klausur 1"
Entfernen:     python3 klausuren_verschluesseln.py weg ID
Liste:         python3 klausuren_verschluesseln.py liste
Das Passwort wird abgefragt (oder aus der Umgebungsvariable KLAUSUR_PW gelesen).
Im Repository liegen nur verschlüsselte Daten (AES-GCM, Schlüssel aus dem Passwort per PBKDF2).
"""
import os, sys, json, base64, getpass, argparse, mimetypes, datetime, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.path.join(HIER, "daten.json"); ORDNER = os.path.join(HIER, "dateien")
b = lambda x: base64.b64encode(x).decode(); u = base64.b64decode
def schluessel(pw, salt): return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=250000).derive(pw.encode())
def pw(): return os.environ.get("KLAUSUR_PW") or getpass.getpass("Passwort: ")
def laden(p):
    d = json.load(open(DATEN)); k = schluessel(p, u(d["salt"]))
    return k, d["salt"], json.loads(AESGCM(k).decrypt(u(d["iv"]), u(d["ct"]), None))
def speichern(k, salt, liste):
    iv = os.urandom(12)
    json.dump({"salt": salt, "iv": b(iv), "ct": b(AESGCM(k).encrypt(iv, json.dumps(liste, ensure_ascii=False).encode(), None))}, open(DATEN, "w"))
a = argparse.ArgumentParser(); a.add_argument("aktion"); a.add_argument("datei", nargs="?")
a.add_argument("--fach", default=""); a.add_argument("--klasse", default=""); a.add_argument("--titel", default="")
z = a.parse_args(); os.makedirs(ORDNER, exist_ok=True)
if z.aktion == "neu":
    salt = os.urandom(16); speichern(schluessel(pw(), salt), b(salt), []); print("leer angelegt")
elif z.aktion == "add":
    k, salt, liste = laden(pw()); roh = open(z.datei, "rb").read(); iv = os.urandom(12); i = secrets.token_hex(8)
    open(os.path.join(ORDNER, i + ".bin"), "wb").write(AESGCM(k).encrypt(iv, roh, None))
    liste.append({"id": i, "fach": z.fach, "kl": z.klasse, "titel": z.titel or os.path.basename(z.datei), "name": os.path.basename(z.datei),
                  "mime": mimetypes.guess_type(z.datei)[0] or "application/octet-stream", "iv": b(iv), "datum": datetime.date.today().isoformat()})
    speichern(k, salt, liste); print("hinzugefügt:", i)
elif z.aktion == "weg":
    k, salt, liste = laden(pw()); liste = [e for e in liste if e["id"] != z.datei]
    p = os.path.join(ORDNER, z.datei + ".bin"); os.path.exists(p) and os.remove(p); speichern(k, salt, liste); print("entfernt")
elif z.aktion == "liste":
    for e in laden(pw())[2]: print(e["id"], e["fach"], e["kl"], e["titel"], e["name"])
