# Creature Luminose su Roblox Studio

Questa cartella contiene tutte le 16 creature già pronte per Roblox:

| File | Cosa contiene |
|---|---|
| `modelli/*.glb` | Serie 1: mantide, gatto, gufo, rana, farfalla, libellula, lupo, Lucina |
| `modelli/deserto/*.glb` | Serie del deserto: scorpione, fennec, scarabeo, vipera, lucertola, avvoltoio, tarantola, cactus |
| `CreatureLuminose.client.lua` | **Un solo script** per tutte le 16 creature: Neon, luci, faretti e animazioni |

Ogni file contiene forme, texture (colore, trasparenza, emissione) e marcatori
invisibili per luci e animazioni.

**Limiti rispettati:**
- **ogni creatura ha al massimo 20.000 triangoli in totale**, tra 15.500 e 19.600 a seconda della creatura;
- nessun pezzo supera il limite di Roblox per singola mesh;
- sono già in scala, alte o larghe tra 3 e 9 stud (un avatar è circa 5 stud).

## 1. Importare le creature

1. Apri il tuo gioco in Roblox Studio.
2. Apri **Import 3D** (menu *File*, oppure il pulsante nella barra in alto) e
   scegli uno o più file `.glb` da `modelli/` o `modelli/deserto/`.
3. Nella finestra di anteprima, prima di premere *Import*:
   - attiva **Anchored**, altrimenti i pezzi cadono a terra appena premi Play;
   - lascia attivo **Import Only As Model**, così ogni creatura resta un unico Model;
   - lascia **Scale Unit** su *Stud*: le dimensioni sono già giuste.
4. Premi **Import** e sposta ogni creatura dove vuoi, sempre come Model intero.

> Non rinominare i pezzi dentro i Model: lo script li riconosce dal nome, per
> esempio `Vipera__Striscia_3` o `Cactus__Faretto_Luce`. Rinominare il Model
> invece va bene. I cubetti `__Radice`, `__Asse…`, `__Perno_…` e `__Luce_…`
> sono marcatori: lo script li rende invisibili, ma non cancellarli.

## 2. Aggiungere luci e animazioni

1. In **Explorer** apri *StarterPlayer › StarterPlayerScripts*.
2. Aggiungi un **LocalScript**, cancella il testo di esempio e incolla tutto il
   contenuto di `CreatureLuminose.client.lua`.
   Se avevi già lo script della prima serie, **sostituiscilo** con questo: vale
   per tutte le 16 creature.
3. Premi **Play**.

Lo script lavora su tutte le creature presenti nel gioco, anche se ne importi
più copie. In particolare:
- rende **Neon** le parti che brillano: occhi, cristalli della lucertola,
  strisce e sonaglio della vipera, collare dell'avvoltoio, bulbo dello
  scorpione, faretto del cactus…;
- crea le **luci** (PointLight) nei punti giusti e le fa pulsare;
- accende dei **faretti** (SpotLight) orientati: il faretto da stadio del
  cactus e gli occhi-faro del gufo;
- aggiunge un **contorno luminoso** (Highlight) al Gattoluna e al Lupo-Luce;
- rende il Lupo-Luce spettrale (materiale **ForceField**) e le ali
  dell'avvoltoio di **vetro** (Glass), che deforma lo sfondo come un miraggio;
- anima:
  - il battito d'ali di tutte le creature alate;
  - la coda dello scorpione;
  - la sfera di magma dello scarabeo, che rotola;
  - le strisce della vipera, che si accendono in sequenza, e la sua lingua;
  - l'antenna e la lampadina della Lucina;
  - la sacca vocale della rana e le lucciole del lupo;
- aggiunge un **BloomEffect** in *Lighting* per far risplendere il Neon.

**Facoltativo: vedere Neon e luci senza premere Play.** Apri *View › Command
Bar*, incolla lo stesso file e premi Invio. Le modifiche restano salvate nel
posto (luci, Neon, parti ancorate). Le animazioni però partono solo in Play.

## 3. Per un effetto migliore

- Rendi la scena notturna: in *Lighting* imposta `ClockTime` a `0` e abbassa
  `Brightness`.
- Imposta `Lighting.Technology` su **Future**: luci, faretti e vetro rendono
  molto meglio.
- Se ali, piume, crepe di lava o venature brillano poco, seleziona la loro
  `SurfaceAppearance` e alza **EmissiveStrength** (per esempio a 10–20).

## Differenze rispetto alla versione Blender

Roblox non ha i materiali procedurali di Blender, e ogni creatura deve stare
sotto i 20.000 triangoli. Per questo alcuni effetti sono ricreati in un altro
modo:

| In Blender | Su Roblox |
|---|---|
| Mesh a dettaglio pieno | Mesh semplificate per stare sotto i 20.000 triangoli (le versioni Blender restano dettagliate) |
| Venature, pannelli, crepe di lava, squame, graffi d'oro | Texture cotte: colore, Emissive Mask e (squame, pelle, corteccia) normal map |
| Emissione pulsante | Neon + luci che pulsano; le texture emissive restano fisse perché Roblox non permette di cambiarle durante il gioco |
| Aure volumetriche (bulbi, punte delle ali, sfera di magma) | Sfere Neon semitrasparenti + luce |
| Cristalli di quarzo con la brace dentro | Neon rosso/arancio semitrasparente |
| Ali-miraggio con distorsione animata | Materiale Glass (deforma lo sfondo) con i bordi Neon |
| Riflessi luminosi sui contorni (gatto, lupo) | Highlight (contorno) |
| Pelo (Lucina, fennec) | Superficie liscia (Roblox non ha il pelo) |
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

I file sono prodotti da `blender/esporta_roblox.py` partendo dagli stessi
generatori delle creature Blender:

```bash
blender --background --python blender/esporta_roblox.py -- --uscita roblox
# opzioni:  --serie deserto          (solo una serie: luminose | deserto)
#           --creatura vipera        (una sola creatura)
#           --scala 4                (1 metro di Blender = 4 stud; default 3)
#           --max-triangoli 20000    (limite per creatura; default 20000)
```

Le impostazioni di ogni creatura per lo script vengono salvate in
`blender/dati_roblox/`, così lo script Luau contiene sempre tutte le creature
esportate, anche se ne rigeneri una sola.
