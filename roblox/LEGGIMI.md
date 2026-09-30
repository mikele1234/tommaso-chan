# Creature Luminose su Roblox Studio

Questa cartella contiene tutte le 48 creature già pronte per Roblox:

| File | Cosa contiene |
|---|---|
| `modelli/*.glb` | Serie 1: mantide, gatto, gufo, rana, farfalla, libellula, lupo, Lucina |
| `modelli/deserto/*.glb` | Serie del deserto: scorpione, fennec, scarabeo, vipera, lucertola, avvoltoio, tarantola, cactus |
| `modelli/neve/*.glb` | Serie della neve: orso, pinguino, renna, volpe, leopardo, falena-yeti, civetta, pupazzo "Skibidi" |
| `modelli/oceano/*.glb` | Serie dell'oceano: medusa, cavalluccio, granchio, manta, squalo, tartaruga, rana pescatrice, blobfish |
| `modelli/mostri/*.glb` | Serie dei mostri: pipistrello-sanguisuga, franken-scarabeo, gargoyle, zucca-infestata, corvo-peste, occhio fluttuante, calderone, verme "Nextbot" |
| `modelli/inferno/*.glb` | Serie dell'inferno: Cerbero, Caronte, Ade, Persefone, Alichino, Ghiacciolo, Flegetonte, Tung Tung Tung Sahur |
| `CreatureLuminose.client.lua` | **Un solo script** per tutte le 48 creature: Neon, luci, faretti, colori e animazioni |

Le serie dalla 5 in poi (mostri, inferno, angeli, draghi) sono **modelli
statici**: lo script accende Neon, luci, faretti, vetro e contorni, ma non
le anima.

Ogni file contiene forme, texture (colore, trasparenza, emissione) e marcatori
invisibili per luci e animazioni.

