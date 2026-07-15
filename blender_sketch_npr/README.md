# Sketch NPR (Line Art + dynamische Schraffur)

Blender-Addon fuer schwarz/weisse Skizzen-Visualisierungen im Stil technischer
Illustrationen (Konturlinien + Schraffur), gerendert mit Eevee.

## Funktionsprinzip

Der Look besteht aus zwei getrennten, kombinierten Techniken:

1. **Konturen**: ein Grease-Pencil-Objekt mit einem Line-Art-Modifier zeichnet
   Silhouette-, Crease- und Schnittkanten der gesamten Szene als schwarze
   Striche.
2. **Schattierung**: ein prozeduraler Shader (`NPR_Hatching`-Node-Group)
   ersetzt Flaechenhelligkeit durch Schraffur. Die Helligkeit einer Flaeche
   (aus Diffuse-Shading via `Shader to RGB`, ein Eevee-Only-Trick) waehlt aus,
   wie viele Schraffur-Lagen (einfach / Kreuz / dichtes Kreuz) sichtbar sind.
   Die Ausrichtung der Schraffur ist per Driver an die Z-Rotation eines von
   dir gewaehlten Licht-Objekts gekoppelt und dreht sich damit animiert mit.

## Installation

1. Ordner `blender_sketch_npr` als Zip packen (oder direkt den Ordner in
   Blenders Addon-Verzeichnis kopieren).
2. Blender: `Edit > Preferences > Add-ons > Install...`, Zip auswaehlen,
   Addon aktivieren.
3. Im 3D-Viewport: Sidebar (Taste `N`) > Tab **"Sketch NPR"**.

## Bedienung

1. **Render Setup**: Button klicken – stellt Eevee (bzw. Eevee Next, falls
   verfuegbar), weissen World-Background und "Standard"-Farbmanagement ein.
2. **Konturen (Line Art)**: Linienstaerke einstellen, Button klicken. Legt
   ein Grease-Pencil-Objekt `Sketch_LineArt` an, das automatisch die ganze
   Szene als Quelle nutzt.
3. **Schattierung (Hatching)**:
   - Licht-Objekt auswaehlen, dessen Rotation die Schraffur-Richtung steuert.
   - Zielobjekte (Meshes) selektieren, "Hatch-Material auf Auswahl anwenden"
     klicken.
   - Aenderst du das Licht-Objekt nachtraeglich, auf den Refresh-Button
     (Icon rechts daneben) klicken, um den Driver neu zu verknuepfen.

Feintuning (Kontrast, Hatch-Skalierung, Linienbreite, Exposure) direkt im
Shader-Editor am Node `NPR_Hatching` (als Group-Node in jedem Material, das
du damit erstellt hast).

## Bekannte Einschraenkungen / Testhinweise

- Die Grease-Pencil/Line-Art-API hat sich zwischen Blender <=4.2 (GPv2) und
  4.3+ (GPv3, vereinheitlichter Modifier-Stack) veraendert. Das Addon
  unterscheidet zur Laufzeit anhand `bpy.app.version`, wurde aber nicht in
  einer echten Blender-Instanz getestet (kein Blender in dieser Umgebung
  verfuegbar). Falls beim Line-Art-Setup ein Fehler auftritt: Fehlertext aus
  der Blender-Konsole kopieren, dann kann gezielt nachgebessert werden.
- Die Licht-Kopplung nutzt vereinfachend nur die Z-Rotation des Lichts als
  Schraffur-Winkel (Azimut). Bei Lichtern, die stark um X/Y gekippt werden,
  ist das eine Naeherung.
- `Shader to RGB` funktioniert nur in Eevee, nicht in Cycles – das ist hier
  gewollt, macht das Material aber Eevee-exklusiv.
- Animation: Line Art wird pro Frame neu berechnet, das kann bei komplexen
  Szenen das Rendering spuerbar verlangsamen.
