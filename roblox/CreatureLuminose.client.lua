--[[
    CREATURE LUMINOSE - luci, Neon, bagliore e animazioni per Roblox
    =================================================================
    File generato da blender/esporta_roblox.py: non serve modificarlo.

    COME SI USA
      1. Importa i file .glb delle creature con "Import 3D"
         (nelle impostazioni di import attiva "Anchored").
      2. In StarterPlayer > StarterPlayerScripts crea un LocalScript,
         incolla TUTTO questo file e premi Play.

    FACOLTATIVO: per vedere Neon, luci e contorni anche senza premere Play,
    apri View > Command Bar, incolla tutto il file e premi Invio: le modifiche
    restano salvate nel posto (le animazioni partono solo in Play).

    Cosa fa:
      * trasforma in Neon le parti luminose (occhi, punti, bulbilli, cristalli...)
      * crea le luci (PointLight) nei punti giusti e le fa pulsare
      * aggiunge contorni luminosi (Highlight), anche con i colori che scorrono
      * usa ForceField, Glass, Ice, Snow... dove serve (lupo spettrale, ali
        dell'avvoltoio, pancia del pinguino, volpe di ghiaccio, medusa...)
      * accende i faretti (SpotLight): cactus, gufo, civetta, granchio-faro
      * fa scorrere i colori (naso LED del pupazzo, aurora dell'orso)
      * anima ali, antenne, code, colli, pinne, sfere che rotolano e fari che
        girano, e fa galleggiare le creature marine
      * aggiunge un BloomEffect in Lighting per far "accendere" il Neon
]]

local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")

local CICLO = 5.000

local CONFIG = {
	Ade = {
		bob = {},
		luci = {
			Ade__Luce_01 = {b0 = 0.312, b1 = 0.312, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.23},
			Ade__Luce_02 = {b0 = 0.312, b1 = 0.312, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.23},
			Ade__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.91},
			Ade__Luce_04 = {b0 = 0.604, b1 = 0.604, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.91},
			Ade__Luce_05 = {b0 = 0.427, b1 = 0.427, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.5},
			Ade__Luce_06 = {b0 = 0.697, b1 = 0.697, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 6.13},
			Ade__Luce_07 = {b0 = 0.697, b1 = 0.697, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 6.13},
			Ade__Luce_08 = {b0 = 0.697, b1 = 0.697, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Ade__Chitina_Nera = {c = {0.1121, 0.0861, 0.1428}, k = "solid"},
			Ade__Elmo_Oscurita = {c = {0.1517, 0.1334, 0.1718}, k = "solid", metallo = true},
			Ade__Gemme = {c = {0.7977, 0.4845, 1}, k = "glass", t = 0.6},
			Ade__Mantello_Bordo_Viola = {e = 24, h = {0.7354, 0.3492, 1}, k = "tex"},
			Ade__Occhi = {c = {0.7354, 0.3492, 1}, k = "neon"},
			Ade__Punte_Bidente = {c = {0.7354, 0.3492, 1}, k = "neon"},
			Ade__Ricchezze_Oro = {c = {0.9547, 0.7977, 0.4845}, k = "solid", metallo = true},
		},
		perni = {},
		scala = {},
	},
	Alichino = {
		bob = {},
		luci = {
			Alichino__Luce_01 = {b0 = 0.604, b1 = 0.604, c = {1, 0.5371, 0.2478}, cyc = 1, ph = 0, r = 5.91},
			Alichino__Luce_02 = {b0 = 0.604, b1 = 0.604, c = {0.3492, 1, 0.4845}, cyc = 1, ph = 0, r = 5.91},
			Alichino__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {0.3492, 0.5838, 1}, cyc = 1, ph = 0, r = 5.91},
			Alichino__Luce_04 = {b0 = 0.551, b1 = 0.551, c = {1, 0.2478, 0.2209}, cyc = 1, ph = 0, r = 5.79},
			Alichino__Luce_05 = {b0 = 0.551, b1 = 0.551, c = {1, 0.9063, 0.1517}, cyc = 1, ph = 0, r = 5.79},
			Alichino__Luce_06 = {b0 = 0.551, b1 = 0.551, c = {0.2478, 0.9547, 0.3811}, cyc = 1, ph = 0, r = 5.79},
		},
		parti = {
			Alichino__Calze_Gialle = {c = {0.9063, 0.7674, 0.1517}, k = "solid"},
			Alichino__Calze_Rosse = {c = {0.7354, 0.1517, 0.1517}, k = "solid"},
			Alichino__Campanelli_Oro = {c = {1, 0.8808, 0.5371}, k = "solid", metallo = true},
			Alichino__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			Alichino__Elitre_Rombi = {e = 24, k = "tex"},
			Alichino__Esca_Blu = {c = {0.3492, 0.5838, 1}, k = "neon"},
			Alichino__Esca_Verde = {c = {0.3492, 1, 0.4845}, k = "neon"},
			Alichino__Gorgiera = {c = {0.964, 0.9547, 0.9357}, k = "solid"},
			Alichino__Maschera_Nera = {c = {0.0999, 0.0999, 0.1121}, k = "solid"},
			Alichino__Occhi = {c = {0.964, 0.964, 0.9547}, k = "solid"},
			Alichino__Pelle_Rossa = {c = {0.6652, 0.1517, 0.1284}, k = "solid"},
			Alichino__Pompon_0 = {c = {0.9547, 0.2478, 0.2478}, k = "solid"},
			Alichino__Pompon_1 = {c = {1, 0.8808, 0.2478}, k = "solid"},
			Alichino__Punta_Coda = {c = {1, 0.3492, 0.2478}, k = "neon"},
			Alichino__Pupille = {c = {0.061, 0.061, 0.061}, k = "solid"},
			Alichino__Riflessi = {c = {1, 1, 1}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	Avvoltoio = {
		bob = {},
		luci = {
			Avvoltoio__Luce_01 = {b0 = 0.712, b1 = 1.273, c = {0.5838, 0.9309, 1}, cyc = 1, ph = 0, r = 7.47},
			Avvoltoio__Luce_02 = {b0 = 0.9, b1 = 1.273, c = {0.5838, 0.9309, 1}, cyc = 1, ph = 0.8, r = 7.47},
		},
		parti = {
			Avvoltoio__Ali_Miraggio__Ala_L = {c = {0.9063, 0.9731, 1}, k = "glass", t = 0.55},
			Avvoltoio__Ali_Miraggio__Ala_R = {c = {0.9063, 0.9731, 1}, k = "glass", t = 0.55},
			Avvoltoio__Artigli = {c = {0.3811, 0.3656, 0.3492}, k = "solid"},
			Avvoltoio__Becco = {c = {0.8543, 0.7977, 0.68}, k = "solid"},
			Avvoltoio__Bordo_Ali__Ala_L = {c = {0.7674, 0.964, 1}, k = "neon", p = {0.5, 1, 1, 0.8}},
			Avvoltoio__Bordo_Ali__Ala_R = {c = {0.7674, 0.964, 1}, k = "neon", p = {0.5, 1, 1, 0.8}},
			Avvoltoio__Collare_Luce = {c = {0.5838, 0.9309, 1}, k = "neon", p = {0.333, 1, 1, 0}},
			Avvoltoio__Occhi = {c = {0.1517, 0.1284, 0.0999}, k = "solid"},
			Avvoltoio__Pelle_Nuda = {c = {0.7354, 0.6097, 0.6012}, k = "solid"},
			Avvoltoio__Piumaggio = {c = {0.2717, 0.2209, 0.1828}, k = "solid"},
			Avvoltoio__Roccia = {k = "tex"},
		},
		perni = {
			Avvoltoio__Perno_Ala_L = {
				membri = {"Avvoltoio__Ali_Miraggio__Ala_L", "Avvoltoio__Bordo_Ali__Ala_L"},
				padre = nil,
				rot = {
					{amp = 0.0873, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Avvoltoio__Perno_Ala_R = {
				membri = {"Avvoltoio__Ali_Miraggio__Ala_R", "Avvoltoio__Bordo_Ali__Ala_R"},
				padre = nil,
				rot = {
					{amp = -0.0873, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	Blobfish = {
		bob = {},
		luci = {
			Blobfish__Luce_01 = {b0 = 0.201, b1 = 0.402, c = {1, 0.5838, 0.8267}, cyc = 1, ph = 0, r = 5.44},
			Blobfish__Luce_02 = {b0 = 2.25, b1 = 2.25, c = {1, 0.964, 0.9777}, cyc = 1, ph = 0, r = 9.75},
		},
		parti = {
			Blobfish__Alucce_Patetiche__Aluccia_L = {ali = true, e = 3.6, k = "tex"},
			Blobfish__Alucce_Patetiche__Aluccia_R = {ali = true, e = 3.6, k = "tex"},
			Blobfish__Bagliore_Ridicolo = {c = {1, 0.5838, 0.8267}, k = "aura", p = {0.286, 1, 1, 0}, t = 0.85},
			Blobfish__Bava = {c = {0.9547, 0.8543, 0.8808}, k = "solid"},
			Blobfish__Gelatina_Rosa = {k = "tex"},
			Blobfish__Labbra = {c = {0.7674, 0.5064, 0.5657}, k = "solid"},
			Blobfish__Mascella_Squadrata = {c = {0.9547, 0.7484, 0.7674}, k = "solid"},
			Blobfish__Occhi = {c = {0.0999, 0.0999, 0.1121}, k = "solid"},
			Blobfish__Zampetta = {c = {0.6652, 0.4845, 0.4366}, k = "solid"},
		},
		perni = {
			Blobfish__Perno_Aluccia_L = {
				membri = {"Blobfish__Alucce_Patetiche__Aluccia_L"},
				padre = nil,
				rot = {
					{amp = 0.1745, asse = "Y", cyc = 2, ph = 0},
				},
			},
			Blobfish__Perno_Aluccia_R = {
				membri = {"Blobfish__Alucce_Patetiche__Aluccia_R"},
				padre = nil,
				rot = {
					{amp = -0.1745, asse = "Y", cyc = 2, ph = 0},
				},
			},
		},
		scala = {},
	},
	Cactus = {
		bob = {},
		luci = {
			Cactus__Luce_01 = {ang = 75, b0 = 10, b1 = 10, c = {0.964, 0.9822, 1}, cyc = 16, dir = "Cactus__Luce_01_Dir", ph = 0, r = 36},
			Cactus__Luce_02 = {b0 = 2.624, b1 = 2.846, c = {0.964, 0.9822, 1}, cyc = 16, ph = 0, r = 11.14},
		},
		parti = {
			Cactus__Ali_Mosca__Ala_Mosca_L = {ali = true, e = 4, k = "tex"},
			Cactus__Ali_Mosca__Ala_Mosca_R = {ali = true, e = 4, k = "tex"},
			Cactus__Cromo = {c = {0.9063, 0.9063, 0.9163}, k = "solid", metallo = true},
			Cactus__Faccia_Decal = {c = {0.0861, 0.0861, 0.0861}, k = "solid"},
			Cactus__Faretto_Luce = {c = {0.964, 0.9822, 1}, k = "neon", p = {0.833, 1, 16, 0}},
			Cactus__Faretto_Metallo = {c = {0.2934, 0.2934, 0.3133}, k = "solid", metallo = true},
			Cactus__Lanugine = {c = {0.9547, 0.9309, 0.8543}, k = "solid"},
			Cactus__Occhiali_Specchio = {c = {0.7674, 0.7977, 0.8808}, k = "solid", metallo = true, rifl = 0.8},
			Cactus__Spine = {c = {0.9309, 0.865, 0.68}, k = "solid"},
			Cactus__Stuzzicadenti = {c = {0.8808, 0.7858, 0.6343}, k = "solid"},
			Cactus__Terra = {c = {0.2717, 0.2209, 0.1718}, k = "solid"},
			Cactus__Vaso_Terracotta = {k = "tex"},
			Cactus__Verde = {c = {0.2717, 0.4845, 0.2478}, k = "solid"},
		},
		perni = {
			Cactus__Perno_Ala_Mosca_L = {
				membri = {"Cactus__Ali_Mosca__Ala_Mosca_L"},
				padre = nil,
				rot = {
					{amp = 0.5934, asse = "Y", cyc = 48, ph = 0},
				},
			},
			Cactus__Perno_Ala_Mosca_R = {
				membri = {"Cactus__Ali_Mosca__Ala_Mosca_R"},
				padre = nil,
				rot = {
					{amp = -0.5934, asse = "Y", cyc = 48, ph = 0},
				},
			},
		},
		scala = {},
	},
	Calderone = {
		bob = {},
		luci = {
			Calderone__Luce_01 = {b0 = 1.102, b1 = 1.102, c = {0.7674, 0.3133, 1}, cyc = 1, ph = 0, r = 7.07},
			Calderone__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {1, 0.3133, 0.8543}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Calderone__Bolle_Fucsia = {c = {1, 0.3133, 0.8543}, k = "neon", t = 0.55},
			Calderone__Bolle_Viola = {c = {0.7674, 0.3133, 1}, k = "neon", t = 0.55},
			Calderone__Ghisa_Arrugginita = {k = "tex"},
			Calderone__Pozione = {c = {0.7674, 0.3133, 1}, k = "neon"},
			Calderone__Ventre_Rana = {c = {0.7674, 0.7484, 0.5838}, k = "solid"},
			Calderone__Zampe_Rana = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Caronte = {
		bob = {},
		luci = {
			Caronte__Luce_01 = {b0 = 0.312, b1 = 0.312, c = {1, 0.5047, 0}, cyc = 1, ph = 0, r = 5.23},
			Caronte__Luce_02 = {b0 = 0.312, b1 = 0.312, c = {1, 0.5047, 0}, cyc = 1, ph = 0, r = 5.23},
			Caronte__Luce_03 = {b0 = 1.207, b1 = 1.207, c = {0.8209, 0.863, 1}, cyc = 1, ph = 0, r = 7.32},
		},
		parti = {
			Caronte__Alone_Lanterna = {c = {0.8209, 0.863, 1}, k = "aura", t = 0.85},
			Caronte__Capelli_Bianchi = {c = {0.8808, 0.8808, 0.865}, k = "solid"},
			Caronte__Ferro_Lanterna = {c = {0.2478, 0.2478, 0.2478}, k = "solid", metallo = true},
			Caronte__Fiamma_Fantasma = {c = {0.8209, 0.863, 1}, k = "neon"},
			Caronte__Legno_Barca = {k = "tex"},
			Caronte__Mantello_Elitre = {c = {0.1601, 0.168, 0.1828}, k = "solid"},
			Caronte__Obolo_Oro = {c = {1, 0.865, 0.5657}, k = "solid", metallo = true},
			Caronte__Occhi_Brace = {c = {1, 0.5047, 0}, k = "neon"},
			Caronte__Ombra_Cappuccio = {c = {0.0258, 0.0258, 0.0388}, k = "solid"},
			Caronte__Remo = {c = {0.2717, 0.2209, 0.1718}, k = "solid"},
			Caronte__Vetro_Lanterna = {c = {0.9063, 1, 0.9777}, k = "glass", t = 0.7},
			Caronte__Zampe = {c = {0.1517, 0.1517, 0.1601}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Cavalluccio = {
		bob = {},
		luci = {
			Cavalluccio__Luce_01 = {b0 = 0.779, b1 = 1.273, c = {0.5371, 1, 0.5838}, cyc = 1, ph = 0, r = 7.47},
			Cavalluccio__Luce_02 = {b0 = 0.551, b1 = 0.9, c = {0.5371, 1, 0.5838}, cyc = 1, ph = 1.5, r = 6.6},
		},
		parti = {
			Cavalluccio__Ali_Frenetiche__Ala_Dorsale_L = {ali = true, e = 10, k = "tex"},
			Cavalluccio__Ali_Frenetiche__Ala_Dorsale_R = {ali = true, e = 10, k = "tex"},
			Cavalluccio__Ali_Frenetiche__Ala_Pettorale_L = {ali = true, e = 10, k = "tex"},
			Cavalluccio__Ali_Frenetiche__Ala_Pettorale_R = {ali = true, e = 10, k = "tex"},
			Cavalluccio__Occhio__Galleggiamento = {c = {0.2478, 0.5838, 0.2478}, k = "neon"},
			Cavalluccio__Pelle_Tribale__Galleggiamento = {e = 16, k = "tex"},
			Cavalluccio__Scia_Ali__Galleggiamento = {c = {0.5371, 1, 0.5838}, k = "neon", p = {0.444, 1, 4, 0}, t = 0.75},
			Cavalluccio__Testa_Tribale__Galleggiamento = {e = 16, k = "tex"},
		},
		perni = {
			Cavalluccio__Perno_Ala_Dorsale_L = {
				membri = {"Cavalluccio__Ali_Frenetiche__Ala_Dorsale_L"},
				padre = "Cavalluccio__Perno_Galleggiamento",
				rot = {
					{amp = 0.5236, asse = "Y", cyc = 36, ph = 0},
				},
			},
			Cavalluccio__Perno_Ala_Dorsale_R = {
				membri = {"Cavalluccio__Ali_Frenetiche__Ala_Dorsale_R"},
				padre = "Cavalluccio__Perno_Galleggiamento",
				rot = {
					{amp = -0.5236, asse = "Y", cyc = 36, ph = 0},
				},
			},
			Cavalluccio__Perno_Ala_Pettorale_L = {
				membri = {"Cavalluccio__Ali_Frenetiche__Ala_Pettorale_L"},
				padre = "Cavalluccio__Perno_Galleggiamento",
				rot = {
					{amp = 0.6109, asse = "Y", cyc = 40, ph = 0.7},
				},
			},
			Cavalluccio__Perno_Ala_Pettorale_R = {
				membri = {"Cavalluccio__Ali_Frenetiche__Ala_Pettorale_R"},
				padre = "Cavalluccio__Perno_Galleggiamento",
				rot = {
					{amp = -0.6109, asse = "Y", cyc = 40, ph = 0.7},
				},
			},
			Cavalluccio__Perno_Galleggiamento = {
				membri = {"Cavalluccio__Luce_01", "Cavalluccio__Luce_02", "Cavalluccio__Occhio__Galleggiamento", "Cavalluccio__Pelle_Tribale__Galleggiamento", "Cavalluccio__Scia_Ali__Galleggiamento", "Cavalluccio__Testa_Tribale__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0698, asse = "X", cyc = 1, ph = 1.1},
					{amp = 0.15, asse = "Z", cyc = 1, mov = true, ph = 0},
				},
			},
		},
		scala = {},
	},
	Cerbero = {
		bob = {},
		luci = {
			Cerbero__Luce_01 = {b0 = 0.854, b1 = 0.854, c = {1, 0.6329, 0.2562}, cyc = 1, ph = 0, r = 6.49},
			Cerbero__Luce_02 = {b0 = 0.854, b1 = 0.854, c = {1, 0.6329, 0.2562}, cyc = 1, ph = 0, r = 6.49},
			Cerbero__Luce_03 = {b0 = 0.854, b1 = 0.854, c = {1, 0.6329, 0.2562}, cyc = 1, ph = 0, r = 6.49},
		},
		parti = {
			Cerbero__Borchie = {c = {0.7977, 0.7674, 0.7354}, k = "solid", metallo = true},
			Cerbero__Chitina_Brace = {e = 8, k = "tex"},
			Cerbero__Collare = {c = {0.1517, 0.1121, 0.0999}, k = "solid"},
			Cerbero__Fari_Ambra = {c = {1, 0.6329, 0.2562}, k = "neon"},
			Cerbero__Lingua = {c = {0.7977, 0.3133, 0.3492}, k = "solid"},
			Cerbero__Muso = {c = {0.3811, 0.2828, 0.206}, k = "solid"},
			Cerbero__Naso = {c = {0.0999, 0.0861, 0.0861}, k = "solid"},
			Cerbero__Occhi_Fresnel = {c = {0.1517, 0.0999, 0.061}, h = {1, 0.6329, 0.2562}, k = "solid"},
			Cerbero__Occhi_Serpi = {c = {1, 0.6329, 0.2562}, k = "neon"},
			Cerbero__Pelo = {c = {0.2478, 0.1828, 0.1517}, k = "solid"},
			Cerbero__Serpentelli = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Cherubino = {
		bob = {},
		luci = {
			Cherubino__Luce_01 = {b0 = 0.604, b1 = 0.604, c = {1, 0.7499, 0.4789}, cyc = 1, ph = 0, r = 5.91},
			Cherubino__Luce_02 = {b0 = 0.604, b1 = 0.604, c = {1, 0.7499, 0.4789}, cyc = 1, ph = 0, r = 5.91},
			Cherubino__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {1, 0.7499, 0.4789}, cyc = 1, ph = 0, r = 5.91},
			Cherubino__Luce_04 = {b0 = 0.604, b1 = 0.604, c = {1, 0.7499, 0.4789}, cyc = 1, ph = 0, r = 5.91},
			Cherubino__Luce_05 = {b0 = 0.854, b1 = 0.854, c = {1, 0.7499, 0.4789}, cyc = 1, ph = 0, r = 6.49},
		},
		parti = {
			Cherubino__Ali_Ambra = {ali = true, e = 16, k = "tex"},
			Cherubino__Armatura_Elettro = {c = {0.9309, 0.7977, 0.5371}, k = "solid", metallo = true},
			Cherubino__Dettagli_Scuri = {c = {0.2478, 0.1897, 0.1284}, k = "solid"},
			Cherubino__Lanternino = {c = {1, 0.7499, 0.4789}, k = "neon"},
			Cherubino__Organi_Luce = {c = {1, 0.7499, 0.4789}, k = "neon"},
			Cherubino__Scintille = {c = {1, 1, 1}, k = "neon"},
			Cherubino__Zoccoli = {c = {0.1897, 0.1517, 0.1284}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Civetta = {
		bob = {},
		luci = {
			Civetta__Luce_01 = {ang = 36, b0 = 1.559, b1 = 2.012, c = {0.7977, 0.9309, 1}, cyc = 1, dir = "Civetta__Luce_01_Dir", ph = 0, r = 9.2},
			Civetta__Luce_02 = {ang = 36, b0 = 1.559, b1 = 2.012, c = {0.7977, 0.9309, 1}, cyc = 1, dir = "Civetta__Luce_02_Dir", ph = 0, r = 9.2},
			Civetta__Luce_03 = {b0 = 0.636, b1 = 4.269, c = {0.9309, 0.9686, 1}, cyc = 1, ph = 0, r = 14.46},
			Civetta__Luce_04 = {b0 = 0.402, b1 = 0.636, c = {0.7674, 0.9309, 1}, cyc = 2, ph = 0, r = 5.98},
		},
		parti = {
			Civetta__Becco = {c = {0.2478, 0.2478, 0.2717}, k = "solid"},
			Civetta__Disco_Facciale = {c = {0.9547, 0.964, 0.9777}, k = "solid"},
			Civetta__Ghiaccioli = {c = {0.7674, 0.9309, 1}, k = "neon", t = 0.2},
			Civetta__Lampo_Bufera = {c = {0.9309, 0.9686, 1}, k = "aura", p = {0.01, 1, 1, 0}, t = 0.85},
			Civetta__Neve = {c = {0.9357, 0.9547, 0.9867}, k = "solid", m = "Snow"},
			Civetta__Occhio_Faro = {c = {0.8543, 0.964, 1}, k = "neon", p = {0.667, 1, 1, 0}},
			Civetta__Palpebre = {c = {0.1517, 0.1517, 0.1718}, k = "solid"},
			Civetta__Piuma_Cristallo = {e = 12, k = "tex"},
			Civetta__Piuma_Cristallo__Ala_L = {e = 12, k = "tex"},
			Civetta__Piuma_Cristallo__Ala_R = {e = 12, k = "tex"},
			Civetta__Piuma_Petto = {e = 8.8, k = "tex"},
			Civetta__Piumino = {c = {0.9309, 0.9405, 0.9547}, k = "solid"},
			Civetta__Roccia = {k = "tex"},
		},
		perni = {
			Civetta__Perno_Ala_L = {
				membri = {"Civetta__Piuma_Cristallo__Ala_L"},
				padre = nil,
				rot = {
					{amp = 0.2443, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Civetta__Perno_Ala_R = {
				membri = {"Civetta__Piuma_Cristallo__Ala_R"},
				padre = nil,
				rot = {
					{amp = -0.2443, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	CorvoPeste = {
		bob = {},
		luci = {
			CorvoPeste__Luce_01 = {b0 = 1.102, b1 = 1.102, c = {0.68, 1, 0.2717}, cyc = 1, ph = 0, r = 7.07},
			CorvoPeste__Luce_02 = {b0 = 0.427, b1 = 0.427, c = {0.68, 1, 0.2717}, cyc = 1, ph = 0, r = 5.5},
			CorvoPeste__Luce_03 = {b0 = 0.427, b1 = 0.427, c = {0.68, 1, 0.2717}, cyc = 1, ph = 0, r = 5.5},
		},
		parti = {
			CorvoPeste__Alone_Tossico = {c = {0.68, 1, 0.2717}, k = "aura", t = 0.85},
			CorvoPeste__Bagliore_Acido = {c = {0.68, 1, 0.2717}, k = "neon"},
			CorvoPeste__Costole = {c = {0.865, 0.8434, 0.7858}, k = "solid"},
			CorvoPeste__Lenti_Vetro = {c = {0.9309, 1, 0.9063}, k = "glass", t = 0.7},
			CorvoPeste__Maschera_Cuoio = {k = "tex"},
			CorvoPeste__Ottone = {c = {0.7674, 0.6343, 0.3811}, k = "solid", metallo = true},
			CorvoPeste__Pelle_Spennata = {k = "tex"},
			CorvoPeste__Petto_Radioattivo = {c = {0.68, 1, 0.2717}, k = "neon"},
			CorvoPeste__Piume_Strappate = {e = 12, k = "tex"},
			CorvoPeste__Polvere_Tossica = {c = {0.68, 1, 0.2717}, k = "neon"},
			CorvoPeste__Zampe = {c = {0.2478, 0.2348, 0.2348}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Custode = {
		bob = {},
		luci = {
			Custode__Luce_01 = {b0 = 0.27, b1 = 0.27, c = {1, 0.5296, 0}, cyc = 1, ph = 0, r = 5.13},
			Custode__Luce_02 = {b0 = 0.27, b1 = 0.27, c = {1, 0.5296, 0}, cyc = 1, ph = 0, r = 5.13},
			Custode__Luce_03 = {b0 = 1.743, b1 = 1.743, c = {1, 0.5296, 0}, cyc = 1, ph = 0, r = 8.57},
			Custode__Luce_04 = {b0 = 0.854, b1 = 0.854, c = {1, 0.5296, 0}, cyc = 1, ph = 0, r = 6.49},
		},
		parti = {
			Custode__Ali = {ali = true, e = 16, k = "tex"},
			Custode__Candela = {c = {1, 0.5296, 0}, k = "neon"},
			Custode__Corpo_Morbido = {c = {0.9547, 0.9163, 0.8434}, k = "solid"},
			Custode__Gabbia_Chitina = {c = {0.7674, 0.65, 0.4236}, k = "solid", metallo = true},
			Custode__Guance = {c = {1, 0.7354, 0.7014}, k = "solid"},
			Custode__Occhioni = {c = {0.1517, 0.1284, 0.1121}, k = "solid"},
			Custode__Punte_Antenne = {c = {1, 0.5296, 0}, k = "neon"},
			Custode__Riflessi = {c = {1, 1, 1}, k = "neon"},
			Custode__Vetro_Lanterna = {c = {1, 0.9777, 0.9309}, k = "glass", t = 0.7},
		},
		perni = {},
		scala = {},
	},
	Ddraig = {
		bob = {},
		luci = {
			Ddraig__Luce_01 = {b0 = 0.854, b1 = 0.854, c = {1, 0.5953, 0.1831}, cyc = 1, ph = 0, r = 6.49},
			Ddraig__Luce_02 = {b0 = 0.427, b1 = 0.427, c = {1, 1, 1}, cyc = 1, ph = 0, r = 5.5},
			Ddraig__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {1, 0.5953, 0.1831}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			Ddraig__Bocca = {c = {0.5838, 0.0999, 0.1517}, k = "solid"},
			Ddraig__Coda_Brace = {c = {1, 0.5953, 0.1831}, k = "neon"},
			Ddraig__Corna = {c = {0.9309, 0.9063, 0.8543}, k = "solid"},
			Ddraig__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			Ddraig__Fratello_Bianco = {c = {1, 1, 1}, k = "neon"},
			Ddraig__Lingua = {c = {0.9063, 0.3492, 0.4236}, k = "solid"},
			Ddraig__Membrana_Ali = {c = {0.5838, 0.1517, 0.1517}, k = "solid"},
			Ddraig__Occhi = {c = {1, 0.8543, 0.3492}, k = "neon"},
			Ddraig__Ossa_Ali = {c = {0.6262, 0.1517, 0.0999}, k = "solid"},
			Ddraig__Petto_Rosso = {c = {1, 0.4918, 0.1865}, k = "neon"},
			Ddraig__Porta = {c = {0.0999, 0.0861, 0.0702}, k = "solid"},
			Ddraig__Scaglie_Rosse = {c = {0.7354, 0.1897, 0.1517}, k = "solid"},
			Ddraig__Torre_Pietra = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Farfalla = {
		bob = {},
		luci = {
			Farfalla__Luce_01 = {b0 = 0.636, b1 = 1.684, c = {0.4236, 0.7354, 1}, cyc = 2, ph = 0, r = 8.43},
		},
		parti = {
			Farfalla__Ala_Anteriore__AlaAnt_L = {ali = true, e = 8.8, k = "tex"},
			Farfalla__Ala_Anteriore__AlaAnt_R = {ali = true, e = 8.8, k = "tex"},
			Farfalla__Ala_Posteriore__AlaPost_L = {ali = true, e = 8.8, k = "tex"},
			Farfalla__Ala_Posteriore__AlaPost_R = {ali = true, e = 8.8, k = "tex"},
			Farfalla__Aura_Antenna = {c = {0.4845, 1, 0.8543}, k = "aura", p = {0.4, 1, 2, 0}, t = 0.85},
			Farfalla__Corpo_Scuro = {c = {0.0861, 0.0999, 0.1428}, k = "solid"},
			Farfalla__Cuore_Luce = {c = {0.3492, 0.7674, 1}, k = "aura", p = {0.2, 1, 2, 0}, t = 0.85},
			Farfalla__Occhi = {c = {0.1517, 0.2478, 0.3492}, k = "solid"},
			Farfalla__Punte_Antenne = {c = {0.5838, 1, 0.8543}, k = "neon", p = {0.5, 1, 2, 0}},
		},
		perni = {
			Farfalla__Perno_AlaAnt_L = {
				membri = {"Farfalla__Ala_Anteriore__AlaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.2793, asse = "Y", cyc = 2, ph = 0},
				},
			},
			Farfalla__Perno_AlaAnt_R = {
				membri = {"Farfalla__Ala_Anteriore__AlaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.2793, asse = "Y", cyc = 2, ph = 0},
				},
			},
			Farfalla__Perno_AlaPost_L = {
				membri = {"Farfalla__Ala_Posteriore__AlaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.2793, asse = "Y", cyc = 2, ph = 0.15},
				},
			},
			Farfalla__Perno_AlaPost_R = {
				membri = {"Farfalla__Ala_Posteriore__AlaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.2793, asse = "Y", cyc = 2, ph = 0.15},
				},
			},
		},
		scala = {},
	},
	Fennec = {
		bob = {},
		luci = {
			Fennec__Luce_01 = {b0 = 0.551, b1 = 1.006, c = {1, 0.8267, 0.5371}, cyc = 1, ph = 0.5, r = 6.85},
			Fennec__Luce_02 = {b0 = 0.636, b1 = 0.955, c = {1, 0.8808, 0.5838}, cyc = 1, ph = 0, r = 6.73},
		},
		parti = {
			Fennec__Alone_Coda = {c = {1, 0.7977, 0.4236}, k = "aura", p = {0.333, 1, 1, 0.5}, t = 0.85},
			Fennec__Luccichio = {c = {1, 0.9777, 0.9063}, k = "neon"},
			Fennec__Naso = {c = {0.0999, 0.0999, 0.0999}, k = "solid"},
			Fennec__Occhi = {c = {0.1897, 0.1284, 0.061}, k = "solid"},
			Fennec__Orecchie_Solari__Orecchio_L = {ali = true, e = 14, k = "tex"},
			Fennec__Orecchie_Solari__Orecchio_R = {ali = true, e = 14, k = "tex"},
			Fennec__Pancia = {c = {0.964, 0.9063, 0.8095}, k = "solid"},
			Fennec__Pelo = {k = "tex"},
			Fennec__Punta_Coda = {c = {1, 0.7977, 0.4236}, k = "neon", p = {0.343, 1, 1, 0.5}},
		},
		perni = {
			Fennec__Perno_Orecchio_L = {
				membri = {"Fennec__Orecchie_Solari__Orecchio_L"},
				padre = nil,
				rot = {
					{amp = 0.0873, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Fennec__Perno_Orecchio_R = {
				membri = {"Fennec__Orecchie_Solari__Orecchio_R"},
				padre = nil,
				rot = {
					{amp = -0.0873, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	Flegetonte = {
		bob = {},
		luci = {
			Flegetonte__Luce_01 = {b0 = 1.102, b1 = 1.102, c = {1, 0.4778, 0}, cyc = 1, ph = 0, r = 7.07},
			Flegetonte__Luce_02 = {b0 = 1.102, b1 = 1.102, c = {1, 0.5296, 0}, cyc = 1, ph = 0, r = 7.07},
		},
		parti = {
			Flegetonte__Ali_Fiamma = {ali = true, e = 16, k = "tex"},
			Flegetonte__Bolle_Lava = {c = {1, 0.8137, 0.6101}, k = "neon"},
			Flegetonte__Chitina_Vulcanica = {e = 24, k = "tex"},
			Flegetonte__Fuoco_Che_Scorre = {e = 32, k = "tex"},
			Flegetonte__Gocce_Lava = {c = {1, 0.4778, 0}, k = "neon"},
			Flegetonte__Guscio_Vetro = {c = {1, 0.9309, 0.8543}, k = "glass", t = 0.7},
			Flegetonte__Zampe = {c = {0.1897, 0.1517, 0.1428}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	FrankenScarabeo = {
		bob = {},
		luci = {
			FrankenScarabeo__Luce_01 = {b0 = 1.102, b1 = 1.102, c = {0.3811, 1, 0.865}, cyc = 1, ph = 0, r = 7.07},
			FrankenScarabeo__Luce_02 = {b0 = 1.102, b1 = 1.102, c = {0.3811, 1, 0.865}, cyc = 1, ph = 0, r = 7.07},
			FrankenScarabeo__Luce_03 = {b0 = 1.102, b1 = 1.102, c = {0.3811, 1, 0.865}, cyc = 1, ph = 0, r = 7.07},
			FrankenScarabeo__Luce_04 = {b0 = 1.102, b1 = 1.102, c = {0.3811, 1, 0.865}, cyc = 1, ph = 0, r = 7.07},
			FrankenScarabeo__Luce_05 = {b0 = 0.604, b1 = 0.604, c = {0.7674, 1, 1}, cyc = 1, ph = 0, r = 5.91},
			FrankenScarabeo__Luce_06 = {b0 = 0.604, b1 = 0.604, c = {0.7674, 1, 1}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			FrankenScarabeo__Bulloni = {c = {0.68, 0.68, 0.6944}, k = "solid", metallo = true},
			FrankenScarabeo__Cicatrici = {c = {0.4366, 0.3133, 0.3318}, k = "solid"},
			FrankenScarabeo__Elitra_Coccinella = {k = "tex"},
			FrankenScarabeo__Elitra_Smeraldo = {c = {0.1517, 0.5064, 0.2934}, k = "solid", metallo = true},
			FrankenScarabeo__Elitra_Viola = {c = {0.3959, 0.1517, 0.4614}, k = "solid"},
			FrankenScarabeo__Energia_Fessure = {c = {0.3811, 1, 0.865}, k = "neon"},
			FrankenScarabeo__Energia_Intrappolata = {c = {0.3811, 1, 0.865}, k = "neon"},
			FrankenScarabeo__Filo_Sutura = {c = {0.1517, 0.1517, 0.1428}, k = "solid"},
			FrankenScarabeo__Occhio_Mosca = {c = {0.7354, 0.1897, 0.1517}, k = "solid"},
			FrankenScarabeo__Occhio_Nero = {c = {0.0999, 0.0999, 0.0999}, k = "solid"},
			FrankenScarabeo__Pronoto_Cervo = {c = {0.1121, 0.0999, 0.1121}, k = "solid"},
			FrankenScarabeo__Scariche = {c = {0.7674, 1, 1}, k = "neon"},
			FrankenScarabeo__Testa = {c = {0.4492, 0.2209, 0.1517}, k = "solid"},
			FrankenScarabeo__Ventre_Larva = {c = {0.7674, 0.7014, 0.5838}, k = "solid"},
			FrankenScarabeo__Zampa_Cavalletta = {c = {0.4845, 0.68, 0.3492}, k = "solid"},
			FrankenScarabeo__Zampa_Mantide = {c = {0.3811, 0.6262, 0.2717}, k = "solid"},
			FrankenScarabeo__Zampa_Nera = {c = {0.1284, 0.1177, 0.1284}, k = "solid"},
			FrankenScarabeo__Zampa_Pelosa = {c = {0.3811, 0.2934, 0.2209}, k = "solid"},
			FrankenScarabeo__Zampa_Saltatrice = {c = {0.5838, 0.5838, 0.3133}, k = "solid"},
			FrankenScarabeo__Zampa_Talpa = {c = {0.5657, 0.41, 0.2478}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Gabriele = {
		bob = {},
		luci = {
			Gabriele__Luce_01 = {ang = 42, b0 = 8.419, b1 = 8.419, c = {0.9403, 0.9503, 1}, cyc = 1, dir = "Gabriele__Luce_01_Dir", ph = 0, r = 24.14},
			Gabriele__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {0.9403, 0.9503, 1}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Gabriele__Ali_Bianche = {ali = true, e = 20, k = "tex"},
			Gabriele__Campana_Luce = {c = {0.9403, 0.9503, 1}, k = "neon"},
			Gabriele__Chitina_Perla = {c = {0.9357, 0.9453, 0.964}, k = "solid"},
			Gabriele__Fascio_Lunare = {c = {0.9403, 0.9503, 1}, k = "aura", t = 0.85},
			Gabriele__Petali_Giglio = {c = {0.9403, 0.9503, 1}, k = "neon"},
			Gabriele__Polline = {c = {1, 0.7674, 0.2478}, k = "solid"},
			Gabriele__Stami = {c = {0.7977, 0.8543, 0.5838}, k = "solid"},
			Gabriele__Steli_Giglio = {c = {0.6262, 0.7674, 0.5371}, k = "solid"},
			Gabriele__Tromba_Argento = {c = {0.9063, 0.9163, 0.9453}, k = "solid", metallo = true},
		},
		perni = {},
		scala = {},
	},
	Gargoyle = {
		bob = {},
		luci = {
			Gargoyle__Luce_01 = {b0 = 0.551, b1 = 0.551, c = {1, 0.5529, 0.0838}, cyc = 1, ph = 0, r = 5.79},
			Gargoyle__Luce_02 = {b0 = 0.551, b1 = 0.551, c = {1, 0.5529, 0.0838}, cyc = 1, ph = 0, r = 5.79},
			Gargoyle__Luce_03 = {b0 = 1.743, b1 = 1.743, c = {1, 0.4172, 0}, cyc = 1, ph = 0, r = 8.57},
			Gargoyle__Luce_04 = {b0 = 1.207, b1 = 1.207, c = {1, 0.4172, 0}, cyc = 1, ph = 0, r = 7.32},
		},
		parti = {
			Gargoyle__Ali_Pietra = {e = 12.5, k = "tex"},
			Gargoyle__Lingue_Fuoco = {c = {1, 0.5047, 0}, k = "neon", t = 0.2},
			Gargoyle__Magma_Interno = {c = {1, 0.4172, 0}, k = "neon"},
			Gargoyle__Occhi_Fiamma = {c = {1, 0.5529, 0.0838}, k = "neon"},
			Gargoyle__Ossidiana_Crepe = {e = 15, k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Gatto = {
		bob = {},
		luci = {
			Gatto__Luce_01 = {b0 = 0.712, b1 = 1.006, c = {0.6652, 0.5838, 1}, cyc = 1, ph = 0, r = 6.85},
		},
		parti = {
			Gatto__Ala_Luce_Post__AlaPost_L = {ali = true, e = 5.2, k = "tex"},
			Gatto__Ala_Luce_Post__AlaPost_R = {ali = true, e = 5.2, k = "tex"},
			Gatto__Ala_Luce__AlaAnt_L = {ali = true, e = 5.6, k = "tex"},
			Gatto__Ala_Luce__AlaAnt_R = {ali = true, e = 5.6, k = "tex"},
			Gatto__Aura_Coda = {c = {0.6652, 0.5838, 1}, k = "aura", p = {0.444, 1, 1, 0}, t = 0.85},
			Gatto__Baffi_Luce = {c = {0.7674, 0.8267, 1}, k = "neon", p = {0.5, 1, 2, 0}},
			Gatto__Coda_Luce = {c = {0.7014, 0.6262, 1}, k = "neon", p = {0.437, 1, 1, 0}},
			Gatto__Iride = {c = {1, 0.865, 0.3811}, k = "neon"},
			Gatto__Luna_Fronte = {c = {0.8808, 0.9063, 1}, k = "neon"},
			Gatto__Naso = {c = {0.2478, 0.1517, 0.2717}, k = "solid"},
			Gatto__Orecchio_Interno = {c = {0.7014, 0.5371, 1}, k = "neon", p = {0.417, 1, 1, 0.5}},
			Gatto__Pelo_Notte = {c = {0.0702, 0.061, 0.1061}, h = {0.6012, 0.5064, 1}, k = "solid"},
			Gatto__Pupilla = {c = {0, 0, 0}, k = "solid"},
		},
		perni = {
			Gatto__Perno_AlaAnt_L = {
				membri = {"Gatto__Ala_Luce__AlaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Gatto__Perno_AlaAnt_R = {
				membri = {"Gatto__Ala_Luce__AlaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.1222, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Gatto__Perno_AlaPost_L = {
				membri = {"Gatto__Ala_Luce_Post__AlaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 0.25},
				},
			},
			Gatto__Perno_AlaPost_R = {
				membri = {"Gatto__Ala_Luce_Post__AlaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.1222, asse = "Y", cyc = 1, ph = 0.25},
				},
			},
		},
		scala = {},
	},
	Ghiacciolo = {
		bob = {},
		luci = {
			Ghiacciolo__Luce_01 = {b0 = 0.382, b1 = 0.382, c = {1, 0.5953, 0.1831}, cyc = 1, ph = 0, r = 5.39},
			Ghiacciolo__Luce_02 = {b0 = 0.382, b1 = 0.382, c = {1, 0.8712, 0.7375}, cyc = 1, ph = 0, r = 5.39},
			Ghiacciolo__Luce_03 = {b0 = 0.382, b1 = 0.382, c = {0.7354, 0.3492, 1}, cyc = 1, ph = 0, r = 5.39},
			Ghiacciolo__Luce_04 = {b0 = 1.35, b1 = 1.35, c = {0.7542, 0.818, 1}, cyc = 1, ph = 0, r = 7.65},
			Ghiacciolo__Luce_05 = {b0 = 1.102, b1 = 1.102, c = {0.7542, 0.818, 1}, cyc = 1, ph = 0, r = 7.07},
		},
		parti = {
			Ghiacciolo__Chitina_Brinata = {c = {0.1718, 0.1828, 0.2209}, k = "solid"},
			Ghiacciolo__Corna = {c = {0.1897, 0.1897, 0.206}, k = "solid"},
			Ghiacciolo__Cuore = {c = {0.7542, 0.818, 1}, k = "neon"},
			Ghiacciolo__Faccia_Gialla = {c = {0.9309, 0.9063, 0.7674}, k = "solid"},
			Ghiacciolo__Faccia_Nera = {c = {0.1121, 0.0999, 0.1232}, k = "solid"},
			Ghiacciolo__Faccia_Rossa = {c = {0.7354, 0.1897, 0.1517}, k = "solid"},
			Ghiacciolo__Ghiaccio_Cocito = {c = {0.7977, 0.9453, 1}, k = "glass", m = "Ice", t = 0.45},
			Ghiacciolo__Membrana_Ali = {c = {0.2478, 0.2717, 0.3133}, k = "solid"},
			Ghiacciolo__Puntino_Giallo = {c = {1, 0.8712, 0.7375}, k = "neon"},
			Ghiacciolo__Puntino_Rosso = {c = {1, 0.5953, 0.1831}, k = "neon"},
			Ghiacciolo__Puntino_Viola = {c = {0.7354, 0.3492, 1}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	Granchio = {
		bob = {},
		luci = {
			Granchio__Luce_01 = {ang = 16, b0 = 2.846, b1 = 3.337, c = {1, 0.9309, 0.7014}, cyc = 2, dir = "Granchio__Luce_01_Dir", ph = 0, r = 12.29},
			Granchio__Luce_02 = {ang = 16, b0 = 2.846, b1 = 3.337, c = {1, 0.9309, 0.7014}, cyc = 2, dir = "Granchio__Luce_02_Dir", ph = 0, r = 12.29},
			Granchio__Luce_03 = {b0 = 1.423, b1 = 1.909, c = {1, 0.9309, 0.7014}, cyc = 1, ph = 0, r = 8.95},
			Granchio__Luce_04 = {b0 = 1.559, b1 = 1.559, c = {0.8808, 0.9309, 1}, cyc = 1, ph = 0, r = 8.14},
		},
		parti = {
			Granchio__Balani = {c = {0.7674, 0.7484, 0.722}, k = "solid"},
			Granchio__Bulbo_Vetro = {c = {1, 0.9309, 0.7014}, k = "neon", p = {0.571, 1, 1, 0}, t = 0.15},
			Granchio__Corallo = {c = {0.9547, 0.5371, 0.6262}, k = "solid"},
			Granchio__Corallo_Arancio = {c = {0.9777, 0.7354, 0.4236}, k = "solid"},
			Granchio__Corazza_Roccia = {k = "tex"},
			Granchio__Crepa = {c = {0.0999, 0.061, 0}, k = "solid"},
			Granchio__Fascio__Faro = {c = {1, 0.9547, 0.7977}, k = "aura", t = 0.85},
			Granchio__Lampada_Faro = {c = {1, 0.9777, 0.9063}, k = "neon", p = {0.773, 1, 2, 0}},
			Granchio__Lanterna = {c = {0.2717, 0.2478, 0.2209}, k = "solid", metallo = true},
			Granchio__Occhi = {c = {0.0999, 0.0999, 0.0999}, k = "solid"},
			Granchio__Punte_Chele = {c = {0.1897, 0.1718, 0.1718}, k = "solid"},
			Granchio__Zampe = {k = "tex"},
		},
		perni = {
			Granchio__Perno_Faro = {
				membri = {"Granchio__Luce_01", "Granchio__Luce_01_Dir", "Granchio__Luce_02", "Granchio__Luce_02_Dir", "Granchio__Fascio__Faro"},
				padre = nil,
				rot = {
					{amp = 0, asse = "Z", cyc = 2, ph = 0, spin = true},
				},
			},
		},
		scala = {},
	},
	Gufo = {
		bob = {},
		luci = {
			Gufo__Luce_01 = {b0 = 0.318, b1 = 0.712, c = {1, 0.8808, 0.5371}, cyc = 2, ph = 0.5, r = 6.16},
			Gufo__Luce_02 = {b0 = 0.318, b1 = 0.712, c = {1, 0.8808, 0.5371}, cyc = 2, ph = 0.5, r = 6.16},
			Gufo__Luce_03 = {ang = 38, b0 = 1.559, b1 = 2.012, c = {1, 0.9309, 0.6652}, cyc = 1, dir = "Gufo__Luce_03_Dir", ph = 0, r = 9.2},
			Gufo__Luce_04 = {ang = 38, b0 = 1.559, b1 = 2.012, c = {1, 0.9309, 0.6652}, cyc = 1, dir = "Gufo__Luce_04_Dir", ph = 0, r = 9.2},
			Gufo__Luce_05 = {b0 = 0.349, b1 = 0.532, c = {1, 0.9063, 0.6262}, cyc = 2, ph = 0, r = 5.74},
		},
		parti = {
			Gufo__Anello_Occhio = {c = {1, 0.8267, 0.3133}, k = "neon"},
			Gufo__Artigli = {c = {0.2717, 0.2478, 0.2348}, k = "solid"},
			Gufo__Aura_Ali = {c = {1, 0.8095, 0.3492}, k = "aura", p = {0.333, 1, 2, 0.5}, t = 0.85},
			Gufo__Becco = {c = {0.5371, 0.4845, 0.3811}, k = "solid"},
			Gufo__Corteccia = {k = "tex"},
			Gufo__Disco_Facciale = {c = {0.5838, 0.4614, 0.3133}, k = "solid"},
			Gufo__Foglia = {c = {0.1517, 0.2934, 0.1517}, k = "solid"},
			Gufo__Occhio_Faro = {c = {1, 0.9777, 0.7354}, k = "neon", p = {0.632, 1, 1, 0}},
			Gufo__Piuma_Chiara = {e = 8, k = "tex"},
			Gufo__Piuma_Neon = {e = 10.4, k = "tex"},
			Gufo__Piumino = {c = {0.3811, 0.2478, 0.1428}, k = "solid"},
			Gufo__Zampe = {c = {0.6262, 0.5657, 0.3811}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Halolo = {
		bob = {},
		luci = {
			Halolo__Luce_01 = {b0 = 0.493, b1 = 0.493, c = {1, 0.4614, 0.7674}, cyc = 1, ph = 0, r = 5.65},
			Halolo__Luce_02 = {b0 = 0.493, b1 = 0.493, c = {1, 0.8808, 0.2478}, cyc = 1, ph = 0, r = 5.65},
			Halolo__Luce_03 = {b0 = 0.493, b1 = 0.493, c = {0.3492, 0.7674, 1}, cyc = 1, ph = 0, r = 5.65},
			Halolo__Luce_04 = {b0 = 0.493, b1 = 0.493, c = {1, 1, 1}, cyc = 1, ph = 0, r = 5.65},
		},
		parti = {
			Halolo__Alucce = {ali = true, e = 24, k = "tex"},
			Halolo__Aureola_Hula_Hoop = {e = 40, k = "tex"},
			Halolo__Bocca = {c = {0.3811, 0.0999, 0.1897}, k = "solid"},
			Halolo__Corpo_Pastello = {c = {0.865, 0.7858, 0.9777}, k = "solid"},
			Halolo__Guance = {c = {1, 0.7014, 0.7977}, k = "solid"},
			Halolo__Labbra = {c = {0.9777, 0.6652, 0.7674}, k = "solid"},
			Halolo__Lacci = {c = {1, 1, 1}, k = "solid"},
			Halolo__Lingua = {c = {0.9547, 0.5838, 0.6652}, k = "solid"},
			Halolo__Occhi_Bianchi = {c = {0.964, 0.964, 0.9547}, k = "solid"},
			Halolo__Puntino_Addome = {c = {1, 1, 1}, k = "neon"},
			Halolo__Pupille = {c = {0.0999, 0.0999, 0.1517}, k = "solid"},
			Halolo__Riflessi = {c = {1, 1, 1}, k = "neon"},
			Halolo__Sneakers_Azzurre = {c = {0.6652, 0.8808, 1}, k = "solid"},
			Halolo__Sneakers_Gialle = {c = {1, 0.9309, 0.5838}, k = "solid"},
			Halolo__Sneakers_Rosa = {c = {1, 0.7014, 0.8267}, k = "solid"},
			Halolo__Suole = {c = {0.9867, 0.9822, 0.9731}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Idra = {
		bob = {},
		luci = {
			Idra__Luce_01 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_02 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_03 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_04 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_05 = {b0 = 0.779, b1 = 0.779, c = {1, 0.7838, 0.5474}, cyc = 1, ph = 0, r = 6.32},
			Idra__Luce_06 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_07 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_08 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
			Idra__Luce_09 = {b0 = 0.551, b1 = 0.551, c = {0.8036, 0.9824, 0.7551}, cyc = 1, ph = 0, r = 5.79},
		},
		parti = {
			Idra__Code_Ninfea = {c = {0.3133, 0.6262, 0.3133}, k = "solid"},
			Idra__Fiore_Ninfea = {c = {1, 0.8808, 0.9309}, k = "solid"},
			Idra__Luce_Oro = {c = {1, 0.7838, 0.5474}, k = "neon"},
			Idra__Luci_Fronte = {c = {0.8036, 0.9824, 0.7551}, k = "neon"},
			Idra__Occhi = {c = {0.9063, 0.7977, 0.2478}, k = "solid"},
			Idra__Pelle_Palude = {k = "tex"},
			Idra__Testa_Centrale_Oro = {c = {0.8808, 0.7674, 0.4236}, k = "solid", metallo = true},
			Idra__Testine = {c = {0.2717, 0.4845, 0.3133}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Leopardo = {
		bob = {},
		luci = {
			Leopardo__Luce_01 = {b0 = 1.191, b1 = 1.909, c = {0.6652, 1, 0.9777}, cyc = 1, ph = 0, r = 8.95},
			Leopardo__Luce_02 = {b0 = 0.636, b1 = 1.006, c = {0.3133, 0.964, 1}, cyc = 1, ph = 0, r = 6.85},
		},
		parti = {
			Leopardo__Alone_Bulbo = {c = {0.5838, 1, 0.9777}, k = "aura", p = {0.333, 1, 1, 0}, t = 0.85},
			Leopardo__Anelli_Bulbo = {c = {0.3133, 0.3492, 0.3492}, k = "solid"},
			Leopardo__Baffi = {c = {0.8543, 0.9777, 1}, k = "neon"},
			Leopardo__Bulbo = {c = {0.7014, 1, 0.9777}, k = "neon", p = {0.375, 1, 1, 0}},
			Leopardo__Naso = {c = {0.6262, 0.5064, 0.5271}, k = "solid"},
			Leopardo__Occhi = {c = {0.5838, 0.9063, 0.8808}, k = "neon"},
			Leopardo__Pelliccia_Rosette = {e = 12.8, k = "tex"},
			Leopardo__Pupilla = {c = {0, 0, 0}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Libellula = {
		bob = {},
		luci = {
			Libellula__Luce_01 = {b0 = 0.45, b1 = 1.423, c = {1, 0.8808, 0.5838}, cyc = 2, ph = 0, r = 7.82},
			Libellula__Luce_02 = {b0 = 0.551, b1 = 0.9, c = {0.5838, 0.7977, 1}, cyc = 3, ph = 0, r = 6.6},
		},
		parti = {
			Libellula__Ala_Circuito__AlaAnt_L = {ali = true, e = 16, k = "tex"},
			Libellula__Ala_Circuito__AlaAnt_R = {ali = true, e = 16, k = "tex"},
			Libellula__Ala_Circuito__AlaPost_L = {ali = true, e = 16, k = "tex"},
			Libellula__Ala_Circuito__AlaPost_R = {ali = true, e = 16, k = "tex"},
			Libellula__Aura_Bulbo = {c = {1, 0.8543, 0.4845}, k = "aura", p = {0.125, 1, 2, 0}, t = 0.85},
			Libellula__Azzurro = {c = {0.2478, 0.7014, 0.9547}, k = "solid"},
			Libellula__Bulbo = {c = {1, 0.9063, 0.6262}, k = "neon", p = {0.167, 1, 2, 0}},
			Libellula__Occhi = {c = {0.1517, 0.5838, 0.8543}, k = "solid"},
			Libellula__Oro = {c = {1, 0.7977, 0.3492}, k = "neon", p = {0.3, 1, 3, 0}},
			Libellula__Zampe = {c = {0.1517, 0.1897, 0.2478}, k = "solid"},
		},
		perni = {
			Libellula__Perno_AlaAnt_L = {
				membri = {"Libellula__Ala_Circuito__AlaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.1745, asse = "Y", cyc = 6, ph = 0},
				},
			},
			Libellula__Perno_AlaAnt_R = {
				membri = {"Libellula__Ala_Circuito__AlaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.1745, asse = "Y", cyc = 6, ph = 0},
				},
			},
			Libellula__Perno_AlaPost_L = {
				membri = {"Libellula__Ala_Circuito__AlaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.1745, asse = "Y", cyc = 6, ph = 1.2},
				},
			},
			Libellula__Perno_AlaPost_R = {
				membri = {"Libellula__Ala_Circuito__AlaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.1745, asse = "Y", cyc = 6, ph = 1.2},
				},
			},
		},
		scala = {},
	},
	Long = {
		bob = {},
		luci = {
			Long__Luce_01 = {b0 = 0.854, b1 = 0.854, c = {0.8209, 0.863, 1}, cyc = 1, ph = 0, r = 6.49},
		},
		parti = {
			Long__Bocca = {c = {0.5838, 0.1517, 0.1897}, k = "solid"},
			Long__Corna_Oro = {c = {0.9063, 0.7674, 0.4845}, k = "solid", metallo = true},
			Long__Criniera = {c = {0.9547, 0.5838, 0.3133}, k = "solid"},
			Long__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			Long__Fiamme_Perla = {c = {0.8094, 0.9104, 1}, k = "neon", t = 0.3},
			Long__Gocce_Pioggia = {c = {0.8378, 0.9227, 1}, k = "neon"},
			Long__Muso_Giada = {c = {0.2717, 0.6262, 0.4845}, k = "solid"},
			Long__Occhi_Coniglio = {c = {0.7354, 0.1897, 0.2478}, k = "solid"},
			Long__Perla_Fiammeggiante = {c = {0.8891, 0.9141, 1}, k = "neon"},
			Long__Squame_Giada = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Lucertola = {
		bob = {},
		luci = {
			Lucertola__Luce_01 = {b0 = 0.779, b1 = 1.191, c = {1, 0.5838, 0.2478}, cyc = 3, ph = 0, r = 7.28},
			Lucertola__Luce_02 = {b0 = 0.636, b1 = 0.9, c = {1, 0.5838, 0.2478}, cyc = 4, ph = 1, r = 6.6},
		},
		parti = {
			Lucertola__Alucce__Aluccia_L = {ali = true, e = 8, k = "tex"},
			Lucertola__Alucce__Aluccia_R = {ali = true, e = 8, k = "tex"},
			Lucertola__Cristallo_Arancio = {c = {1, 0.5838, 0.0999}, k = "neon", p = {0.25, 1, 5, 3.1}, t = 0.2},
			Lucertola__Cristallo_Brace = {c = {1, 0.41, 0}, k = "neon", p = {0.25, 1, 4, 1.7}, t = 0.2},
			Lucertola__Cristallo_Rosso = {c = {1, 0.2209, 0}, k = "neon", p = {0.25, 1, 3, 0}, t = 0.2},
			Lucertola__Occhi = {c = {0.1517, 0.0999, 0}, k = "solid"},
			Lucertola__Pelle = {k = "tex"},
		},
		perni = {
			Lucertola__Perno_Aluccia_L = {
				membri = {"Lucertola__Alucce__Aluccia_L"},
				padre = nil,
				rot = {
					{amp = 0.4887, asse = "Y", cyc = 60, ph = 0},
				},
			},
			Lucertola__Perno_Aluccia_R = {
				membri = {"Lucertola__Alucce__Aluccia_R"},
				padre = nil,
				rot = {
					{amp = -0.4887, asse = "Y", cyc = 60, ph = 0},
				},
			},
		},
		scala = {},
	},
	Lucina = {
		bob = {},
		luci = {
			Lucina__Luce_01 = {b0 = 1.684, b1 = 2.111, c = {1, 0.865, 0.6262}, cyc = 1, ph = 0, r = 9.42},
			Lucina__Luce_02 = {b0 = 0.551, b1 = 0.712, c = {1, 0.865, 0.5657}, cyc = 1, ph = 0, r = 6.16},
		},
		parti = {
			Lucina__Alette_Luce__AlettaAnt_L = {ali = true, e = 12, k = "tex"},
			Lucina__Alette_Luce__AlettaAnt_R = {ali = true, e = 12, k = "tex"},
			Lucina__Alette_Luce__AlettaPost_L = {ali = true, e = 12, k = "tex"},
			Lucina__Alette_Luce__AlettaPost_R = {ali = true, e = 12, k = "tex"},
			Lucina__Antenna__Antenna = {c = {0.5371, 0.4614, 0.3492}, k = "solid"},
			Lucina__Attacco_Metallo__Lampadina = {c = {0.9063, 0.8808, 0.7977}, k = "solid", metallo = true},
			Lucina__Filamento__Lampadina = {c = {1, 0.8543, 0.5371}, k = "neon", p = {0.696, 1, 1, 0}},
			Lucina__Guance = {c = {1, 0.6262, 0.6262}, k = "neon"},
			Lucina__Luccichio = {c = {1, 1, 1}, k = "neon"},
			Lucina__Luce_Lampadina__Lampadina = {c = {1, 0.8808, 0.5838}, k = "aura", p = {0.688, 1, 1, 0}, t = 0.85},
			Lucina__Occhio_Bianco = {c = {0.9777, 0.9777, 0.964}, k = "solid"},
			Lucina__Pelo_Soffice = {c = {1, 0.886, 0.5064}, k = "solid"},
			Lucina__Pupilla = {c = {0.061, 0.061, 0.0999}, k = "solid"},
			Lucina__Sorriso = {c = {0.3133, 0.1517, 0.1517}, k = "solid"},
			Lucina__Vetro_Lampadina__Lampadina = {c = {1, 0.9063, 0.7014}, k = "neon", p = {0.7, 1, 1, 0}, t = 0.45},
		},
		perni = {
			Lucina__Perno_AlettaAnt_L = {
				membri = {"Lucina__Alette_Luce__AlettaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.384, asse = "Y", cyc = 8, ph = 0},
				},
			},
			Lucina__Perno_AlettaAnt_R = {
				membri = {"Lucina__Alette_Luce__AlettaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.384, asse = "Y", cyc = 8, ph = 0},
				},
			},
			Lucina__Perno_AlettaPost_L = {
				membri = {"Lucina__Alette_Luce__AlettaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.384, asse = "Y", cyc = 8, ph = 0.3},
				},
			},
			Lucina__Perno_AlettaPost_R = {
				membri = {"Lucina__Alette_Luce__AlettaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.384, asse = "Y", cyc = 8, ph = 0.3},
				},
			},
			Lucina__Perno_Antenna = {
				membri = {"Lucina__Antenna__Antenna"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "X", cyc = 2, ph = 0},
					{amp = 0.0873, asse = "Y", cyc = 1, ph = 1.3},
				},
			},
			Lucina__Perno_Lampadina = {
				membri = {"Lucina__Luce_01", "Lucina__Attacco_Metallo__Lampadina", "Lucina__Filamento__Lampadina", "Lucina__Luce_Lampadina__Lampadina", "Lucina__Vetro_Lampadina__Lampadina"},
				padre = "Lucina__Perno_Antenna",
				rot = {
					{amp = 0.4189, asse = "X", cyc = 2, ph = 0.6},
					{amp = 0.1745, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	Lupo = {
		bob = {
			Lupo__Lucciole__Lucciola_00 = {amp = 0.18, cyc = 1, ph = 6.219},
			Lupo__Lucciole__Lucciola_01 = {amp = 0.18, cyc = 1, ph = 0.089},
			Lupo__Lucciole__Lucciola_02 = {amp = 0.18, cyc = 1, ph = 4.36},
			Lupo__Lucciole__Lucciola_03 = {amp = 0.18, cyc = 2, ph = 0.214},
			Lupo__Lucciole__Lucciola_04 = {amp = 0.18, cyc = 2, ph = 0.146},
			Lupo__Lucciole__Lucciola_05 = {amp = 0.18, cyc = 1, ph = 3.468},
			Lupo__Lucciole__Lucciola_06 = {amp = 0.18, cyc = 1, ph = 0.469},
			Lupo__Lucciole__Lucciola_07 = {amp = 0.18, cyc = 1, ph = 0.77},
			Lupo__Lucciole__Lucciola_08 = {amp = 0.18, cyc = 2, ph = 1.835},
			Lupo__Lucciole__Lucciola_09 = {amp = 0.18, cyc = 2, ph = 0.169},
			Lupo__Lucciole__Lucciola_10 = {amp = 0.18, cyc = 2, ph = 0.441},
			Lupo__Lucciole__Lucciola_11 = {amp = 0.18, cyc = 1, ph = 1.135},
			Lupo__Lucciole__Lucciola_12 = {amp = 0.18, cyc = 2, ph = 1.544},
			Lupo__Lucciole__Lucciola_13 = {amp = 0.18, cyc = 1, ph = 4.294},
			Lupo__Lucciole__Lucciola_14 = {amp = 0.18, cyc = 1, ph = 6.041},
			Lupo__Lucciole__Lucciola_15 = {amp = 0.18, cyc = 1, ph = 5.883},
			Lupo__Lucciole__Lucciola_16 = {amp = 0.18, cyc = 2, ph = 0.361},
			Lupo__Lucciole__Lucciola_17 = {amp = 0.18, cyc = 1, ph = 1.072},
			Lupo__Lucciole__Lucciola_18 = {amp = 0.18, cyc = 2, ph = 0.31},
			Lupo__Lucciole__Lucciola_19 = {amp = 0.18, cyc = 1, ph = 5.651},
			Lupo__Lucciole__Lucciola_20 = {amp = 0.18, cyc = 2, ph = 3.651},
			Lupo__Lucciole__Lucciola_21 = {amp = 0.18, cyc = 1, ph = 2.402},
			Lupo__Lucciole__Lucciola_22 = {amp = 0.18, cyc = 1, ph = 5.351},
			Lupo__Lucciole__Lucciola_23 = {amp = 0.18, cyc = 1, ph = 0.839},
			Lupo__Lucciole__Lucciola_24 = {amp = 0.18, cyc = 1, ph = 0.452},
			Lupo__Lucciole__Lucciola_25 = {amp = 0.18, cyc = 2, ph = 3.103},
			Lupo__Lucciole__Lucciola_26 = {amp = 0.18, cyc = 1, ph = 3.794},
			Lupo__Lucciole__Lucciola_27 = {amp = 0.18, cyc = 2, ph = 2.915},
		},
		luci = {
			Lupo__Luce_01 = {b0 = 0.779, b1 = 1.35, c = {0.3492, 1, 0.9309}, cyc = 1, ph = 0, r = 7.65},
			Lupo__Luce_02 = {b0 = 0.636, b1 = 1.102, c = {0.3492, 1, 0.9309}, cyc = 1, ph = 0, r = 7.07},
		},
		parti = {
			Lupo__Ali_Delicate__Ali2_L = {ali = true, e = 12, k = "tex"},
			Lupo__Ali_Delicate__Ali2_R = {ali = true, e = 12, k = "tex"},
			Lupo__Ali_Delicate__Ali_L = {ali = true, e = 12, k = "tex"},
			Lupo__Ali_Delicate__Ali_R = {ali = true, e = 12, k = "tex"},
			Lupo__Corpo_Spettrale = {c = {0.7977, 0.9777, 1}, h = {0.2478, 1, 0.9163}, k = "ghost"},
			Lupo__Lucciole__Lucciola_00 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_01 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_02 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_03 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_04 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_05 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_06 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_07 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_08 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_09 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_10 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_11 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_12 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_13 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_14 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_15 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_16 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_17 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_18 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_19 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_20 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_21 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_22 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_23 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_24 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_25 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_26 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Lucciole__Lucciola_27 = {c = {0.7354, 1, 0.9309}, k = "neon", p = {0.25, 1, 3, 0}},
			Lupo__Naso = {c = {0.8808, 0.9547, 1}, h = {0.2478, 1, 0.9163}, k = "ghost"},
			Lupo__Occhi = {c = {0.7354, 1, 0.9777}, k = "neon", p = {0.571, 1, 1, 0}},
		},
		perni = {
			Lupo__Perno_Ali2_L = {
				membri = {"Lupo__Ali_Delicate__Ali2_L"},
				padre = nil,
				rot = {
					{amp = 0.2443, asse = "Y", cyc = 5, ph = 0.9},
				},
			},
			Lupo__Perno_Ali2_R = {
				membri = {"Lupo__Ali_Delicate__Ali2_R"},
				padre = nil,
				rot = {
					{amp = -0.2443, asse = "Y", cyc = 5, ph = 0.9},
				},
			},
			Lupo__Perno_Ali_L = {
				membri = {"Lupo__Ali_Delicate__Ali_L"},
				padre = nil,
				rot = {
					{amp = 0.2443, asse = "Y", cyc = 5, ph = 0},
				},
			},
			Lupo__Perno_Ali_R = {
				membri = {"Lupo__Ali_Delicate__Ali_R"},
				padre = nil,
				rot = {
					{amp = -0.2443, asse = "Y", cyc = 5, ph = 0},
				},
			},
		},
		scala = {},
	},
	Manta = {
		bob = {
			Manta__Scaglie_Luminose__Scaglia_00 = {amp = 0.15, cyc = 1, ph = 6.153},
			Manta__Scaglie_Luminose__Scaglia_01 = {amp = 0.15, cyc = 1, ph = 1.893},
			Manta__Scaglie_Luminose__Scaglia_02 = {amp = 0.15, cyc = 2, ph = 5.831},
			Manta__Scaglie_Luminose__Scaglia_03 = {amp = 0.15, cyc = 1, ph = 6.224},
			Manta__Scaglie_Luminose__Scaglia_04 = {amp = 0.15, cyc = 1, ph = 2.223},
			Manta__Scaglie_Luminose__Scaglia_05 = {amp = 0.15, cyc = 1, ph = 0.398},
			Manta__Scaglie_Luminose__Scaglia_06 = {amp = 0.15, cyc = 1, ph = 4.252},
			Manta__Scaglie_Luminose__Scaglia_07 = {amp = 0.15, cyc = 2, ph = 3.054},
			Manta__Scaglie_Luminose__Scaglia_08 = {amp = 0.15, cyc = 1, ph = 5.887},
			Manta__Scaglie_Luminose__Scaglia_09 = {amp = 0.15, cyc = 2, ph = 4.583},
			Manta__Scaglie_Luminose__Scaglia_10 = {amp = 0.15, cyc = 2, ph = 5.949},
			Manta__Scaglie_Luminose__Scaglia_11 = {amp = 0.15, cyc = 2, ph = 1.996},
			Manta__Scaglie_Luminose__Scaglia_12 = {amp = 0.15, cyc = 1, ph = 4.779},
			Manta__Scaglie_Luminose__Scaglia_13 = {amp = 0.15, cyc = 1, ph = 5.342},
			Manta__Scaglie_Luminose__Scaglia_14 = {amp = 0.15, cyc = 1, ph = 3.6},
			Manta__Scaglie_Luminose__Scaglia_15 = {amp = 0.15, cyc = 1, ph = 3.604},
			Manta__Scaglie_Luminose__Scaglia_16 = {amp = 0.15, cyc = 1, ph = 2.871},
			Manta__Scaglie_Luminose__Scaglia_17 = {amp = 0.15, cyc = 1, ph = 5.022},
			Manta__Scaglie_Luminose__Scaglia_18 = {amp = 0.15, cyc = 1, ph = 3.127},
			Manta__Scaglie_Luminose__Scaglia_19 = {amp = 0.15, cyc = 2, ph = 4.722},
			Manta__Scaglie_Luminose__Scaglia_20 = {amp = 0.15, cyc = 2, ph = 3.328},
			Manta__Scaglie_Luminose__Scaglia_21 = {amp = 0.15, cyc = 1, ph = 0.148},
		},
		luci = {
			Manta__Luce_01 = {b0 = 0.779, b1 = 1.559, c = {0.3492, 0.5838, 1}, cyc = 1, ph = 0, r = 8.14},
			Manta__Luce_02 = {b0 = 0.779, b1 = 1.423, c = {0.7674, 0.4845, 1}, cyc = 1, ph = 3.142, r = 7.82},
		},
		parti = {
			Manta__Ali_Falena_Luna__AlaAnt_L = {ali = true, e = 12, k = "tex"},
			Manta__Ali_Falena_Luna__AlaAnt_R = {ali = true, e = 12, k = "tex"},
			Manta__Ali_Falena_Luna__AlaPost_L = {ali = true, e = 12, k = "tex"},
			Manta__Ali_Falena_Luna__AlaPost_R = {ali = true, e = 12, k = "tex"},
			Manta__Occhi__Galleggiamento = {c = {0.0999, 0.0999, 0.1517}, k = "solid"},
			Manta__Ocello_Cobalto__AlaAnt_L = {c = {0.3492, 0.5838, 1}, k = "neon", p = {0.167, 1, 1, 0}},
			Manta__Ocello_Cobalto__AlaAnt_R = {c = {0.3492, 0.5838, 1}, k = "neon", p = {0.167, 1, 1, 0}},
			Manta__Ocello_Cobalto__AlaPost_L = {c = {0.3492, 0.5838, 1}, k = "neon", p = {0.167, 1, 1, 0}},
			Manta__Ocello_Cobalto__AlaPost_R = {c = {0.3492, 0.5838, 1}, k = "neon", p = {0.167, 1, 1, 0}},
			Manta__Ocello_Viola__AlaAnt_L = {c = {0.7674, 0.4845, 1}, k = "neon", p = {0.167, 1, 1, 3.142}},
			Manta__Ocello_Viola__AlaAnt_R = {c = {0.7674, 0.4845, 1}, k = "neon", p = {0.167, 1, 1, 3.142}},
			Manta__Ocello_Viola__AlaPost_L = {c = {0.7674, 0.4845, 1}, k = "neon", p = {0.167, 1, 1, 3.142}},
			Manta__Ocello_Viola__AlaPost_R = {c = {0.7674, 0.4845, 1}, k = "neon", p = {0.167, 1, 1, 3.142}},
			Manta__Pelle__Galleggiamento = {k = "tex"},
			Manta__Scaglie_Luminose__Scaglia_00 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_01 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_02 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_03 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_04 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_05 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_06 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_07 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_08 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_09 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_10 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_11 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_12 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_13 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_14 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_15 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_16 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_17 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_18 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_19 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_20 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
			Manta__Scaglie_Luminose__Scaglia_21 = {c = {0.6652, 0.8808, 1}, k = "neon", p = {0.286, 1, 2, 0}},
		},
		perni = {
			Manta__Perno_AlaAnt_L = {
				membri = {"Manta__Ali_Falena_Luna__AlaAnt_L", "Manta__Ocello_Cobalto__AlaAnt_L", "Manta__Ocello_Viola__AlaAnt_L"},
				padre = "Manta__Perno_Galleggiamento",
				rot = {
					{amp = 0.2793, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Manta__Perno_AlaAnt_R = {
				membri = {"Manta__Ali_Falena_Luna__AlaAnt_R", "Manta__Ocello_Cobalto__AlaAnt_R", "Manta__Ocello_Viola__AlaAnt_R"},
				padre = "Manta__Perno_Galleggiamento",
				rot = {
					{amp = -0.2793, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Manta__Perno_AlaPost_L = {
				membri = {"Manta__Ali_Falena_Luna__AlaPost_L", "Manta__Ocello_Cobalto__AlaPost_L", "Manta__Ocello_Viola__AlaPost_L"},
				padre = "Manta__Perno_Galleggiamento",
				rot = {
					{amp = 0.2793, asse = "Y", cyc = 1, ph = 0.25},
				},
			},
			Manta__Perno_AlaPost_R = {
				membri = {"Manta__Ali_Falena_Luna__AlaPost_R", "Manta__Ocello_Cobalto__AlaPost_R", "Manta__Ocello_Viola__AlaPost_R"},
				padre = "Manta__Perno_Galleggiamento",
				rot = {
					{amp = -0.2793, asse = "Y", cyc = 1, ph = 0.25},
				},
			},
			Manta__Perno_Galleggiamento = {
				membri = {"Manta__Luce_01", "Manta__Luce_02", "Manta__Occhi__Galleggiamento", "Manta__Pelle__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0698, asse = "Y", cyc = 1, ph = 2.2},
					{amp = 0.3, asse = "Z", cyc = 1, mov = true, ph = 0},
				},
			},
		},
		scala = {},
	},
	Mantide = {
		bob = {},
		luci = {
			Mantide__Luce_01 = {b0 = 0.779, b1 = 1.743, c = {1, 0.7354, 0.3811}, cyc = 2, ph = 0, r = 8.57},
			Mantide__Luce_02 = {b0 = 0.636, b1 = 0.9, c = {1, 0.7674, 0.4845}, cyc = 1, ph = 0, r = 6.6},
		},
		parti = {
			Mantide__Addome_Pulsante = {c = {1, 0.5838, 0.1517}, k = "neon", p = {0.154, 1, 2, 0}},
			Mantide__Ala_Anteriore__AlaAnteriore_L = {ali = true, e = 7.2, k = "tex"},
			Mantide__Ala_Anteriore__AlaAnteriore_R = {ali = true, e = 7.2, k = "tex"},
			Mantide__Ala_Vetrata__AlaPosteriore_L = {ali = true, e = 7.2, k = "tex"},
			Mantide__Ala_Vetrata__AlaPosteriore_R = {ali = true, e = 7.2, k = "tex"},
			Mantide__Occhi = {c = {0.5371, 0.7977, 0.2478}, k = "solid"},
			Mantide__Punte = {c = {1, 0.8808, 0.5838}, k = "neon"},
			Mantide__Smeraldo = {c = {0.061, 0.5657, 0.2934}, k = "solid"},
			Mantide__Spine = {c = {1, 0.8543, 0.4845}, k = "neon"},
		},
		perni = {
			Mantide__Perno_AlaAnteriore_L = {
				membri = {"Mantide__Ala_Anteriore__AlaAnteriore_L"},
				padre = nil,
				rot = {
					{amp = 0.0524, asse = "Y", cyc = 1, ph = 0.4},
				},
			},
			Mantide__Perno_AlaAnteriore_R = {
				membri = {"Mantide__Ala_Anteriore__AlaAnteriore_R"},
				padre = nil,
				rot = {
					{amp = -0.0524, asse = "Y", cyc = 1, ph = 0.4},
				},
			},
			Mantide__Perno_AlaPosteriore_L = {
				membri = {"Mantide__Ala_Vetrata__AlaPosteriore_L"},
				padre = nil,
				rot = {
					{amp = 0.0524, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Mantide__Perno_AlaPosteriore_R = {
				membri = {"Mantide__Ala_Vetrata__AlaPosteriore_R"},
				padre = nil,
				rot = {
					{amp = -0.0524, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	Medusa = {
		bob = {},
		luci = {
			Medusa__Luce_01 = {b0 = 1.423, b1 = 2.295, c = {0.3492, 0.9547, 1}, cyc = 1, ph = 0, r = 9.85},
			Medusa__Luce_02 = {b0 = 0.779, b1 = 1.273, c = {0.5838, 0.9777, 1}, cyc = 1, ph = 1, r = 7.47},
		},
		parti = {
			Medusa__Antenne__Antenna_0 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_1 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_2 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_3 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_4 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_5 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_6 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Antenne__Antenna_7 = {c = {0.5838, 0.9777, 1}, k = "neon", p = {0.375, 1, 1, 1}},
			Medusa__Gas_Luminoso__Galleggiamento__Gas = {c = {0.3492, 0.9547, 1}, k = "aura", p = {0.429, 1, 1, 0}, t = 0.85},
			Medusa__Lanterna__Galleggiamento = {c = {0.7977, 1, 1}, k = "neon", p = {0.5, 1, 1, 0}},
			Medusa__Ombrella_Gelatina__Galleggiamento__Ombrella = {c = {0.3492, 0.9547, 1}, h = {0.3492, 0.9547, 1}, k = "ghost"},
			Medusa__Perline__Galleggiamento = {c = {0.5838, 1, 0.9777}, k = "neon", p = {0.333, 1, 2, 0}},
		},
		perni = {
			Medusa__Perno_Antenna_0 = {
				membri = {"Medusa__Antenne__Antenna_0"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 0},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 1.3},
				},
			},
			Medusa__Perno_Antenna_1 = {
				membri = {"Medusa__Antenne__Antenna_1"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 0.8},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 2.1},
				},
			},
			Medusa__Perno_Antenna_2 = {
				membri = {"Medusa__Antenne__Antenna_2"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 1.6},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 2.9},
				},
			},
			Medusa__Perno_Antenna_3 = {
				membri = {"Medusa__Antenne__Antenna_3"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 2.4},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 3.7},
				},
			},
			Medusa__Perno_Antenna_4 = {
				membri = {"Medusa__Antenne__Antenna_4"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 3.2},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 4.5},
				},
			},
			Medusa__Perno_Antenna_5 = {
				membri = {"Medusa__Antenne__Antenna_5"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 4},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 5.3},
				},
			},
			Medusa__Perno_Antenna_6 = {
				membri = {"Medusa__Antenne__Antenna_6"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 4.8},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 6.1},
				},
			},
			Medusa__Perno_Antenna_7 = {
				membri = {"Medusa__Antenne__Antenna_7"},
				padre = "Medusa__Perno_Galleggiamento",
				rot = {
					{amp = 0.1222, asse = "X", cyc = 1, ph = 5.6},
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 6.9},
				},
			},
			Medusa__Perno_Galleggiamento = {
				membri = {"Medusa__Luce_01", "Medusa__Luce_02", "Medusa__Gas_Luminoso__Galleggiamento__Gas", "Medusa__Ombrella_Gelatina__Galleggiamento__Ombrella", "Medusa__Lanterna__Galleggiamento", "Medusa__Perline__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0524, asse = "X", cyc = 1, ph = -0.471},
					{amp = 0.0524, asse = "Y", cyc = 1, ph = 0.629},
					{amp = 0.24, asse = "Z", cyc = 1, mov = true, ph = -1.571},
				},
			},
		},
		scala = {
			Medusa__Gas_Luminoso__Galleggiamento__Gas = {cyc = 1, hi = 1.07, lo = 0.93, ph = 3.1416},
			Medusa__Ombrella_Gelatina__Galleggiamento__Ombrella = {cyc = 1, hi = 1.07, lo = 0.93, ph = 3.1416},
		},
	},
	Michele = {
		bob = {},
		luci = {
			Michele__Luce_01 = {b0 = 0.986, b1 = 0.986, c = {0.8628, 0.8904, 1}, cyc = 1, ph = 0, r = 6.8},
			Michele__Luce_02 = {b0 = 0.27, b1 = 0.27, c = {0.8628, 0.8904, 1}, cyc = 1, ph = 0, r = 5.13},
			Michele__Luce_03 = {b0 = 0.27, b1 = 0.27, c = {0.8628, 0.8904, 1}, cyc = 1, ph = 0, r = 5.13},
		},
		parti = {
			Michele__Catene = {c = {0.8543, 0.865, 0.8962}, k = "solid", metallo = true},
			Michele__Corpo_Acciaio = {c = {0.3811, 0.3959, 0.4366}, k = "solid", metallo = true},
			Michele__Occhi = {c = {0.8628, 0.8904, 1}, k = "neon"},
			Michele__Piatti_Bilancia = {c = {0.8808, 0.865, 0.7977}, k = "solid", metallo = true},
			Michele__Placche_Armatura = {c = {0.8095, 0.8323, 0.8756}, k = "solid", metallo = true},
			Michele__Scudo_Stella = {c = {0.8628, 0.8904, 1}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	OcchioFluttuante = {
		bob = {},
		luci = {
			OcchioFluttuante__Luce_01 = {ang = 34, b0 = 8.419, b1 = 8.419, c = {0.9309, 1, 0.2717}, cyc = 1, dir = "OcchioFluttuante__Luce_01_Dir", ph = 0, r = 24.14},
			OcchioFluttuante__Luce_02 = {b0 = 0.854, b1 = 0.854, c = {0.9309, 1, 0.2717}, cyc = 1, ph = 0, r = 6.49},
		},
		parti = {
			OcchioFluttuante__Cornea = {c = {0.9777, 1, 0.9547}, k = "glass", t = 0.7},
			OcchioFluttuante__Fascio_Volumetrico = {c = {0.9309, 1, 0.2717}, k = "aura", t = 0.85},
			OcchioFluttuante__Iride_Lampadina = {c = {0.9309, 1, 0.2717}, k = "neon"},
			OcchioFluttuante__Muscoli = {c = {0.7014, 0.2717, 0.2717}, k = "solid"},
			OcchioFluttuante__Nervo_Ottico = {k = "tex"},
			OcchioFluttuante__Sclera_Bagnata = {k = "tex"},
			OcchioFluttuante__Vasi = {c = {0.6262, 0.0999, 0.1517}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Ofanim = {
		bob = {},
		luci = {
			Ofanim__Luce_01 = {b0 = 0.604, b1 = 0.604, c = {0.8403, 0.8758, 1}, cyc = 1, ph = 0, r = 5.91},
			Ofanim__Luce_02 = {b0 = 0.604, b1 = 0.604, c = {0.8403, 0.8758, 1}, cyc = 1, ph = 0, r = 5.91},
			Ofanim__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {0.8403, 0.8758, 1}, cyc = 1, ph = 0, r = 5.91},
			Ofanim__Luce_04 = {b0 = 0.604, b1 = 0.604, c = {0.8403, 0.8758, 1}, cyc = 1, ph = 0, r = 5.91},
			Ofanim__Luce_05 = {b0 = 0.604, b1 = 0.604, c = {1, 0.8712, 0.7375}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			Ofanim__Alucce = {ali = true, e = 24, k = "tex"},
			Ofanim__Anello_Cristallo = {e = 24, k = "tex"},
			Ofanim__Anello_Interno = {e = 24, k = "tex"},
			Ofanim__Chitina = {c = {0.5371, 0.6012, 0.7674}, k = "solid"},
			Ofanim__Iridi_Oro = {c = {1, 0.8712, 0.7375}, k = "neon"},
			Ofanim__Occhi_Bianco = {c = {0.9547, 0.9453, 0.9063}, k = "solid"},
			Ofanim__Pupille = {c = {0.0999, 0.0999, 0.1517}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Orso = {
		bob = {},
		luci = {
			Orso__Luce_01 = {b0 = 0.636, b1 = 1.8, c = {0.3133, 1, 0.68}, cyc = 1, ph = 0, r = 8.7},
			Orso__Luce_02 = {b0 = 0.636, b1 = 1.8, c = {0.1897, 0.9309, 1}, cyc = 1, ph = -2.094, r = 8.7},
			Orso__Luce_03 = {b0 = 0.636, b1 = 1.8, c = {0.7354, 0.4845, 1}, cyc = 1, ph = -4.189, r = 8.7},
			Orso__Luce_04 = {b0 = 0.636, b1 = 1.102, c = {0.4845, 0.9547, 1}, cyc = 2, ph = 0, r = 7.07},
		},
		parti = {
			Orso__Ali_Aurora__AlaAnt_L = {ali = true, e = 12.8, k = "tex"},
			Orso__Ali_Aurora__AlaAnt_R = {ali = true, e = 12.8, k = "tex"},
			Orso__Ali_Aurora__AlaPost_L = {ali = true, e = 12.8, k = "tex"},
			Orso__Ali_Aurora__AlaPost_R = {ali = true, e = 12.8, k = "tex"},
			Orso__Artigli = {c = {0.1897, 0.1897, 0.206}, k = "solid"},
			Orso__Naso = {c = {0.0999, 0.0999, 0.1284}, k = "solid"},
			Orso__Occhi = {c = {0.061, 0.061, 0.0999}, k = "solid"},
			Orso__Pelliccia_Aurora = {
				cc = {
					cyc = 1,
					pal = {{0.3133, 1, 0.68}, {0.1897, 0.9309, 1}, {0.3492, 1, 0.865}, {0.7354, 0.4845, 1}},
					ph = 0,
				},
				e = 9.6,
				h = {0.1897, 0.9309, 1},
				k = "tex",
			},
		},
		perni = {
			Orso__Perno_AlaAnt_L = {
				membri = {"Orso__Ali_Aurora__AlaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.1571, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Orso__Perno_AlaAnt_R = {
				membri = {"Orso__Ali_Aurora__AlaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.1571, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Orso__Perno_AlaPost_L = {
				membri = {"Orso__Ali_Aurora__AlaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.1571, asse = "Y", cyc = 1, ph = 0.35},
				},
			},
			Orso__Perno_AlaPost_R = {
				membri = {"Orso__Ali_Aurora__AlaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.1571, asse = "Y", cyc = 1, ph = 0.35},
				},
			},
		},
		scala = {},
	},
	Ourobo = {
		bob = {},
		luci = {
			Ourobo__Luce_01 = {b0 = 0.427, b1 = 0.427, c = {0.7977, 0.9309, 1}, cyc = 1, ph = 0, r = 5.5},
			Ourobo__Luce_02 = {b0 = 0.427, b1 = 0.427, c = {1, 0.8543, 0.9063}, cyc = 1, ph = 0, r = 5.5},
			Ourobo__Luce_03 = {b0 = 0.427, b1 = 0.427, c = {0.7977, 0.9309, 1}, cyc = 1, ph = 0, r = 5.5},
			Ourobo__Luce_04 = {b0 = 0.427, b1 = 0.427, c = {1, 0.8543, 0.9063}, cyc = 1, ph = 0, r = 5.5},
			Ourobo__Luce_05 = {b0 = 0.427, b1 = 0.427, c = {0.7977, 0.9309, 1}, cyc = 1, ph = 0, r = 5.5},
		},
		parti = {
			Ourobo__Alucce = {ali = true, e = 24, k = "tex"},
			Ourobo__Anello_Cromatico = {e = 32, k = "tex"},
			Ourobo__Lacci = {c = {1, 1, 1}, k = "solid"},
			Ourobo__Occhi_Bianchi = {c = {0.964, 0.964, 0.9547}, k = "solid"},
			Ourobo__Pupille = {c = {0.0999, 0.0999, 0.1517}, k = "solid"},
			Ourobo__Riflessi = {c = {1, 1, 1}, k = "neon"},
			Ourobo__Sneakers = {c = {0.6262, 0.5838, 0.9777}, k = "solid"},
			Ourobo__Sopracciglia = {c = {0.3492, 0.2478, 0.4236}, k = "solid"},
			Ourobo__Striscia = {c = {1, 0.6652, 0.8543}, k = "solid"},
			Ourobo__Suole = {c = {0.9867, 0.9822, 0.9731}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Persefone = {
		bob = {},
		luci = {
			Persefone__Luce_01 = {b0 = 0.493, b1 = 0.493, c = {1, 0.3492, 0.3811}, cyc = 1, ph = 0, r = 5.65},
			Persefone__Luce_02 = {b0 = 0.312, b1 = 0.312, c = {1, 0.3492, 0.3811}, cyc = 1, ph = 0, r = 5.23},
		},
		parti = {
			Persefone__Albedo = {c = {0.9547, 0.8962, 0.8095}, k = "solid"},
			Persefone__Ali_Sottili = {ali = true, e = 2.4, k = "tex"},
			Persefone__Buccia_Melagrana = {k = "tex"},
			Persefone__Chitina_Prugna = {c = {0.3811, 0.1428, 0.2478}, k = "solid"},
			Persefone__Fiori_Centro = {c = {0.7977, 1, 0.5371}, k = "neon"},
			Persefone__Fiori_Petali = {c = {1, 0.9317, 0.8833}, k = "neon"},
			Persefone__Oro = {c = {1, 0.865, 0.5838}, k = "solid", metallo = true},
			Persefone__Semi_Rubino = {c = {1, 0.2478, 0.3492}, k = "neon"},
			Persefone__Spighe_Grano = {c = {0.9309, 0.7977, 0.5064}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Pescatrice = {
		bob = {},
		luci = {
			Pescatrice__Luce_01 = {b0 = 0.779, b1 = 1.35, c = {0.8808, 1, 0.5371}, cyc = 6, ph = 0, r = 7.65},
			Pescatrice__Luce_02 = {b0 = 0.551, b1 = 0.9, c = {0.8808, 1, 0.5371}, cyc = 6, ph = 0, r = 6.6},
			Pescatrice__Luce_03 = {b0 = 1.273, b1 = 1.273, c = {0.6652, 0.8543, 1}, cyc = 1, ph = 0, r = 7.47},
		},
		parti = {
			Pescatrice__Alone_Esca__Esca = {c = {0.8808, 1, 0.5371}, k = "aura", p = {0.25, 1, 6, 0}, t = 0.85},
			Pescatrice__Bocca__Galleggiamento = {c = {0.2717, 0.0999, 0.1284}, k = "solid"},
			Pescatrice__Denti__Galleggiamento = {c = {0.9163, 0.9063, 0.8543}, k = "solid"},
			Pescatrice__Esca_Vetro_Organico__Esca = {c = {0.8808, 1, 0.7977}, k = "glass", t = 0.55},
			Pescatrice__Lucciola_Ali__Lucciola_Ala_L = {ali = true, e = 2.4, k = "tex"},
			Pescatrice__Lucciola_Ali__Lucciola_Ala_R = {ali = true, e = 2.4, k = "tex"},
			Pescatrice__Lucciola_Corpo__Esca = {c = {0.1897, 0.1718, 0.1517}, k = "solid"},
			Pescatrice__Lucciola_Lanterna__Esca = {c = {0.8808, 1, 0.5371}, k = "neon", p = {0.375, 1, 6, 0}},
			Pescatrice__Lucciola_Pronoto__Esca = {c = {0.9309, 0.5371, 0.3133}, k = "solid"},
			Pescatrice__Occhi__Galleggiamento = {c = {0.3811, 0.4236, 0.4614}, k = "solid"},
			Pescatrice__Pelle_Abissale__Esca = {k = "tex"},
			Pescatrice__Pelle_Abissale__Galleggiamento = {k = "tex"},
			Pescatrice__Pelle_Abissale__Illicio = {k = "tex"},
			Pescatrice__Pinne__Galleggiamento = {c = {0.2209, 0.206, 0.206}, k = "solid"},
		},
		perni = {
			Pescatrice__Perno_Esca = {
				membri = {"Pescatrice__Luce_01", "Pescatrice__Alone_Esca__Esca", "Pescatrice__Esca_Vetro_Organico__Esca", "Pescatrice__Lucciola_Corpo__Esca", "Pescatrice__Lucciola_Lanterna__Esca", "Pescatrice__Lucciola_Pronoto__Esca", "Pescatrice__Pelle_Abissale__Esca"},
				padre = "Pescatrice__Perno_Illicio",
				rot = {
					{amp = 0.1745, asse = "X", cyc = 2, ph = 0},
					{amp = 0.1396, asse = "Y", cyc = 1, ph = 1},
				},
			},
			Pescatrice__Perno_Galleggiamento = {
				membri = {"Pescatrice__Luce_02", "Pescatrice__Luce_03", "Pescatrice__Bocca__Galleggiamento", "Pescatrice__Denti__Galleggiamento", "Pescatrice__Occhi__Galleggiamento", "Pescatrice__Pelle_Abissale__Galleggiamento", "Pescatrice__Pinne__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0349, asse = "X", cyc = 1, ph = 1.1},
					{amp = 0.15, asse = "Z", cyc = 1, mov = true, ph = 0},
				},
			},
			Pescatrice__Perno_Illicio = {
				membri = {"Pescatrice__Pelle_Abissale__Illicio"},
				padre = "Pescatrice__Perno_Galleggiamento",
				rot = {
					{amp = 0.0698, asse = "X", cyc = 1, ph = 0.5},
				},
			},
			Pescatrice__Perno_Lucciola_Ala_L = {
				membri = {"Pescatrice__Lucciola_Ali__Lucciola_Ala_L"},
				padre = "Pescatrice__Perno_Esca",
				rot = {
					{amp = 0.6981, asse = "Y", cyc = 60, ph = 0},
				},
			},
			Pescatrice__Perno_Lucciola_Ala_R = {
				membri = {"Pescatrice__Lucciola_Ali__Lucciola_Ala_R"},
				padre = "Pescatrice__Perno_Esca",
				rot = {
					{amp = -0.6981, asse = "Y", cyc = 60, ph = 0},
				},
			},
		},
		scala = {},
	},
	Pinguino = {
		bob = {},
		luci = {
			Pinguino__Luce_01 = {b0 = 1.35, b1 = 1.8, c = {0.5838, 0.865, 1}, cyc = 1, ph = 0, r = 8.7},
			Pinguino__Luce_02 = {ang = 110, b0 = 2.25, b1 = 3.019, c = {0.5838, 0.865, 1}, cyc = 1, dir = "Pinguino__Luce_02_Dir", ph = 0, r = 11.54},
		},
		parti = {
			Pinguino__Ali_Brinate__Aluccia2_L = {ali = true, e = 8.8, k = "tex"},
			Pinguino__Ali_Brinate__Aluccia2_R = {ali = true, e = 8.8, k = "tex"},
			Pinguino__Ali_Brinate__Aluccia_L = {ali = true, e = 8.8, k = "tex"},
			Pinguino__Ali_Brinate__Aluccia_R = {ali = true, e = 8.8, k = "tex"},
			Pinguino__Alone = {c = {0.5838, 0.865, 1}, k = "aura", p = {0.429, 1, 1, 0}, t = 0.85},
			Pinguino__Anello_Occhio = {c = {0.9547, 0.9686, 0.9867}, k = "solid"},
			Pinguino__Arancio = {c = {0.9777, 0.68, 0.2717}, k = "solid"},
			Pinguino__Becco = {c = {0.1897, 0.1897, 0.206}, k = "solid"},
			Pinguino__Lastra_Ghiaccio = {c = {0.7674, 0.8962, 0.9777}, k = "solid", m = "Ice"},
			Pinguino__Nucleo_Luce = {c = {0.7014, 0.9163, 1}, k = "neon", p = {0.5, 1, 1, 0}},
			Pinguino__Occhi = {c = {0.061, 0.061, 0.0999}, k = "solid"},
			Pinguino__Pancia_Vetro = {c = {0.5838, 0.865, 1}, k = "glass", t = 0.3},
			Pinguino__Piumaggio = {k = "tex"},
			Pinguino__Segmenti_Vetro = {c = {0.7674, 0.9309, 1}, k = "neon", p = {0.5, 1, 1, 0}},
		},
		perni = {
			Pinguino__Perno_Aluccia2_L = {
				membri = {"Pinguino__Ali_Brinate__Aluccia2_L"},
				padre = nil,
				rot = {
					{amp = 0.4189, asse = "Y", cyc = 20, ph = 1.2},
				},
			},
			Pinguino__Perno_Aluccia2_R = {
				membri = {"Pinguino__Ali_Brinate__Aluccia2_R"},
				padre = nil,
				rot = {
					{amp = -0.4189, asse = "Y", cyc = 20, ph = 1.2},
				},
			},
			Pinguino__Perno_Aluccia_L = {
				membri = {"Pinguino__Ali_Brinate__Aluccia_L"},
				padre = nil,
				rot = {
					{amp = 0.4189, asse = "Y", cyc = 20, ph = 0},
				},
			},
			Pinguino__Perno_Aluccia_R = {
				membri = {"Pinguino__Ali_Brinate__Aluccia_R"},
				padre = nil,
				rot = {
					{amp = -0.4189, asse = "Y", cyc = 20, ph = 0},
				},
			},
		},
		scala = {},
	},
	Pipistrello = {
		bob = {},
		luci = {
			Pipistrello__Luce_01 = {b0 = 0.22, b1 = 0.22, c = {1, 0.2209, 0.1897}, cyc = 1, ph = 0, r = 5.01},
			Pipistrello__Luce_02 = {b0 = 0.22, b1 = 0.22, c = {1, 0.2209, 0.1897}, cyc = 1, ph = 0, r = 5.01},
			Pipistrello__Luce_03 = {b0 = 1.304, b1 = 1.304, c = {0.8808, 0, 0.206}, cyc = 1, ph = 0, r = 7.54},
			Pipistrello__Luce_04 = {b0 = 0.697, b1 = 0.697, c = {0.8808, 0, 0.206}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Pipistrello__Alone_Cremisi = {c = {0.8808, 0, 0.206}, k = "aura", t = 0.85},
			Pipistrello__Fiala_Vetro = {c = {0.9777, 0.9547, 0.964}, k = "glass", t = 0.7},
			Pipistrello__Ghiera_Metallo = {c = {0.8095, 0.7977, 0.8095}, k = "solid", metallo = true},
			Pipistrello__Membrana_Cuoio = {k = "tex"},
			Pipistrello__Occhi_Cremisi = {c = {1, 0.2209, 0.1897}, k = "neon"},
			Pipistrello__Orecchio_Interno = {c = {0.4845, 0.2348, 0.2601}, k = "solid"},
			Pipistrello__Ossa_Ali = {c = {0.1517, 0.1177, 0.1232}, k = "solid"},
			Pipistrello__Pelle_Muso = {c = {0.2478, 0.1517, 0.1718}, k = "solid"},
			Pipistrello__Pelo_Nero = {c = {0.0861, 0.0785, 0.0861}, k = "solid"},
			Pipistrello__Sangue_Luminoso = {c = {0.8808, 0, 0.206}, k = "neon", t = 0.2},
			Pipistrello__Zanne = {c = {0.9547, 0.9405, 0.8962}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Pupazzo = {
		bob = {},
		luci = {
			Pupazzo__Luce_01 = {
				b0 = 0.779,
				b1 = 1.273,
				c = {1, 0, 0},
				cc = {
					cyc = 12,
					pal = {{1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0, 1, 1}, {0, 0, 1}, {1, 0, 1}},
					ph = 0.8,
				},
				cyc = 6,
				ph = 0,
				r = 7.47,
			},
			Pupazzo__Luce_02 = {
				b0 = 1.006,
				b1 = 1.006,
				c = {1, 0, 0},
				cc = {
					cyc = 12,
					pal = {{1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0, 1, 1}, {0, 0, 1}, {1, 0, 1}},
					ph = 0.8,
				},
				cyc = 1,
				ph = 0,
				r = 6.85,
			},
		},
		parti = {
			Pupazzo__Alone_LED__Testa = {
				c = {1, 0, 0},
				cc = {
					cyc = 12,
					pal = {{1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0, 1, 1}, {0, 0, 1}, {1, 0, 1}},
					ph = 0.8,
				},
				k = "aura",
				t = 0.85,
			},
			Pupazzo__Alucce_Mosca__Aluccia_L = {ali = true, e = 2, k = "tex"},
			Pupazzo__Alucce_Mosca__Aluccia_R = {ali = true, e = 2, k = "tex"},
			Pupazzo__Bocca__Testa = {c = {0.2478, 0.0999, 0.1517}, k = "solid"},
			Pupazzo__Carbone = {c = {0.1517, 0.1517, 0.1601}, k = "solid", m = "Slate"},
			Pupazzo__Carbone__Testa = {c = {0.1517, 0.1517, 0.1601}, k = "solid", m = "Slate"},
			Pupazzo__Gocce_Ghiaccio = {c = {0.7977, 0.9309, 1}, k = "neon", t = 0.2},
			Pupazzo__LED_Piedini__Testa = {c = {0.9063, 0.9063, 0.9163}, k = "solid", metallo = true},
			Pupazzo__LED_RGB__Testa = {
				c = {1, 0, 0},
				cc = {
					cyc = 12,
					pal = {{1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0, 1, 1}, {0, 0, 1}, {1, 0, 1}},
					ph = 0.8,
				},
				k = "neon",
			},
			Pupazzo__Neve_Bagnata = {c = {0.9357, 0.9547, 0.9867}, k = "solid", m = "Snow"},
			Pupazzo__Neve_Bagnata__Collo = {c = {0.9357, 0.9547, 0.9867}, k = "solid", m = "Snow"},
			Pupazzo__Neve_Bagnata__Testa = {c = {0.9357, 0.9547, 0.9867}, k = "solid", m = "Snow"},
			Pupazzo__Pozzanghera = {c = {0.1517, 0.1897, 0.2478}, k = "solid", m = "Glass", rifl = 0.5},
			Pupazzo__Rametti__Testa = {c = {0.4614, 0.3492, 0.2478}, k = "solid"},
			Pupazzo__Zampette = {c = {0.2209, 0.2209, 0.2478}, k = "solid"},
		},
		perni = {
			Pupazzo__Perno_Aluccia_L = {
				membri = {"Pupazzo__Alucce_Mosca__Aluccia_L"},
				padre = nil,
				rot = {
					{amp = 0.2443, asse = "Y", cyc = 16, ph = 0},
				},
			},
			Pupazzo__Perno_Aluccia_R = {
				membri = {"Pupazzo__Alucce_Mosca__Aluccia_R"},
				padre = nil,
				rot = {
					{amp = -0.2443, asse = "Y", cyc = 16, ph = 0},
				},
			},
			Pupazzo__Perno_Collo = {
				membri = {"Pupazzo__Neve_Bagnata__Collo"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "X", cyc = 2, ph = 0},
					{amp = 0.1571, asse = "Y", cyc = 1, ph = 1.1},
				},
			},
			Pupazzo__Perno_Testa = {
				membri = {"Pupazzo__Luce_01", "Pupazzo__Alone_LED__Testa", "Pupazzo__Bocca__Testa", "Pupazzo__Carbone__Testa", "Pupazzo__LED_Piedini__Testa", "Pupazzo__LED_RGB__Testa", "Pupazzo__Neve_Bagnata__Testa", "Pupazzo__Rametti__Testa"},
				padre = "Pupazzo__Perno_Collo",
				rot = {
					{amp = 0.1396, asse = "X", cyc = 2, ph = 2},
					{amp = 0.2443, asse = "Y", cyc = 3, ph = 0.4},
				},
			},
		},
		scala = {},
	},
	Quetzal = {
		bob = {},
		luci = {
			Quetzal__Luce_01 = {b0 = 0.697, b1 = 0.697, c = {1, 0.9751, 0.9967}, cyc = 1, ph = 0, r = 6.13},
			Quetzal__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {0.3035, 0.9429, 0.7977}, cyc = 1, ph = 0, r = 6.13},
			Quetzal__Luce_03 = {b0 = 0.697, b1 = 0.697, c = {0.3035, 0.9429, 0.7977}, cyc = 1, ph = 0, r = 6.13},
			Quetzal__Luce_04 = {b0 = 0.697, b1 = 0.697, c = {0.3035, 0.9429, 0.7977}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Quetzal__Bocca = {c = {0.6652, 0.1897, 0.2478}, k = "solid"},
			Quetzal__Occhi = {c = {1, 0.8808, 0.3492}, k = "neon"},
			Quetzal__Petto_Rosso = {c = {0.8543, 0.2478, 0.2478}, k = "solid"},
			Quetzal__Piume_Coda = {e = 12, k = "tex"},
			Quetzal__Piume_Smeraldo = {e = 12, k = "tex"},
			Quetzal__Squame = {e = 24, k = "tex"},
			Quetzal__Testa = {c = {0.1897, 0.5838, 0.41}, k = "solid"},
			Quetzal__Zanne = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Raffaele = {
		bob = {},
		luci = {
			Raffaele__Luce_01 = {b0 = 0.779, b1 = 0.779, c = {0.4845, 1, 0.7354}, cyc = 1, ph = 0, r = 6.32},
			Raffaele__Luce_02 = {b0 = 0.604, b1 = 0.604, c = {0.4845, 1, 0.7354}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			Raffaele__Ali_Verdi = {ali = true, e = 24, k = "tex"},
			Raffaele__Bastone = {c = {0.5838, 0.5064, 0.3492}, k = "solid"},
			Raffaele__Bisaccia = {c = {0.5371, 0.41, 0.2934}, k = "solid"},
			Raffaele__Chitina = {c = {0.1897, 0.3811, 0.2934}, k = "solid"},
			Raffaele__Conchiglia = {c = {0.9777, 0.9063, 0.7674}, k = "solid"},
			Raffaele__Occhi = {c = {0.4845, 1, 0.7354}, k = "neon"},
			Raffaele__Sacca_Pesce = {c = {0.4845, 1, 0.7354}, k = "neon", t = 0.2},
			Raffaele__Serpentello = {c = {0.3133, 0.7014, 0.4845}, k = "solid"},
			Raffaele__Torace_Smeraldo = {c = {0.4845, 1, 0.7354}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	Rana = {
		bob = {},
		luci = {
			Rana__Luce_01 = {b0 = 0.45, b1 = 1.559, c = {1, 0.6652, 0.2478}, cyc = 2, ph = 0, r = 8.14},
			Rana__Luce_02 = {b0 = 0.45, b1 = 0.779, c = {1, 0.7014, 0.3133}, cyc = 2, ph = 2.1, r = 6.32},
		},
		parti = {
			Rana__Ali_Insetto__AlaDorso2_L = {ali = true, e = 7.2, k = "tex"},
			Rana__Ali_Insetto__AlaDorso2_R = {ali = true, e = 7.2, k = "tex"},
			Rana__Ali_Insetto__AlaDorso_L = {ali = true, e = 7.2, k = "tex"},
			Rana__Ali_Insetto__AlaDorso_R = {ali = true, e = 7.2, k = "tex"},
			Rana__Ali_Insetto__AlaFianco_L = {ali = true, e = 7.2, k = "tex"},
			Rana__Ali_Insetto__AlaFianco_R = {ali = true, e = 7.2, k = "tex"},
			Rana__Bulbilli = {c = {1, 0.7674, 0.3133}, k = "neon", p = {0.5, 1, 2, 1}},
			Rana__Iride = {c = {0.9547, 0.6262, 0.1517}, k = "neon"},
			Rana__Pelle_Bagnata = {k = "tex"},
			Rana__Punto_Luce_0 = {c = {1, 0.5838, 0.0999}, k = "neon", p = {0.192, 1, 2, 0}},
			Rana__Punto_Luce_1 = {c = {1, 0.5838, 0.0999}, k = "neon", p = {0.192, 1, 2, 2.1}},
			Rana__Punto_Luce_2 = {c = {1, 0.5838, 0.0999}, k = "neon", p = {0.192, 1, 2, 4.2}},
			Rana__Pupilla = {c = {0, 0, 0}, k = "solid"},
			Rana__Sacca_Vocale__SaccaVocale = {c = {1, 0.5657, 0.0999}, k = "neon", p = {0.156, 1, 2, 0}, t = 0.1},
			Rana__Ventre = {c = {0.2717, 0.3133, 0.206}, k = "solid"},
		},
		perni = {
			Rana__Perno_AlaDorso2_L = {
				membri = {"Rana__Ali_Insetto__AlaDorso2_L"},
				padre = nil,
				rot = {
					{amp = 0.1745, asse = "Y", cyc = 4, ph = 0.8},
				},
			},
			Rana__Perno_AlaDorso2_R = {
				membri = {"Rana__Ali_Insetto__AlaDorso2_R"},
				padre = nil,
				rot = {
					{amp = -0.1745, asse = "Y", cyc = 4, ph = 0.8},
				},
			},
			Rana__Perno_AlaDorso_L = {
				membri = {"Rana__Ali_Insetto__AlaDorso_L"},
				padre = nil,
				rot = {
					{amp = 0.1745, asse = "Y", cyc = 4, ph = 0},
				},
			},
			Rana__Perno_AlaDorso_R = {
				membri = {"Rana__Ali_Insetto__AlaDorso_R"},
				padre = nil,
				rot = {
					{amp = -0.1745, asse = "Y", cyc = 4, ph = 0},
				},
			},
			Rana__Perno_AlaFianco_L = {
				membri = {"Rana__Ali_Insetto__AlaFianco_L"},
				padre = nil,
				rot = {
					{amp = 0.1396, asse = "Y", cyc = 4, ph = 1.6},
				},
			},
			Rana__Perno_AlaFianco_R = {
				membri = {"Rana__Ali_Insetto__AlaFianco_R"},
				padre = nil,
				rot = {
					{amp = -0.1396, asse = "Y", cyc = 4, ph = 1.6},
				},
			},
		},
		scala = {
			Rana__Sacca_Vocale__SaccaVocale = {cyc = 2, hi = 1.12, lo = 0.82, ph = 0},
		},
	},
	Renna = {
		bob = {
			Renna__Fiocchi__Fiocco_00 = {amp = 0.15, cyc = 2, ph = 0.692},
			Renna__Fiocchi__Fiocco_01 = {amp = 0.15, cyc = 2, ph = 0.864},
			Renna__Fiocchi__Fiocco_02 = {amp = 0.15, cyc = 1, ph = 2.08},
			Renna__Fiocchi__Fiocco_03 = {amp = 0.15, cyc = 1, ph = 4.289},
			Renna__Fiocchi__Fiocco_04 = {amp = 0.15, cyc = 2, ph = 0.316},
			Renna__Fiocchi__Fiocco_05 = {amp = 0.15, cyc = 1, ph = 3.311},
			Renna__Fiocchi__Fiocco_06 = {amp = 0.15, cyc = 1, ph = 1.572},
			Renna__Fiocchi__Fiocco_07 = {amp = 0.15, cyc = 2, ph = 0.061},
			Renna__Fiocchi__Fiocco_08 = {amp = 0.15, cyc = 2, ph = 1.622},
			Renna__Fiocchi__Fiocco_09 = {amp = 0.15, cyc = 2, ph = 4.597},
			Renna__Fiocchi__Fiocco_10 = {amp = 0.15, cyc = 1, ph = 5.701},
			Renna__Fiocchi__Fiocco_11 = {amp = 0.15, cyc = 1, ph = 5.818},
			Renna__Fiocchi__Fiocco_12 = {amp = 0.15, cyc = 1, ph = 3.412},
			Renna__Fiocchi__Fiocco_13 = {amp = 0.15, cyc = 2, ph = 3.685},
			Renna__Fiocchi__Fiocco_14 = {amp = 0.15, cyc = 1, ph = 1.439},
			Renna__Fiocchi__Fiocco_15 = {amp = 0.15, cyc = 2, ph = 0.337},
			Renna__Fiocchi__Fiocco_16 = {amp = 0.15, cyc = 1, ph = 6.271},
			Renna__Fiocchi__Fiocco_17 = {amp = 0.15, cyc = 1, ph = 5.92},
			Renna__Fiocchi__Fiocco_18 = {amp = 0.15, cyc = 2, ph = 2.845},
			Renna__Fiocchi__Fiocco_19 = {amp = 0.15, cyc = 1, ph = 1.679},
			Renna__Fiocchi__Fiocco_20 = {amp = 0.15, cyc = 1, ph = 4.889},
			Renna__Fiocchi__Fiocco_21 = {amp = 0.15, cyc = 1, ph = 5.344},
			Renna__Fiocchi__Fiocco_22 = {amp = 0.15, cyc = 2, ph = 2.242},
			Renna__Fiocchi__Fiocco_23 = {amp = 0.15, cyc = 2, ph = 0.508},
			Renna__Fiocchi__Fiocco_24 = {amp = 0.15, cyc = 1, ph = 3.383},
			Renna__Fiocchi__Fiocco_25 = {amp = 0.15, cyc = 2, ph = 4.303},
		},
		luci = {
			Renna__Luce_01 = {b0 = 2.111, b1 = 2.624, c = {0.8543, 0.9309, 1}, cyc = 1, ph = 0, r = 10.62},
			Renna__Luce_02 = {b0 = 1.102, b1 = 1.559, c = {0.7977, 0.9063, 1}, cyc = 1, ph = 0.5, r = 8.14},
			Renna__Luce_03 = {b0 = 0.636, b1 = 0.9, c = {0.8543, 0.9309, 1}, cyc = 1, ph = 0, r = 6.6},
		},
		parti = {
			Renna__Alone_Corna = {c = {0.7977, 0.9163, 1}, k = "aura", p = {0.556, 1, 1, 0}, t = 0.85},
			Renna__Coda_Cometa = {c = {0.7354, 0.8808, 1}, k = "aura", p = {0.5, 1, 1, 0}, t = 0.85},
			Renna__Corna_Antenne = {c = {0.865, 0.9453, 1}, k = "neon", p = {0.667, 1, 1, 0}},
			Renna__Criniera = {c = {0.8808, 0.8756, 0.865}, k = "solid"},
			Renna__Fiocchi__Fiocco_00 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_01 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_02 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_03 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_04 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_05 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_06 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_07 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_08 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_09 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_10 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_11 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_12 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_13 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_14 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_15 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_16 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_17 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_18 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_19 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_20 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_21 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_22 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_23 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_24 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Fiocchi__Fiocco_25 = {c = {0.9063, 0.964, 1}, k = "neon", p = {0.375, 1, 2, 0}},
			Renna__Naso = {c = {0.2478, 0.2348, 0.2478}, k = "solid"},
			Renna__Occhi = {c = {0.0999, 0.0999, 0.1284}, k = "solid"},
			Renna__Pelo = {k = "tex"},
			Renna__Zoccoli = {c = {0.2209, 0.206, 0.1897}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Ryujin = {
		bob = {},
		luci = {
			Ryujin__Luce_01 = {b0 = 0.697, b1 = 0.697, c = {0.5288, 0.6452, 1}, cyc = 1, ph = 0, r = 6.13},
			Ryujin__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {0.9777, 0.9912, 1}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			Ryujin__Bocca = {c = {0.5371, 0.1517, 0.2478}, k = "solid"},
			Ryujin__Corna = {c = {0.9063, 0.8808, 0.7977}, k = "solid"},
			Ryujin__Criniera_Blu = {c = {0.2478, 0.5838, 0.7977}, k = "solid"},
			Ryujin__Criniera_Onda = {c = {0.8808, 0.964, 0.9777}, k = "solid"},
			Ryujin__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			Ryujin__Kanju_Luce = {c = {0.5288, 0.6452, 1}, k = "neon"},
			Ryujin__Kanju_Vetro = {c = {0.8525, 0.8806, 1}, k = "glass", t = 0.6},
			Ryujin__Manju_Luce = {c = {0.9777, 0.9912, 1}, k = "neon"},
			Ryujin__Manju_Vetro = {c = {0.9912, 0.9965, 1}, k = "glass", t = 0.6},
			Ryujin__Muso = {c = {0.2209, 0.6012, 0.6012}, k = "solid"},
			Ryujin__Occhi = {c = {1, 0.9063, 0.4845}, k = "neon"},
			Ryujin__Squame_Verde_Mare = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
	Scarabeo = {
		bob = {},
		luci = {
			Scarabeo__Luce_01 = {b0 = 2.662, b1 = 3.337, c = {1, 0.68, 0.3133}, cyc = 1, ph = 0, r = 12.29},
			Scarabeo__Luce_02 = {b0 = 1.102, b1 = 1.684, c = {1, 0.6652, 0.2717}, cyc = 1, ph = 0, r = 8.43},
			Scarabeo__Luce_03 = {b0 = 0.779, b1 = 1.273, c = {1, 0.6262, 0.2478}, cyc = 2, ph = 0, r = 7.47},
		},
		parti = {
			Scarabeo__Addome_Brace = {e = 20, k = "tex"},
			Scarabeo__Ali_Membrana__Ala_L = {ali = true, e = 7.2, k = "tex"},
			Scarabeo__Ali_Membrana__Ala_R = {ali = true, e = 7.2, k = "tex"},
			Scarabeo__Alone_Sfera = {c = {1, 0.5838, 0.1517}, k = "aura", p = {0.375, 1, 1, 0}, t = 0.85},
			Scarabeo__Guscio = {k = "tex"},
			Scarabeo__Sfera_Magma__Sfera = {e = 8.8, k = "tex"},
		},
		perni = {
			Scarabeo__Perno_Ala_L = {
				membri = {"Scarabeo__Ali_Membrana__Ala_L"},
				padre = nil,
				rot = {
					{amp = 0.1047, asse = "Y", cyc = 3, ph = 0},
				},
			},
			Scarabeo__Perno_Ala_R = {
				membri = {"Scarabeo__Ali_Membrana__Ala_R"},
				padre = nil,
				rot = {
					{amp = -0.1047, asse = "Y", cyc = 3, ph = 0},
				},
			},
			Scarabeo__Perno_Sfera = {
				membri = {"Scarabeo__Sfera_Magma__Sfera"},
				padre = nil,
				rot = {
					{amp = 0, asse = "X", cyc = -1, ph = 0, spin = true},
				},
			},
		},
		scala = {},
	},
	Scorpione = {
		bob = {},
		luci = {
			Scorpione__Luce_01 = {b0 = 1.559, b1 = 2.846, c = {1, 0.7354, 0.4236}, cyc = 2, ph = 0, r = 11.14},
			Scorpione__Luce_02 = {b0 = 1.006, b1 = 1.559, c = {1, 0.7674, 0.4845}, cyc = 2, ph = 0, r = 8.14},
		},
		parti = {
			Scorpione__Alone__Coda = {c = {1, 0.68, 0.2717}, k = "aura", p = {0.278, 1, 2, 0}, t = 0.85},
			Scorpione__Anelli_Oro__Coda = {c = {1, 0.8543, 0.5371}, k = "solid", metallo = true},
			Scorpione__Bulbo_Smerigliato__Coda = {c = {1, 0.6652, 0.2478}, k = "neon", p = {0.273, 1, 2, 0}, t = 0.2},
			Scorpione__Corazza = {e = 3.6, k = "tex"},
			Scorpione__Corazza__Coda = {e = 3.6, k = "tex"},
			Scorpione__Elitre = {c = {0.5838, 0.4492, 0.2478}, k = "solid", metallo = true},
			Scorpione__Fiamma_Interna__Coda = {c = {1, 0.7014, 0.2717}, k = "neon", p = {0.333, 1, 2, 0}},
			Scorpione__Occhi = {c = {0, 0, 0}, k = "solid"},
			Scorpione__Zampe = {e = 2, k = "tex"},
		},
		perni = {
			Scorpione__Perno_Coda = {
				membri = {"Scorpione__Luce_01", "Scorpione__Alone__Coda", "Scorpione__Anelli_Oro__Coda", "Scorpione__Bulbo_Smerigliato__Coda", "Scorpione__Corazza__Coda", "Scorpione__Fiamma_Interna__Coda"},
				padre = nil,
				rot = {
					{amp = 0.0524, asse = "X", cyc = 2, ph = 0.8},
					{amp = 0.0873, asse = "Y", cyc = 1, ph = 0},
				},
			},
		},
		scala = {},
	},
	Serafino = {
		bob = {},
		luci = {
			Serafino__Luce_01 = {b0 = 1.102, b1 = 1.102, c = {1, 0.9317, 0.8833}, cyc = 1, ph = 0, r = 7.07},
			Serafino__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {1, 0.6666, 0.3193}, cyc = 1, ph = 0, r = 6.13},
			Serafino__Luce_03 = {b0 = 0.604, b1 = 0.604, c = {1, 0.9317, 0.8833}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			Serafino__Addome_Ardente = {c = {1, 0.8317, 0.649}, k = "neon"},
			Serafino__Ali_Nervature = {ali = true, e = 24, k = "tex"},
			Serafino__Alone_Dorato = {c = {1, 0.9317, 0.8833}, k = "aura", t = 0.85},
			Serafino__Chitina_Perla = {c = {0.7354, 0.6343, 0.4236}, k = "solid"},
			Serafino__Elitre_Aperte = {c = {0.7674, 0.65, 0.3811}, k = "solid", metallo = true},
			Serafino__Nimbo = {c = {1, 0.9317, 0.8833}, k = "neon"},
			Serafino__Occhi_Composti = {c = {0.6262, 0.3811, 0.1517}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Squalo = {
		bob = {},
		luci = {
			Squalo__Luce_01 = {b0 = 0.9, b1 = 1.559, c = {0.4236, 0.7014, 1}, cyc = 2, ph = 0, r = 8.14},
			Squalo__Luce_02 = {b0 = 0.636, b1 = 1.191, c = {0.7354, 0.8808, 1}, cyc = 4, ph = 0, r = 7.28},
		},
		parti = {
			Squalo__Ali_Energia__Ala2_L = {ali = true, e = 8.8, k = "tex"},
			Squalo__Ali_Energia__Ala2_R = {ali = true, e = 8.8, k = "tex"},
			Squalo__Ali_Energia__Ala_L = {ali = true, e = 8.8, k = "tex"},
			Squalo__Ali_Energia__Ala_R = {ali = true, e = 8.8, k = "tex"},
			Squalo__Branchie__Galleggiamento = {c = {0.5371, 0.7977, 1}, k = "neon", p = {0.25, 1, 2, 0}},
			Squalo__Occhi__Galleggiamento = {c = {0.061, 0.061, 0.0999}, k = "solid"},
			Squalo__Pelle_Vasi_Plasma__Galleggiamento = {e = 10.4, k = "tex"},
			Squalo__Pinne__Coda = {c = {0.1897, 0.2209, 0.2601}, k = "solid"},
			Squalo__Pinne__Galleggiamento = {c = {0.1897, 0.2209, 0.2601}, k = "solid"},
		},
		perni = {
			Squalo__Perno_Ala2_L = {
				membri = {"Squalo__Ali_Energia__Ala2_L"},
				padre = "Squalo__Perno_Galleggiamento",
				rot = {
					{amp = 0.3142, asse = "Y", cyc = 24, ph = 1.3},
				},
			},
			Squalo__Perno_Ala2_R = {
				membri = {"Squalo__Ali_Energia__Ala2_R"},
				padre = "Squalo__Perno_Galleggiamento",
				rot = {
					{amp = -0.3142, asse = "Y", cyc = 24, ph = 1.3},
				},
			},
			Squalo__Perno_Ala_L = {
				membri = {"Squalo__Ali_Energia__Ala_L"},
				padre = "Squalo__Perno_Galleggiamento",
				rot = {
					{amp = 0.3142, asse = "Y", cyc = 24, ph = 0},
				},
			},
			Squalo__Perno_Ala_R = {
				membri = {"Squalo__Ali_Energia__Ala_R"},
				padre = "Squalo__Perno_Galleggiamento",
				rot = {
					{amp = -0.3142, asse = "Y", cyc = 24, ph = 0},
				},
			},
			Squalo__Perno_Coda = {
				membri = {"Squalo__Pinne__Coda"},
				padre = "Squalo__Perno_Galleggiamento",
				rot = {
					{amp = 0.2793, asse = "Z", cyc = 2, ph = 0},
				},
			},
			Squalo__Perno_Galleggiamento = {
				membri = {"Squalo__Luce_01", "Squalo__Luce_02", "Squalo__Branchie__Galleggiamento", "Squalo__Occhi__Galleggiamento", "Squalo__Pelle_Vasi_Plasma__Galleggiamento", "Squalo__Pinne__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0873, asse = "Y", cyc = 1, ph = 2.2},
					{amp = 0.18, asse = "Z", cyc = 1, mov = true, ph = 0},
				},
			},
		},
		scala = {},
	},
	Tarantola = {
		bob = {},
		luci = {
			Tarantola__Luce_01 = {b0 = 1.006, b1 = 1.684, c = {1, 0.6262, 0.2478}, cyc = 1, ph = 0.9, r = 8.43},
			Tarantola__Luce_02 = {b0 = 0.779, b1 = 1.191, c = {1, 0.7014, 0.3133}, cyc = 1, ph = 0, r = 7.28},
		},
		parti = {
			Tarantola__Addome_Lava = {e = 20, k = "tex"},
			Tarantola__Carapace_Sole = {e = 16, k = "tex"},
			Tarantola__Giunture_Lava = {c = {1, 0.6012, 0.1517}, k = "neon", p = {0.333, 1, 1, 0.4}},
			Tarantola__Occhi = {c = {0, 0, 0}, k = "solid"},
			Tarantola__Zampe = {e = 10, k = "tex"},
			Tarantola__Zanne = {c = {0.1517, 0.1284, 0.1121}, k = "solid"},
		},
		perni = {},
		scala = {},
	},
	Tartaruga = {
		bob = {},
		luci = {
			Tartaruga__Luce_01 = {b0 = 0.45, b1 = 1.35, c = {0.3492, 1, 0.8808}, cyc = 1, ph = -0.785, r = 7.65},
			Tartaruga__Luce_02 = {b0 = 0.45, b1 = 1.35, c = {0.3492, 1, 0.8808}, cyc = 1, ph = -3.142, r = 7.65},
			Tartaruga__Luce_03 = {b0 = 0.45, b1 = 1.35, c = {0.3492, 1, 0.8808}, cyc = 1, ph = -5.498, r = 7.65},
		},
		parti = {
			Tartaruga__Becco__Galleggiamento = {c = {0.3492, 0.3492, 0.2934}, k = "solid"},
			Tartaruga__Cella_0__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, 0}, t = 0.2},
			Tartaruga__Cella_1__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -0.785}, t = 0.2},
			Tartaruga__Cella_2__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -1.571}, t = 0.2},
			Tartaruga__Cella_3__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -2.356}, t = 0.2},
			Tartaruga__Cella_4__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -3.142}, t = 0.2},
			Tartaruga__Cella_5__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -3.927}, t = 0.2},
			Tartaruga__Cella_6__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -4.712}, t = 0.2},
			Tartaruga__Cella_7__Galleggiamento = {c = {0.3492, 1, 0.8808}, k = "neon", p = {0.114, 1, 1, -5.498}, t = 0.2},
			Tartaruga__Guscio_Base__Galleggiamento = {c = {0.1517, 0.206, 0.1897}, k = "solid"},
			Tartaruga__Occhi__Galleggiamento = {c = {0.0999, 0.1284, 0.1121}, k = "solid"},
			Tartaruga__Pelle__Galleggiamento = {k = "tex"},
			Tartaruga__Pelle__Pinna_Ant_L = {k = "tex"},
			Tartaruga__Pelle__Pinna_Ant_R = {k = "tex"},
			Tartaruga__Pelle__Pinna_Post_L = {k = "tex"},
			Tartaruga__Pelle__Pinna_Post_R = {k = "tex"},
			Tartaruga__Piastrone__Galleggiamento = {c = {0.7354, 0.7084, 0.5838}, k = "solid"},
		},
		perni = {
			Tartaruga__Perno_Galleggiamento = {
				membri = {"Tartaruga__Luce_01", "Tartaruga__Luce_02", "Tartaruga__Luce_03", "Tartaruga__Becco__Galleggiamento", "Tartaruga__Cella_0__Galleggiamento", "Tartaruga__Cella_1__Galleggiamento", "Tartaruga__Cella_2__Galleggiamento", "Tartaruga__Cella_3__Galleggiamento", "Tartaruga__Cella_4__Galleggiamento", "Tartaruga__Cella_5__Galleggiamento", "Tartaruga__Cella_6__Galleggiamento", "Tartaruga__Cella_7__Galleggiamento", "Tartaruga__Guscio_Base__Galleggiamento", "Tartaruga__Occhi__Galleggiamento", "Tartaruga__Pelle__Galleggiamento", "Tartaruga__Piastrone__Galleggiamento"},
				padre = nil,
				rot = {
					{amp = 0.0524, asse = "X", cyc = 1, ph = 1.1},
					{amp = 0.0349, asse = "Y", cyc = 1, ph = 2.2},
					{amp = 0.21, asse = "Z", cyc = 1, mov = true, ph = 0},
				},
			},
			Tartaruga__Perno_Pinna_Ant_L = {
				membri = {"Tartaruga__Pelle__Pinna_Ant_L"},
				padre = "Tartaruga__Perno_Galleggiamento",
				rot = {
					{amp = -0.384, asse = "Y", cyc = 1, ph = 0},
					{amp = -0.1745, asse = "Z", cyc = 1, ph = 1.571},
				},
			},
			Tartaruga__Perno_Pinna_Ant_R = {
				membri = {"Tartaruga__Pelle__Pinna_Ant_R"},
				padre = "Tartaruga__Perno_Galleggiamento",
				rot = {
					{amp = 0.384, asse = "Y", cyc = 1, ph = 0},
					{amp = 0.1745, asse = "Z", cyc = 1, ph = 1.571},
				},
			},
			Tartaruga__Perno_Pinna_Post_L = {
				membri = {"Tartaruga__Pelle__Pinna_Post_L"},
				padre = "Tartaruga__Perno_Galleggiamento",
				rot = {
					{amp = -0.2094, asse = "Z", cyc = 1, ph = 1},
				},
			},
			Tartaruga__Perno_Pinna_Post_R = {
				membri = {"Tartaruga__Pelle__Pinna_Post_R"},
				padre = "Tartaruga__Perno_Galleggiamento",
				rot = {
					{amp = 0.2094, asse = "Z", cyc = 1, ph = 1},
				},
			},
		},
		scala = {},
	},
	Tesorino = {
		bob = {},
		luci = {
			Tesorino__Luce_01 = {b0 = 0.697, b1 = 0.697, c = {1, 0.7247, 0.4295}, cyc = 1, ph = 0, r = 6.13},
			Tesorino__Luce_02 = {b0 = 1.102, b1 = 1.102, c = {1, 0.7247, 0.4295}, cyc = 1, ph = 0, r = 7.07},
		},
		parti = {
			Tesorino__Ali_Ripiegate = {c = {0.4614, 0.3811, 0.2478}, k = "solid"},
			Tesorino__Corna = {c = {0.5838, 0.5064, 0.3811}, k = "solid"},
			Tesorino__Lanternino_Coda = {c = {1, 0.7247, 0.4295}, k = "neon"},
			Tesorino__Monete_Oro = {c = {1, 0.865, 0.5657}, k = "solid", metallo = true},
			Tesorino__Rubino = {c = {1, 0.3492, 0.4236}, k = "glass", t = 0.6},
			Tesorino__Smeraldo = {c = {0.3492, 1, 0.6652}, k = "glass", t = 0.6},
			Tesorino__Squame = {e = 24, k = "tex"},
		},
		perni = {},
		scala = {},
	},
	TungSahur = {
		bob = {},
		luci = {
			TungSahur__Luce_01 = {b0 = 1.559, b1 = 1.559, c = {1, 0.4488, 0}, cyc = 1, ph = 0, r = 8.14},
			TungSahur__Luce_02 = {b0 = 1.207, b1 = 1.207, c = {1, 0.4488, 0}, cyc = 1, ph = 0, r = 7.32},
			TungSahur__Luce_03 = {b0 = 0.349, b1 = 0.349, c = {1, 0.2478, 0}, cyc = 1, ph = 0, r = 5.31},
			TungSahur__Luce_04 = {b0 = 0.349, b1 = 0.349, c = {1, 0.2478, 0}, cyc = 1, ph = 0, r = 5.31},
			TungSahur__Luce_05 = {b0 = 1.207, b1 = 1.207, c = {1, 0.5371, 0}, cyc = 1, ph = 0, r = 7.32},
		},
		parti = {
			TungSahur__Alucce = {ali = true, e = 8, k = "tex"},
			TungSahur__Bocca = {c = {0.2478, 0, 0}, k = "solid"},
			TungSahur__Cornetti = {c = {0.5371, 0.1517, 0.0999}, k = "solid"},
			TungSahur__Corteccia_Lava = {e = 32, k = "tex"},
			TungSahur__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			TungSahur__Iridi_Rosse = {c = {1, 0.2478, 0}, k = "neon"},
			TungSahur__Mazza_Rovente = {c = {1, 0.4614, 0}, k = "neon"},
			TungSahur__Occhi_Bianchi = {c = {0.964, 0.964, 0.9547}, k = "solid"},
			TungSahur__Pupille = {c = {0.0507, 0.0507, 0.0507}, k = "solid"},
			TungSahur__Rami = {k = "tex"},
			TungSahur__Riflessi = {c = {1, 1, 1}, k = "neon"},
			TungSahur__Sneakers_Lacci = {c = {0.9777, 0.9777, 0.9777}, k = "solid"},
			TungSahur__Sneakers_Rosse = {c = {0.8808, 0.1517, 0.1517}, k = "solid"},
			TungSahur__Sneakers_Striscia = {c = {0.1517, 0.1517, 0.1517}, k = "solid"},
			TungSahur__Sneakers_Suola = {c = {0.964, 0.9547, 0.9357}, k = "solid"},
			TungSahur__Sopracciglia = {c = {0.061, 0.0507, 0.0507}, k = "solid"},
			TungSahur__Vena_Rabbia = {c = {1, 0.2478, 0}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	VermeOhio = {
		bob = {},
		luci = {
			VermeOhio__Luce_01 = {b0 = 0.697, b1 = 0.697, c = {1, 0.0728, 0.0728}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_02 = {b0 = 0.697, b1 = 0.697, c = {1, 0.875, 0.0728}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_03 = {b0 = 0.697, b1 = 0.697, c = {0.3555, 1, 0.0728}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_04 = {b0 = 0.697, b1 = 0.697, c = {0.0728, 1, 0.6199}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_05 = {b0 = 0.697, b1 = 0.697, c = {0.0728, 0.6199, 1}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_06 = {b0 = 0.697, b1 = 0.697, c = {0.3555, 0.0728, 1}, cyc = 1, ph = 0, r = 6.13},
			VermeOhio__Luce_07 = {b0 = 0.697, b1 = 0.697, c = {1, 0.0728, 0.875}, cyc = 1, ph = 0, r = 6.13},
		},
		parti = {
			VermeOhio__Coda_Lucciola = {c = {1, 0.9777, 0.8543}, k = "neon"},
			VermeOhio__Faccia_Meme = {e = 4, k = "tex"},
			VermeOhio__Segmento_RGB_0 = {c = {1, 0.0728, 0.0728}, k = "neon"},
			VermeOhio__Segmento_RGB_1 = {c = {1, 0.875, 0.0728}, k = "neon"},
			VermeOhio__Segmento_RGB_2 = {c = {0.3555, 1, 0.0728}, k = "neon"},
			VermeOhio__Segmento_RGB_3 = {c = {0.0728, 1, 0.6199}, k = "neon"},
			VermeOhio__Segmento_RGB_4 = {c = {0.0728, 0.6199, 1}, k = "neon"},
			VermeOhio__Segmento_RGB_5 = {c = {0.3555, 0.0728, 1}, k = "neon"},
			VermeOhio__Segmento_RGB_6 = {c = {1, 0.0728, 0.875}, k = "neon"},
		},
		perni = {},
		scala = {},
	},
	Vipera = {
		bob = {},
		luci = {
			Vipera__Luce_01 = {b0 = 0.636, b1 = 1.35, c = {0.7977, 1, 0.4236}, cyc = 3, ph = 0, r = 7.65},
			Vipera__Luce_02 = {b0 = 0.551, b1 = 0.9, c = {0.7977, 1, 0.3133}, cyc = 2, ph = 0, r = 6.6},
		},
		parti = {
			Vipera__Alone_Sonaglio = {c = {0.7977, 1, 0.3492}, k = "aura", p = {0.3, 1, 3, 0}, t = 0.85},
			Vipera__Anelli_Scuri = {c = {0.2478, 0.2209, 0.1517}, k = "solid"},
			Vipera__Lingua__Lingua = {c = {0.7354, 0.1517, 0.2478}, k = "solid"},
			Vipera__Occhi = {c = {0.9547, 0.7674, 0.2478}, k = "neon"},
			Vipera__Pupilla = {c = {0, 0, 0}, k = "solid"},
			Vipera__Sonaglio_0 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, 0}},
			Vipera__Sonaglio_1 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -0.898}},
			Vipera__Sonaglio_2 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -1.795}},
			Vipera__Sonaglio_3 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -2.693}},
			Vipera__Sonaglio_4 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -3.59}},
			Vipera__Sonaglio_5 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -4.488}},
			Vipera__Sonaglio_6 = {c = {0.8808, 1, 0.3811}, k = "neon", p = {0.075, 1, 3, -5.386}},
			Vipera__Squame_Terracotta = {k = "tex"},
			Vipera__Striscia_0 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, 0}},
			Vipera__Striscia_1 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -0.785}},
			Vipera__Striscia_2 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -1.571}},
			Vipera__Striscia_3 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -2.356}},
			Vipera__Striscia_4 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -3.142}},
			Vipera__Striscia_5 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -3.927}},
			Vipera__Striscia_6 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -4.712}},
			Vipera__Striscia_7 = {c = {0.7977, 1, 0.3133}, k = "neon", p = {0.017, 1, 2, -5.498}},
			Vipera__Testa = {c = {0.6097, 0.3811, 0.2478}, k = "solid"},
		},
		perni = {
			Vipera__Perno_Lingua = {
				membri = {"Vipera__Lingua__Lingua"},
				padre = nil,
				rot = {
					{amp = 0.2443, asse = "X", cyc = 6, ph = 0},
				},
			},
		},
		scala = {},
	},
	Volpe = {
		bob = {},
		luci = {
			Volpe__Luce_01 = {b0 = 0.45, b1 = 1.273, c = {0.7674, 0.9309, 1}, cyc = 2, ph = 0, r = 7.47},
		},
		parti = {
			Volpe__Ali_Ghiacciate__Ala2_L = {ali = true, e = 9.6, k = "tex"},
			Volpe__Ali_Ghiacciate__Ala2_R = {ali = true, e = 9.6, k = "tex"},
			Volpe__Ali_Ghiacciate__Ala_L = {ali = true, e = 9.6, k = "tex"},
			Volpe__Ali_Ghiacciate__Ala_R = {ali = true, e = 9.6, k = "tex"},
			Volpe__Alone_Cuore = {c = {0.7674, 0.9309, 1}, k = "aura", p = {0.15, 1, 2, 0}, t = 0.85},
			Volpe__Corpo_Ghiaccio = {c = {0.8962, 0.9686, 1}, k = "glass", t = 0.45},
			Volpe__Cuore_Luce = {c = {0.7977, 0.9547, 1}, k = "neon", p = {0.143, 1, 2, 0}},
			Volpe__Naso = {c = {0.2478, 0.3492, 0.4366}, k = "solid"},
			Volpe__Occhi = {c = {0.7354, 0.9309, 1}, k = "neon"},
			Volpe__Punte_Ghiaccio = {c = {0.7674, 0.9309, 1}, k = "neon", p = {0.333, 1, 2, 0.5}, t = 0.2},
		},
		perni = {
			Volpe__Perno_Ala2_L = {
				membri = {"Volpe__Ali_Ghiacciate__Ala2_L"},
				padre = nil,
				rot = {
					{amp = 0.3142, asse = "Y", cyc = 36, ph = 1.4},
				},
			},
			Volpe__Perno_Ala2_R = {
				membri = {"Volpe__Ali_Ghiacciate__Ala2_R"},
				padre = nil,
				rot = {
					{amp = -0.3142, asse = "Y", cyc = 36, ph = 1.4},
				},
			},
			Volpe__Perno_Ala_L = {
				membri = {"Volpe__Ali_Ghiacciate__Ala_L"},
				padre = nil,
				rot = {
					{amp = 0.3142, asse = "Y", cyc = 36, ph = 0},
				},
			},
			Volpe__Perno_Ala_R = {
				membri = {"Volpe__Ali_Ghiacciate__Ala_R"},
				padre = nil,
				rot = {
					{amp = -0.3142, asse = "Y", cyc = 36, ph = 0},
				},
			},
		},
		scala = {},
	},
	Wyvern = {
		bob = {},
		luci = {
			Wyvern__Luce_01 = {b0 = 0.604, b1 = 0.604, c = {1, 0.7247, 0.4295}, cyc = 1, ph = 0, r = 5.91},
		},
		parti = {
			Wyvern__Bocca = {c = {0.5838, 0.1517, 0.2209}, k = "solid"},
			Wyvern__Corna_Artigli = {c = {0.9309, 0.8808, 0.7354}, k = "solid"},
			Wyvern__Denti = {c = {0.9777, 0.964, 0.9309}, k = "solid"},
			Wyvern__Membrana = {c = {0.4845, 0.3811, 0.5838}, k = "solid"},
			Wyvern__Occhi = {c = {1, 0.9063, 0.4845}, k = "neon"},
			Wyvern__Punta_Freccia_Smalti = {c = {1, 0.7247, 0.4295}, k = "neon"},
			Wyvern__Scaglie = {c = {0.3811, 0.3492, 0.4614}, k = "solid"},
			Wyvern__Scudo_Azzurro = {c = {0.2478, 0.4236, 0.8543}, k = "solid"},
			Wyvern__Scudo_Oro = {c = {1, 0.865, 0.5371}, k = "solid", metallo = true},
		},
		perni = {},
		scala = {},
	},
	Yeti = {
		bob = {},
		luci = {
			Yeti__Luce_01 = {b0 = 0.551, b1 = 1.191, c = {0.9309, 0.2478, 0.8808}, cyc = 1, ph = 0, r = 7.28},
			Yeti__Luce_02 = {b0 = 2.25, b1 = 2.25, c = {0.9063, 0.9309, 1}, cyc = 1, ph = 0, r = 9.75},
			Yeti__Luce_03 = {b0 = 0.318, b1 = 0.9, c = {0.9063, 0.4236, 1}, cyc = 1, ph = 0, r = 6.6},
			Yeti__Luce_04 = {b0 = 0.318, b1 = 0.9, c = {0.9063, 0.4236, 1}, cyc = 1, ph = 0, r = 6.6},
		},
		parti = {
			Yeti__Ali_Carnose__AlaAnt_L = {ali = true, e = 10.4, k = "tex"},
			Yeti__Ali_Carnose__AlaAnt_R = {ali = true, e = 10.4, k = "tex"},
			Yeti__Ali_Carnose__AlaPost_L = {ali = true, e = 10.4, k = "tex"},
			Yeti__Ali_Carnose__AlaPost_R = {ali = true, e = 10.4, k = "tex"},
			Yeti__Antenne = {c = {0.9063, 0.8962, 0.9309}, k = "solid"},
			Yeti__Bagliore_Nella_Pelliccia = {c = {1, 0.9163, 0.9867}, h = {0.9309, 0.2478, 0.8808}, k = "ghost"},
			Yeti__Occhi = {c = {0.1897, 0, 0.1897}, k = "solid"},
			Yeti__Pelliccia = {c = {0.9309, 0.2478, 0.8808}, k = "neon", p = {0.278, 1, 1, 0}},
			Yeti__Zampe = {c = {0.9309, 0.9212, 0.9547}, k = "solid"},
		},
		perni = {
			Yeti__Perno_AlaAnt_L = {
				membri = {"Yeti__Ali_Carnose__AlaAnt_L"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Yeti__Perno_AlaAnt_R = {
				membri = {"Yeti__Ali_Carnose__AlaAnt_R"},
				padre = nil,
				rot = {
					{amp = -0.1222, asse = "Y", cyc = 1, ph = 0},
				},
			},
			Yeti__Perno_AlaPost_L = {
				membri = {"Yeti__Ali_Carnose__AlaPost_L"},
				padre = nil,
				rot = {
					{amp = 0.1222, asse = "Y", cyc = 1, ph = 0.3},
				},
			},
			Yeti__Perno_AlaPost_R = {
				membri = {"Yeti__Ali_Carnose__AlaPost_R"},
				padre = nil,
				rot = {
					{amp = -0.1222, asse = "Y", cyc = 1, ph = 0.3},
				},
			},
		},
		scala = {},
	},
	Zucca = {
		bob = {},
		luci = {
			Zucca__Luce_01 = {b0 = 2.7, b1 = 2.7, c = {1, 0.5174, 0}, cyc = 1, ph = 0, r = 10.8},
			Zucca__Luce_02 = {b0 = 0.986, b1 = 0.986, c = {1, 0.5174, 0}, cyc = 1, ph = 0, r = 6.8},
		},
		parti = {
			Zucca__Ali_Foglie_Morte = {ali = true, k = "tex"},
			Zucca__Ali_Foglie_Rosse = {ali = true, k = "tex"},
			Zucca__Buccia = {k = "tex"},
			Zucca__Falena_Pelo = {c = {0.3318, 0.2601, 0.1897}, k = "solid"},
			Zucca__Gambo = {k = "tex"},
			Zucca__Luce_Interna = {c = {1, 0.5174, 0}, k = "neon"},
			Zucca__Occhi_Falena = {c = {0.1517, 0.1121, 0.0999}, k = "solid"},
			Zucca__Polpa_Accesa = {c = {1, 0.5174, 0}, k = "neon"},
			Zucca__Rametti = {k = "tex"},
		},
		perni = {},
		scala = {},
	},
}


local DUE_PI = math.pi * 2
local MARCATORI = { "__Radice", "__Asse", "__Perno_", "__Luce_" }

local function onda(cyc, ph, t)
	return 0.5 + 0.5 * math.sin(DUE_PI * cyc * t / CICLO + ph)
end

local function seno(cyc, ph, t)
	return math.sin(DUE_PI * cyc * t / CICLO + ph)
end

local function colore(c)
	return Color3.new(c[1], c[2], c[3])
end

-- colore di un ciclo: la tavolozza scorre cc.cyc volte per CICLO
local function ciclo(cc, t)
	local pal = cc.pal
	local n = #pal
	local x = ((cc.cyc * t / CICLO + cc.ph) % 1) * n
	local i = math.floor(x)
	local f = x - i
	local a = pal[(i % n) + 1]
	local b = pal[((i + 1) % n) + 1]
	return Color3.new(a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f)
end

local function materiale(nome)
	local ok, m = pcall(function()
		return Enum.Material[nome]
	end)
	return ok and m or nil
end

local function trova(model, nome)
	local p = model:FindFirstChild(nome, true)
	if p and p:IsA("BasePart") then
		return p
	end
	return nil
end

local function eMarcatore(nome)
	for _, m in ipairs(MARCATORI) do
		if string.find(nome, m, 1, true) then
			return true
		end
	end
	return false
end

local function contorno(parte, c)
	if parte:FindFirstChild("Contorno_Creatura") then
		return
	end
	local h = Instance.new("Highlight")
	h.Name = "Contorno_Creatura"
	h.Adornee = parte
	h.FillTransparency = 1
	h.OutlineColor = colore(c)
	h.OutlineTransparency = 0.35
	h.DepthMode = Enum.HighlightDepthMode.Occluded
	h.Parent = parte
end

local function togliTexture(parte)
	local sa = parte:FindFirstChildOfClass("SurfaceAppearance")
	if sa then
		sa:Destroy()
	end
	if parte:IsA("MeshPart") then
		pcall(function()
			parte.TextureID = ""
		end)
	end
end

-- Bagliore (bloom) per il Neon
if not Lighting:FindFirstChild("Bagliore_Creature") then
	local b = Instance.new("BloomEffect")
	b.Name = "Bagliore_Creature"
	b.Intensity = 1
	b.Size = 24
	b.Threshold = 0.9
	b.Parent = Lighting
end

-- ---------------------------------------------------------------------------
-- Preparazione di una creatura (materiali, luci, contorni)
-- ---------------------------------------------------------------------------

local istanze = {}

local function prepara(radice)
	if istanze[radice] then
		return
	end
	local prefisso = string.match(radice.Name, "^(.-)__Radice$")
	local cfg = prefisso and CONFIG[prefisso]
	local model = radice:FindFirstAncestorOfClass("Model") or radice.Parent
	if not cfg or not model then
		return
	end
	istanze[radice] = false

	-- in gioco le parti possono arrivare un po' alla volta: aspettale (max 10 s)
	if RunService:IsRunning() then
		local limite = os.clock() + 10
		while os.clock() < limite do
			local mancanti = 0
			for nome in pairs(cfg.parti) do
				if not trova(model, nome) then
					mancanti += 1
				end
			end
			if mancanti == 0 then
				break
			end
			task.wait(0.25)
		end
	else
		pcall(function()
			model.ModelStreamingMode = Enum.ModelStreamingMode.Atomic
		end)
	end

	for _, d in ipairs(model:GetDescendants()) do
		if d:IsA("BasePart") then
			d.Anchored = true
			if eMarcatore(d.Name) then
				d.Transparency = 1
				d.CanCollide = false
				d.CanQuery = false
				d.CanTouch = false
				d.CastShadow = false
			end
		end
	end

	for nome, s in pairs(cfg.parti) do
		local p = trova(model, nome)
		if p then
			if s.k == "neon" or s.k == "aura" then
				togliTexture(p)
				p.Material = Enum.Material.Neon
				p.Color = colore(s.c)
				p.Transparency = s.t or 0
				p.CastShadow = false
				p.CanCollide = false
			elseif s.k == "ghost" then
				togliTexture(p)
				p.Material = Enum.Material.ForceField
				p.Color = colore(s.c)
				p.CastShadow = false
			elseif s.k == "glass" then
				-- ali "miraggio": vetro che deforma lo sfondo come l'aria calda
				togliTexture(p)
				p.Material = Enum.Material.Glass
				p.Color = colore(s.c)
				p.Transparency = s.t or 0.6
				p.CastShadow = false
				p.CanCollide = false
			elseif s.k == "solid" then
				-- colore uniforme (se l'importer non l'ha gia' preso dal file)
				if not p:FindFirstChildOfClass("SurfaceAppearance") then
					p.Color = colore(s.c)
					p.Material = s.metallo and Enum.Material.Metal or Enum.Material.SmoothPlastic
				end
				-- materiale Roblox specifico (Ice, Snow, Slate...)
				local m = s.m and materiale(s.m)
				if m then
					p.Material = m
				end
			elseif s.k == "tex" then
				if s.ali then
					p.CastShadow = false
					p.CanCollide = false
					if p.Transparency < 0.02 then
						p.Transparency = 0.02
					end
				end
				local sa = p:FindFirstChildOfClass("SurfaceAppearance")
				if sa and s.e then
					pcall(function()
						sa.EmissiveStrength = s.e
					end)
				end
			end
			if s.rifl then
				p.Reflectance = s.rifl
			end
			if s.h then
				contorno(p, s.h)
			end
			if s.cc then
				local c0 = ciclo(s.cc, 0)
				if s.k ~= "tex" then
					p.Color = c0
				end
				local h = p:FindFirstChild("Contorno_Creatura")
				if h then
					h.OutlineColor = c0
				end
			end
		end
	end

	for nome, l in pairs(cfg.luci) do
		local p = trova(model, nome)
		if p then
			local classe = l.dir and "SpotLight" or "PointLight"
			local luce = p:FindFirstChild("Luce_Creatura")
			if luce and luce.ClassName ~= classe then
				luce:Destroy()
				luce = nil
			end
			luce = luce or Instance.new(classe)
			if l.dir then
				-- faretto: il marcatore guarda verso il suo marcatore "_Dir"
				local bersaglio = trova(model, l.dir)
				if bersaglio then
					p.CFrame = CFrame.lookAt(p.Position, bersaglio.Position)
				end
				luce.Face = Enum.NormalId.Front
				luce.Angle = l.ang or 60
			end
			luce.Name = "Luce_Creatura"
			luce.Color = l.cc and ciclo(l.cc, 0) or colore(l.c)
			luce.Range = l.r
			luce.Brightness = (l.b0 + l.b1) / 2
			luce.Shadows = false
			luce.Parent = p
		end
	end

	if not RunService:IsRunning() then
		return -- dalla Command Bar: solo preparazione, niente animazioni
	end

	-- dati per le animazioni -------------------------------------------------
	local origine = radice.Position
	local assi = {}
	for _, a in ipairs({ "X", "Y", "Z" }) do
		local m = trova(model, prefisso .. "__Asse" .. a)
		local v = m and (m.Position - origine) or Vector3.zero
		assi[a] = v.Magnitude > 0 and v.Unit or nil
	end

	local inst = { assi = assi, perni = {}, luci = {}, neon = {}, scala = {}, bob = {}, colori = {} }
	for nome, pv in pairs(cfg.perni) do
		local m = trova(model, nome)
		if m then
			local membri = {}
			for _, n in ipairs(pv.membri) do
				local p = trova(model, n)
				if p then
					table.insert(membri, { parte = p, riposo = p.CFrame })
				end
			end
			inst.perni[nome] = { centro = m.Position, rot = pv.rot, padre = pv.padre, membri = membri }
		end
	end
	for nome, l in pairs(cfg.luci) do
		local p = trova(model, nome)
		local luce = p and p:FindFirstChild("Luce_Creatura")
		if luce and l.b0 ~= l.b1 then
			table.insert(inst.luci, { luce = luce, b0 = l.b0, b1 = l.b1, cyc = l.cyc, ph = l.ph })
		end
	end
	for nome, s in pairs(cfg.parti) do
		local p = trova(model, nome)
		if p and s.p then
			table.insert(inst.neon, { parte = p, base = s.t or 0, lo = s.p[1], cyc = s.p[3], ph = s.p[4] })
		end
		if p and s.cc then
			table.insert(inst.colori, {
				parte = s.k ~= "tex" and p or nil,
				contorno = p:FindFirstChild("Contorno_Creatura"),
				cc = s.cc,
			})
		end
	end
	for nome, l in pairs(cfg.luci) do
		local p = trova(model, nome)
		local luce = p and p:FindFirstChild("Luce_Creatura")
		if luce and l.cc then
			table.insert(inst.colori, { luce = luce, cc = l.cc })
		end
	end
	for nome, s in pairs(cfg.scala) do
		local p = trova(model, nome)
		if p then
			table.insert(inst.scala, { parte = p, size0 = p.Size, lo = s.lo, hi = s.hi, cyc = s.cyc, ph = s.ph })
		end
	end
	for nome, s in pairs(cfg.bob) do
		local p = trova(model, nome)
		if p then
			table.insert(inst.bob, { parte = p, riposo = p.CFrame, amp = s.amp, cyc = s.cyc, ph = s.ph })
		end
	end
	istanze[radice] = inst
end

-- ---------------------------------------------------------------------------
-- Animazioni
-- ---------------------------------------------------------------------------

local function trasforma(inst, nome, t, cache)
	local fatto = cache[nome]
	if fatto then
		return fatto
	end
	local pv = inst.perni[nome]
	if not pv then
		return CFrame.identity
	end
	local T = CFrame.identity
	if pv.padre then
		T = trasforma(inst, pv.padre, t, cache)
	end
	local R = CFrame.identity
	local D = Vector3.zero
	for _, r in ipairs(pv.rot) do
		local asse = inst.assi[r.asse]
		if asse then
			if r.mov then
				D += asse * (r.amp * seno(r.cyc, r.ph, t)) -- galleggiamento (spostamento)
			else
				local ang
				if r.spin then
					ang = DUE_PI * r.cyc * t / CICLO + r.ph -- rotazione continua (sfera che rotola)
				else
					ang = r.amp * seno(r.cyc, r.ph, t)
				end
				R = CFrame.fromAxisAngle(asse, ang) * R
			end
		end
	end
	local W = T * CFrame.new(D) * CFrame.new(pv.centro) * R * CFrame.new(-pv.centro)
	cache[nome] = W
	return W
end

local function anima(t)
	for _, inst in pairs(istanze) do
		if inst then
			local cache = {}
			for nome, pv in pairs(inst.perni) do
				local W = trasforma(inst, nome, t, cache)
				for _, m in ipairs(pv.membri) do
					m.parte.CFrame = W * m.riposo
				end
			end
			for _, l in ipairs(inst.luci) do
				l.luce.Brightness = l.b0 + (l.b1 - l.b0) * onda(l.cyc, l.ph, t)
			end
			for _, n in ipairs(inst.neon) do
				local f = n.lo + (1 - n.lo) * onda(n.cyc, n.ph, t)
				n.parte.Transparency = math.clamp(n.base + (1 - f) * 0.5 * (1 - n.base), 0, 0.95)
			end
			for _, s in ipairs(inst.scala) do
				s.parte.Size = s.size0 * (s.lo + (s.hi - s.lo) * onda(s.cyc, s.ph, t))
			end
			local su = inst.assi.Z
			if su then
				for _, b in ipairs(inst.bob) do
					b.parte.CFrame = b.riposo + su * (b.amp * seno(b.cyc, b.ph, t))
				end
			end
			for _, c in ipairs(inst.colori) do
				local col = ciclo(c.cc, t)
				if c.parte then
					c.parte.Color = col
				end
				if c.contorno then
					c.contorno.OutlineColor = col
				end
				if c.luce then
					c.luce.Color = col
				end
			end
		end
	end
end

-- ---------------------------------------------------------------------------
-- Avvio
-- ---------------------------------------------------------------------------

local function controlla(d)
	if d:IsA("BasePart") and string.match(d.Name, "__Radice$") then
		if RunService:IsRunning() then
			task.spawn(prepara, d)
		else
			prepara(d)
		end
	end
end

for _, d in ipairs(workspace:GetDescendants()) do
	controlla(d)
end

if RunService:IsRunning() then
	workspace.DescendantAdded:Connect(controlla)
	local t0 = os.clock()
	RunService.RenderStepped:Connect(function()
		anima(os.clock() - t0)
	end)
end