**Limiti rispettati:**
- **ogni creatura ha al massimo 20.000 triangoli in totale** (quasi tutte tra 15.000 e 19.900; le più semplici,
  come il Verme dell'Ohio, ne hanno molti meno);
- nessun pezzo supera il limite di Roblox per singola mesh;
- sono già in scala: quasi tutte sono alte o larghe tra 2 e 8 stud (un avatar
  è circa 5 stud); con scie, fasci di luce e ali aperte alcune arrivano a
  10–15 stud (renna, manta, granchio-faro).

## 1. Importare le creature

1. Apri il tuo gioco in Roblox Studio.
2. Apri **Import 3D** (menu *File*, oppure il pulsante nella barra in alto) e
   scegli uno o più file `.glb` da `modelli/` o dalle sottocartelle `deserto/`,
   `neve/`, `oceano/`.
3. Nella finestra di anteprima, prima di premere *Import*:
   - attiva **Anchored**, altrimenti i pezzi cadono a terra appena premi Play;
   - lascia attivo **Import Only As Model**, così ogni creatura resta un unico Model;
   - lascia **Scale Unit** su *Stud*: le dimensioni sono già giuste.
4. Premi **Import** e sposta ogni creatura dove vuoi, sempre come Model intero.

Le creature marine che nuotano (medusa, cavalluccio, manta, squalo,
tartaruga, rana pescatrice) sono già sollevate di qualche stud rispetto alla
base del Model: appoggiando il Model sul fondale, galleggiano sopra di esso.

> Non rinominare i pezzi dentro i Model: lo script li riconosce dal nome, per
> esempio `Vipera__Striscia_3` o `Cactus__Faretto_Luce`. Rinominare il Model
> invece va bene. I cubetti `__Radice`, `__Asse…`, `__Perno_…` e `__Luce_…`
> sono marcatori: lo script li rende invisibili, ma non cancellarli.

## 2. Aggiungere luci e animazioni

1. In **Explorer** apri *StarterPlayer › StarterPlayerScripts*.
2. Aggiungi un **LocalScript**, cancella il testo di esempio e incolla tutto il
   contenuto di `CreatureLuminose.client.lua`.
   Se avevi già uno script delle serie precedenti, **sostituiscilo** con
   questo: vale per tutte le 48 creature.
3. Premi **Play**.

Lo script lavora su tutte le creature presenti nel gioco, anche se ne importi
più copie. In particolare:
- rende **Neon** le parti che brillano: occhi, cristalli, bulbi, corna della
  renna, antenne della medusa, celle del guscio della tartaruga, faretto del
  cactus…;
- crea le **luci** (PointLight) nei punti giusti e le fa pulsare;
- accende dei **faretti** (SpotLight) orientati: il faretto da stadio del
  cactus, gli occhi-faro del gufo e della civetta, i fasci del granchio-faro;
- aggiunge **contorni luminosi** (Highlight): gatto, lupo, medusa,
  falena-yeti e l'orso, il cui contorno cambia colore come un'aurora;
- usa i materiali di Roblox dove servono: **ForceField** (lupo spettrale,
  medusa gelatinosa, pelliccia della falena-yeti), **Glass** (ali
  dell'avvoltoio, pancia del pinguino, volpe di ghiaccio, esca della rana
  pescatrice), **Ice** e **Snow** (lastra del pinguino, pupazzo di neve);
- fa **scorrere i colori**: il naso LED del pupazzo e la sua luce passano per
  tutto l'arcobaleno;
- anima:
  - il battito d'ali di tutte le creature alate;
  - code, colli e antenne (scorpione, vipera, pupazzo, medusa, rana pescatrice);
  - le cose che girano: la sfera di magma dello scarabeo e il faro del granchio;
  - le sequenze di luce: strisce della vipera, onde sul guscio della tartaruga;
  - il **galleggiamento** delle creature marine e il respiro della medusa;
  - l'antenna della Lucina, la sacca vocale della rana, lucciole e scie;
- aggiunge un **BloomEffect** in *Lighting* per far risplendere il Neon.

**Facoltativo: vedere Neon e luci senza premere Play.** Apri *View › Command
Bar*, incolla lo stesso file e premi Invio. Le modifiche restano salvate nel
posto (luci, Neon, parti ancorate). Le animazioni però partono solo in Play.

## 3. Per un effetto migliore

- Rendi la scena notturna: in *Lighting* imposta `ClockTime` a `0` e abbassa
  `Brightness`.
- Imposta `Lighting.Technology` su **Future**: luci, faretti e vetro rendono
  molto meglio.
- Se ali, piume, crepe di lava, rosette o vasi sanguigni brillano poco,
  seleziona la loro `SurfaceAppearance` e alza **EmissiveStrength** (per
  esempio a 10–20).
- Per le creature marine, un'atmosfera subacquea: in *Lighting* aggiungi un
  `Atmosphere` con `Density` alta e colore azzurro scuro, oppure metti le
  creature dentro un volume di `Terrain` d'acqua.

## Differenze rispetto alla versione Blender

Roblox non ha i materiali procedurali di Blender, e ogni creatura deve stare
sotto i 20.000 triangoli. Per questo alcuni effetti sono ricreati in un altro
modo:

| In Blender | Su Roblox |
|---|---|
| Mesh a dettaglio pieno | Mesh semplificate per stare sotto i 20.000 triangoli (le versioni Blender restano dettagliate) |
| Venature, pannelli, crepe di lava, squame, graffi d'oro | Texture cotte: colore, Emissive Mask e (squame, pelle, corteccia) normal map |
| Emissione pulsante | Neon + luci che pulsano; le texture emissive restano fisse perché Roblox non permette di cambiarle durante il gioco |
| Aure volumetriche (bulbi, punte delle ali, sfera di magma, fasci del faro) | Sfere e coni Neon semitrasparenti + luce |
| Cristalli di quarzo con la brace dentro | Neon rosso/arancio semitrasparente |
| Ali-miraggio con distorsione animata | Materiale Glass (deforma lo sfondo) con i bordi Neon |
| Riflessi luminosi sui contorni (gatto, lupo) | Highlight (contorno) |
| Pelo (Lucina, fennec, orso, renna, leopardo, falena-yeti) | Superficie liscia con i colori cotti in texture (Roblox non ha il pelo) |
| Pelliccia della falena-yeti con la luce che filtra (Volume Scatter) | Corpo Neon magenta dentro un guscio ForceField |
| Onde dell'aurora che scorrono sulla pelliccia dell'orso | Aurora fissa in texture + contorno che cambia colore + tre luci che si accendono in sequenza |
| Ghiaccio e vetro con rifrazione vera | Materiale Glass di Roblox |
| Particelle (scia della renna, plancton) | Qualche fiocco o scaglia Neon che fluttua |
| Caustiche, foschia e aurora nel cielo | Non incluse (fanno parte della scena, non delle creature) |
| Cornee lucide degli occhi | Non incluse |
| Serie 5-8: emissione con il nodo Blackbody e luci proxy (Point Light con Child Of) | Neon con lo stesso colore + una `PointLight` nel punto della luce proxy |
| Liquidi dentro al vetro (fiala di sangue, pozione, lanterne) | Guscio Glass + interno Neon |
| Volumi luminosi (alone del Serafino e della lanterna di Caronte, fasci dell'Occhio e della tromba di Gabriele) | Forme Neon semitrasparenti |
| Fumo della zucca e volumi di scena (foschie, nebbia) | Non inclusi |
| Crepe di magma scavate con il Displacement (Gargoyle, Tung Tung) | Crepe cotte in texture con Emissive Mask e normal map |
| Faccia meme compressa del Verme dell'Ohio | La stessa immagine, cotta nella texture del pannello |
| Wireframe delle nervature (ali di Ddraig) | Non incluso: resta la membrana con i puntini Neon |

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
# opzioni:  --serie neve             (solo una serie: luminose | deserto | neve | oceano |
#                                     mostri | inferno | angeli | draghi)
#           --creatura vipera        (una sola creatura)
#           --scala 4                (1 metro di Blender = 4 stud; default 3)
#           --max-triangoli 20000    (limite per creatura; default 20000;
#                                     0 = nessun limite, dettaglio pieno)
```

Le impostazioni di ogni creatura per lo script vengono salvate in
`blender/dati_roblox/`, così lo script Luau contiene sempre tutte le creature
esportate, anche se ne rigeneri una sola.
