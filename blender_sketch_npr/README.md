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
   - **Wobble**: staerke der handgezeichneten Unregelmaessigkeit (0 = perfekt
     gerade Linien, hoehere Werte = zittrige, organische Striche).
   - **Blur**: Weichheit der Strichkanten (0 = harte Kante, hoehere Werte =
     unscharfe/verwaschene Linien wie bei Tusche, die leicht verlaeuft).
   - **Transparent**: siehe Abschnitt "Transparenz" unten.
   - Zielobjekte (Meshes) selektieren, "Hatch-Material auf Auswahl anwenden"
     klicken.
   - Aenderst du das Licht-Objekt nachtraeglich, auf den Refresh-Button
     (Icon rechts daneben) klicken, um den Driver neu zu verknuepfen.

Feintuning (Kontrast, Hatch-Skalierung, Linienbreite, Exposure) direkt im
Shader-Editor am Node `NPR_Hatching` (als Group-Node in jedem Material, das
du damit erstellt hast).

## Transparenz / Schraffur ueber ein bestehendes Material legen

Es gibt zwei Wege, dafuer zwei Buttons im Panel:

**A) "Auf bestehendes Material legen"** (empfohlen fuer den Normalfall)
Splict die Schraffur direkt in den Node-Baum des *aktiven* Materials jedes
ausgewaehlten Objekts: dein bisheriges Shading (Principled BSDF, Texturen
etc.) bleibt erhalten, die Tinte wird per Mix-Shader oben drueber gelegt.
Kein Alpha-/Blend-Mode-Setup noetig, kein Z-Fighting, da es dieselbe
Geometrie/denselben Material-Slot nutzt. Das ist der richtige Weg, wenn du
"die Schraffur auf mein vorhandenes Material legen" meinst.

**B) Checkbox "Transparent"** + "Hatch-Material auf Auswahl anwenden"
Erzeugt ein eigenstaendiges Material, bei dem die Papierflaeche komplett
durchsichtig ist (`Transparent BSDF`) und nur die Tinten-Striche opak bleiben
(`blend_method = HASHED`). Sinnvoll, wenn du die Schraffur auf einem
**separaten Overlay-Objekt** brauchst, z. B.:
- eine leicht nach aussen versetzte Kopie deines Meshes (z. B. mit einem
  Solidify-Modifier, Offset ~0.001) nur fuer die Schraffur, waehrend das
  Original-Objekt sein eigenes Material behaelt,
- eine Bildebene/Plane vor der Kamera, um die Schraffur separat zu
  compositen (z. B. um sie im Compositor ueber ein Foto oder einen anderen
  Render zu legen).

**Manuelle Variante** (falls du es lieber selbst im Shader-Editor baust,
oder der Automatismus bei deiner Materialstruktur nicht greift):
1. Shader-Editor oeffnen, dein Material auswaehlen.
2. `Add > Group > NPR_Hatching` einfuegen (die Node-Group existiert, sobald
   einmal ein Hatch-Material im Addon erzeugt wurde).
3. `Add > Shader > Emission`, `Color`-Ausgang der Group hineinstecken.
4. `Add > Converter > Mix Shader`. `Fac` <- `Alpha`-Ausgang der Group.
   Eingang 1 <- dein bisheriger Shader (z. B. Principled BSDF). Eingang 2
   <- die Emission aus Schritt 3.
5. Ausgang des Mix Shader in den `Surface`-Eingang des Material-Output
   stecken (ersetzt die bisherige direkte Verbindung).
6. Fuer echte Transparenz statt Ueberlagerung: `Add > Shader > Transparent
   BSDF` statt deines bisherigen Shaders in Eingang 1 des Mix Shader, dann
   am Material `Settings > Blend Mode` auf `Hashed` stellen.

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
