# Feedback

## Gefällt mir sehr gut

- Python Masterclass, Respekt! 👏🏻
- Funktionen sauber mit Parametern, keine globalen Abhängigkeiten
- Sprechende Namen für Variablen und Funktionen
- Sehr fein granuliertes Error handling -> gute Basis für Debugging!
- rotate_part.gif ist geil und einfach verständlich!
  - Mini Verbesserung: Der Perspektivenwechsel für die umgedrehte Tasse ist etwas komisch. Originalbild mit KI bearbeiten um die gedrehte Variante zu erzeugen?

## Geht besser

- Klarere Trennung zwischen selbst programiert und für UI generiert
- Durch Asynchronität, objektorientierung ist der Entry Point der Anwendung nicht offensichtlich
- Strukturierung in `application` und `instances` missverstädnlich (`assets` passt)
  - `application` beinhaltet utility (z.B. conversions)
  - `instances` sind technisch genau das Gegenteil, keine Instanzen sondern nur Definitionen
- `app` ist etwas unstrukturiert (sollte als einfach verstädnlicher Entry-point dienen)
  - UI Definitionen auslagern
  - Utilities (parse_float, ..) seperat halten
- project-sheduler .tick() -> Inline definition von weiteren Funktion macht Programmfluss wieder schwerer lesbar

## Nicht gut

- Zu wenig funktionsbeschreibende Kommentare
  - Was macht Funktion / Klasse XY
  - Wo wird FUnktion XY im Programmablauf augerufen
  - Was ist die Logik / der Entscheidungsbaum der ticks, ..

## High-Level Anmerkungen

- Programm extrem asynchron -> theretisch sehr gute Lösung, aber (unnötig?) kompliziert
  - Serial, camera crane, turn table -> alles asynchron zu trennen ist flexibel aber wirklich nötig? Hätte man auf ein Layer reduzierehn können imho
- Bilder werden erst beim Abschluss geschrieben, Memory "Leak"? 144 Bilder a X MB, da kommt schnell was zusammen
- Programm setzt stark auf Klassen --> Architektur Entscheidung (Ich bin persönlich nicht der größte Fan, weil viel Boilerplate, ist aber eine legitime Entscheidung 👍🏻)

## Sonstiges

- Anmerkungen mit `# Yannik` direkt im Code
- Conda enviroment noch exportieren und im Ordner `conda` ablegen (damit man alle Packages auf anderem System unkompliziert installieren kann)
- Es gibt noch ein paar ungenutzte Imports / Funktionen

# PyInstaller

https://pyinstaller.org/en/stable/usage.html

```bash
pyinstaller --onedir app.py
```

Falls assets nicht automatisch übernommen werden:

```bash
pyinstaller --onedir --add-data "assets;assets" app.py
```
