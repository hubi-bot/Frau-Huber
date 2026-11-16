# ✏️ Anleitung: So pflegst du die Materialseite

**Übersicht für Lehrkräfte:** https://hubi-bot.github.io/Frau-Huber/uebersicht-x4brac/

Diese Adresse bitte nicht an Schülerinnen und Schüler weitergeben. Für die Klasse gibt es zu jeder Lernumgebung einen eigenen **Kurzlink**, zum Beispiel `https://hubi-bot.github.io/Frau-Huber/bruch-mal`. Von dort kommt man nicht zur Übersicht: Die Startseite zeigt keine Materialliste.

In der Übersicht steht neben jedem Material **🔗 Link** (kopiert den Kurzlink) und **QR** (zeigt einen QR-Code zu genau diesem Material).

> **Vorher:** Oben rechts muss dein Profilbild zu sehen sein. Steht dort **Sign in**, klick darauf und melde dich an.

---

## So funktioniert die Seite

| Hier bei GitHub …               | … wird auf der Seite zu         |
|---------------------------------|---------------------------------|
| ein Ordner, z. B. `Mathematik 5` oder `Chemie Oberstufe` | ein Kasten mit Überschrift |
| der Anfang des Ordnernamens | das Fach: `Mathe…` steht unter **Mathematik**, `Chemie…` unter **Chemie**, alles andere unter **Weitere Fächer** |
| ein Ordner im Ordner, z. B. `Bruchrechnung` | eine blaue Zwischenüberschrift im Kasten |
| eine Datei, z. B. `Brüche kürzen.pdf` | ein Eintrag „Brüche kürzen“ mit **Ansehen** |
| eine Zeile in `links.txt`       | ein Internet-Link mit **Öffnen** |
| eine GeoGebra-, Word-, PowerPoint- oder Excel-Datei | ein Eintrag unter **Downloads** mit **⬇ Herunterladen** |

**Nach jeder Änderung 2 Minuten warten**, dann die Seite neu laden. Erst dann ist die Änderung zu sehen.

**Keine Angst:** GitHub merkt sich jede Änderung, und alles lässt sich wieder rückgängig machen.

---

## 📄 Ein Material hinzufügen

1. **Datei vorher passend benennen.** Der Dateiname wird zum Titel auf der Seite. Also zum Beispiel `Brüche kürzen.pdf` statt `Scan_0034.pdf`.
2. Oben in der Dateiliste auf den passenden Ordner klicken, z. B. **Mathematik 6**.
3. Oben rechts auf **Add file** → **Upload files** klicken.
4. Die Datei in das große Feld ziehen. Oder auf **choose your files** klicken und die Datei auswählen.
5. Ganz unten auf den grünen Knopf **Commit changes** klicken. Das heißt so viel wie „Speichern“.

**Eine neue Gruppe** (z. B. `Chemie Klasse 9`) entsteht, wenn du auf dem eigenen Computer einen Ordner mit diesem Namen anlegst, die Dateien hineinlegst und **den ganzen Ordner** auf der Startseite des Repositorys über **Add file** → **Upload files** in das Feld ziehst.

---

## 🔗 Einen Internet-Link hinzufügen

1. Im passenden Ordner die Datei `links.txt` öffnen und auf den Stift klicken. Gibt es sie noch nicht: **Add file** → **Create new file**, als Namen `links.txt` eintragen.
2. Pro Link eine Zeile: erst der Titel, dann ein senkrechter Strich `|`, dann die Internetadresse:
   ```
   Bruchrechnen üben | https://www.beispiel.de
   ```
   Den Strich `|` bekommst du unter **Windows** mit `AltGr` + `<`, am **Mac** mit `Alt` + `7`.
3. Auf **Commit changes…** klicken, im kleinen Fenster nochmal auf **Commit changes**.

Soll ein Link **ganz oben** im Bereich stehen (zum Beispiel eine TaskCards-Pinnwand), setze ein Ausrufezeichen davor: `! TaskCards Oberstufe | https://www.taskcards.de/...`

---

## 🔄 Ein Material austauschen, umbenennen oder löschen

- **Neue Version:** Die Datei mit **genau dem gleichen Namen** hochladen. Die alte Version wird ersetzt, alte Links und QR-Codes funktionieren weiter.
- **Löschen:** Datei anklicken, oben rechts auf die **drei Punkte `…`** → **Delete file** → **Commit changes**.
- **Anderer Titel, direkt auf der Seite:** In der Übersicht oben auf **✏️ Überschriften bearbeiten** klicken, die Titel in den Feldern ändern und auf **Speichern** klicken. Ohne weitere Einrichtung kommt danach ein Schritt bei GitHub (einfügen und bestätigen). Wer unter „Direktes Speichern einrichten“ einmal einen Zugangsschlüssel hinterlegt, speichert mit einem Klick.
- **Anderer Titel, bei GitHub:** Die Datei `titel.txt` öffnen, auf den Stift klicken und den Text **rechts** vom Strich `|` ändern. Das geht für Materialien, für die Überschriften der Kästen (z. B. „Mathe Klasse 8“) und für den Titel der Seite. Der Link zum Material bleibt dabei gleich.

**Reihenfolge:** Eine Zahl vor den Namen setzen, also `1 Natürliche Zahlen`, `2 Geometrie`. Die Zahl wird auf der Seite nicht angezeigt.

**Kurzlinks:** Die Kurznamen stehen in der Datei `kurzlinks.txt`, eine Zeile pro Datei: `kurzname | Ordner/Dateiname`. Fehlt eine Datei dort, wird der Kurzname automatisch aus dem Dateinamen gebildet. Wer einen Kurznamen ändert, ändert auch den Link: Schon verteilte Links und QR-Codes funktionieren dann nicht mehr.

**Alte Adressen:** Die früheren langen Adressen (…/Mathematik 6/Bruchheft ….html) leiten automatisch auf den Kurzlink weiter.

---

## 📱 QR-Code für die Klasse

In der Übersicht beim gewünschten Material auf **QR** klicken. Es erscheint ein großer QR-Code, der nur zu diesem einen Material führt.

---

## ❓ Wenn etwas nicht klappt

**Die Änderung ist nicht zu sehen**
- 2 Minuten gewartet? Die Seite neu laden: **Windows:** `Strg` + `F5`, **Mac:** `Cmd` + `Shift` + `R`.
- Oben auf den Reiter **Actions** klicken:
  - 🟡 Gelber Punkt: Die Seite wird noch gebaut. Kurz warten.
  - ✅ Grüner Haken: Alles in Ordnung. Nochmal neu laden.
  - ❌ Rotes Kreuz: Die Seite konnte nicht gebaut werden. Die letzte Änderung ansehen oder rückgängig machen.

---

## ⚠️ Bitte beachten

- **Alles hier ist öffentlich.** Die Übersicht ist nur versteckt, nicht geschützt: Wer die Adresse kennt oder dieses Repository bei GitHub findet, sieht alle Materialien. Keine Namen von Schülern, keine Noten, keine Fotos von Schülern hochladen.
- **Lösungen** erst hochladen, wenn die Klasse sie sehen darf.
- **Keine Seiten aus Schulbüchern** einscannen und hochladen, nur eigene Arbeitsblätter.
- **Diese Dateien bitte nicht löschen:** `generate_index.py`, `kurzlinks.txt`, `titel.txt`, den Ordner `.github` und `README.md` (diese Anleitung). Sie sorgen dafür, dass die Seite funktioniert.
