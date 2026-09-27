Diese Custom Component inklusive Karte zeigt die Abfahrtszeiten der
Karlsruher KVV an. Inspiriert von https://github.com/demartinomarco/F.A.R.T.,
daher der Name.

![Screenshot](screenshot.png)

Repository: https://github.com/emente/fart_home_assistant

[![Öffnet die eigene Home Assistant-Instanz und zeigt den Dialog zum Hinzufügen dieses benutzerdefinierten Repositories in HACS an.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=emente&repository=fart_home_assistant&category=integration)
[![Öffnet die eigene Home Assistant-Instanz und startet das Einrichten einer neuen Integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=fart)


## Installation über HACS

1. Auf den ersten Button oben klicken (oder in HACS dieses Repository manuell als benutzerdefiniertes Repository hinzufügen, Kategorie: Integration).
2. Über HACS installieren.
3. Home Assistant neu starten.
4. Auf den zweiten Button oben klicken (oder Einstellungen -> Geräte & Dienste -> `Integration hinzufügen` -> `FART` auswählen).
5. Die Haltestelle aus der Liste auswählen.
6. Es erscheint eine Benachrichtigung mit den Einrichtungsschritten: `/fart_files/fart-ha-card.js` als Dashboard-Ressource hinzufügen (einmalig, auch bei mehreren Haltestellen nur einmal nötig) und das genaue Karten-YAML (inklusive der Entity-ID der Haltestelle) in ein Dashboard einfügen.

Die Ressource muss nur einmal hinzugefügt werden:

1. Einstellungen -> Dashboards -> das ⋮-Menü (oben rechts) -> Ressourcen.
2. Ressource hinzufügen -> URL `/fart_files/fart-ha-card.js` -> Ressourcentyp `JavaScript-Modul` -> Erstellen.

(Falls `Ressourcen` nicht in diesem Menü erscheint, im Benutzerprofil den `Erweiterten Modus` aktivieren.)
