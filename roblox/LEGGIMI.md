# Creature Luminose su Roblox Studio

Questa cartella contiene le 8 creature già pronte per Roblox:

| File | Cosa contiene |
|---|---|
| `modelli/*.glb` | Una creatura per file: forme, texture (colore, trasparenza, emissione) e marcatori invisibili per luci e animazioni |
| `CreatureLuminose.client.lua` | Script che accende Neon e luci e fa partire le animazioni |

Le creature sono già in scala Roblox, alte o larghe tra 3 e 9 stud (un avatar
è alto circa 5 stud). Nessun pezzo supera il limite di 20.000 triangoli.

## 1. Importare le creature

1. Apri il tuo gioco in Roblox Studio.
2. Apri **Import 3D** (menu *File*, oppure il pulsante nella barra in alto) e
   scegli uno o più file `.glb` dalla cartella `modelli/`.
3. Nella finestra di anteprima, prima di premere *Import*:
   - attiva **Anchored**, altrimenti i pezzi cadono a terra appena premi Play;
   - lascia attivo **Import Only As Model**, così ogni creatura resta un unico Model;
   - lascia **Scale Unit** su *Stud*: le dimensioni sono già giuste.
4. Premi **Import** e sposta ogni creatura dove vuoi, sempre come Model intero.

> Non rinominare i pezzi dentro i Model: lo script li riconosce dal nome, per
> esempio `Mantide__Ala_Vetrata__AlaPosteriore_R`. Rinominare il Model invece
> va bene. I cubetti `__Radice`, `__Asse…`, `__Perno_…` e `__Luce_…` sono
> marcatori: lo script li rende invisibili, ma non cancellarli.

## 2. Aggiungere luci e animazioni

1. In **Explorer** apri *StarterPlayer › StarterPlayerScripts*.
2. Aggiungi un **LocalScript**, cancella il testo di esempio e incolla tutto il
   contenuto di `CreatureLuminose.client.lua`.
3. Premi **Play**.

Lo script lavora su tutte le creature presenti nel gioco, anche se ne importi
più copie. In particolare:
- rende **Neon** le parti che brillano (occhi, punti della rana, bulbilli,
  filamento e vetro della lampadina, lucciole, bulbo della libellula…);
- crea le **luci** (PointLight) nei punti giusti e le fa pulsare;
- aggiunge un **contorno luminoso** (Highlight) al Gattoluna e al Lupo-Luce;
- rende il Lupo-Luce spettrale con il materiale **ForceField**;
- anima il **battito d'ali** di tutte le creature alate, l'**antenna** e la
  **lampadina** che dondolano sulla Lucina, la **sacca vocale** della rana
  che si gonfia e le **lucciole** attorno al lupo;
- aggiunge un **BloomEffect** in *Lighting* per far risplendere il Neon.

**Facoltativo: vedere Neon e luci senza premere Play.** Apri *View › Command
Bar*, incolla lo stesso file e premi Invio. Le modifiche restano salvate nel
posto (luci, Neon, parti ancorate). Le animazioni però partono solo in Play.

## 3. Per un effetto migliore

- Rendi la scena notturna: in *Lighting* imposta `ClockTime` a `0` e abbassa
  `Brightness`.
- Imposta `Lighting.Technology` su **Future** per luci più belle.
- Se le ali o le piume brillano poco, seleziona la loro `SurfaceAppearance` e
  alza **EmissiveStrength** (per esempio a 10–20).

## Differenze rispetto alla versione Blender

Roblox non ha i materiali procedurali di Blender, quindi alcuni effetti sono
ricreati in un altro modo:

| In Blender | Su Roblox |
|---|---|
| Venature e pannelli luminosi delle ali, piume al neon | Texture con trasparenza ed Emissive Mask (SurfaceAppearance) |
| Emissione pulsante | Neon + PointLight che pulsano; le texture emissive restano fisse perché Roblox non permette di cambiarle durante il gioco |
| Aure volumetriche (punte delle ali del gufo, bulbo, lampadina) | Sfere Neon semitrasparenti + luce |
| Riflessi luminosi sui contorni (gatto, lupo) | Highlight (contorno) |
| Lupo semitrasparente | Materiale ForceField turchese |
| Pelo della Lucina | Superficie liscia giallo caldo (Roblox non ha il pelo) |
| Cornee lucide degli occhi | Non incluse |

## Se qualcosa non va

- **I pezzi cadono o si staccano:** hai importato senza *Anchored*. Seleziona
  il Model e attiva *Anchored*, oppure esegui lo script dalla Command Bar
  (ancora tutto).
- **Le creature sono grigie:** l'importer non ha letto i colori. Lo script li
  imposta comunque quando premi Play; per vederli subito, usa la Command Bar.
- **Qualche pezzo appare in ritardo o manca in gioco:** con *StreamingEnabled*
  i pezzi arrivano un po' alla volta. Esegui una volta lo script dalla Command
  Bar: imposta `ModelStreamingMode = Atomic` su ogni creatura, così arriva
  tutta insieme.
- **Voglio creature più grandi o più piccole:** scala il Model in Studio,
  oppure rigenera i file con un'altra scala (vedi sotto).

## Rigenerare i file

I file sono prodotti da `blender/esporta_roblox.py` partendo dallo stesso
generatore delle creature Blender:

```bash
blender --background --python blender/esporta_roblox.py -- --uscita roblox
# opzioni:  --creatura gatto   (una sola creatura)
#           --scala 4          (1 metro di Blender = 4 stud; default 3)
```
