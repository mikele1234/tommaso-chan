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
      * trasforma in Neon le parti luminose (occhi, punti, bulbilli, filamenti...)
      * crea le luci (PointLight) nei punti giusti e le fa pulsare
      * aggiunge un contorno luminoso (Highlight) al gatto e al lupo
      * rende il lupo spettrale (materiale ForceField)
      * anima ali, antenna e lampadina, sacca vocale della rana, lucciole
      * aggiunge un BloomEffect in Lighting per far "accendere" il Neon
]]

local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")

local CICLO = 5.000

local CONFIG = {
    ["Farfalla"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Farfalla__Luce_01"] = {
                ["b0"] = 0.636,
                ["b1"] = 1.684,
                ["c"] = {0.4236, 0.7354, 1.0},
                ["cyc"] = 2,
                ["ph"] = 0.0,
                ["r"] = 8.43,
            },
        },
        ["parti"] = {
            ["Farfalla__Ala_Anteriore__AlaAnt_L"] = {
                ["ali"] = true,
                ["e"] = 8.8,
                ["k"] = "tex",
            },
            ["Farfalla__Ala_Anteriore__AlaAnt_R"] = {
                ["ali"] = true,
                ["e"] = 8.8,
                ["k"] = "tex",
            },
            ["Farfalla__Ala_Posteriore__AlaPost_L"] = {
                ["ali"] = true,
                ["e"] = 8.8,
                ["k"] = "tex",
            },
            ["Farfalla__Ala_Posteriore__AlaPost_R"] = {
                ["ali"] = true,
                ["e"] = 8.8,
                ["k"] = "tex",
            },
            ["Farfalla__Aura_Antenna"] = {
                ["c"] = {0.4845, 1.0, 0.8543},
                ["k"] = "aura",
                ["p"] = {0.4, 1.0, 2.0, 0.0},
                ["t"] = 0.85,
            },
            ["Farfalla__Corpo_Scuro"] = {
                ["c"] = {0.0861, 0.0999, 0.1428},
                ["k"] = "solid",
            },
            ["Farfalla__Cuore_Luce"] = {
                ["c"] = {0.3492, 0.7674, 1.0},
                ["k"] = "aura",
                ["p"] = {0.2, 1.0, 2.0, 0.0},
                ["t"] = 0.85,
            },
            ["Farfalla__Occhi"] = {
                ["c"] = {0.1517, 0.2478, 0.3492},
                ["k"] = "solid",
            },
            ["Farfalla__Punte_Antenne"] = {
                ["c"] = {0.5838, 1.0, 0.8543},
                ["k"] = "neon",
                ["p"] = {0.5, 1.0, 2.0, 0.0},
            },
        },
        ["perni"] = {
            ["Farfalla__Perno_AlaAnt_L"] = {
                ["membri"] = {
                    "Farfalla__Ala_Anteriore__AlaAnt_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.2793,
                        ["asse"] = "Y",
                        ["cyc"] = 2,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Farfalla__Perno_AlaAnt_R"] = {
                ["membri"] = {
                    "Farfalla__Ala_Anteriore__AlaAnt_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.2793,
                        ["asse"] = "Y",
                        ["cyc"] = 2,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Farfalla__Perno_AlaPost_L"] = {
                ["membri"] = {
                    "Farfalla__Ala_Posteriore__AlaPost_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.2793,
                        ["asse"] = "Y",
                        ["cyc"] = 2,
                        ["ph"] = 0.15,
                    },
                },
            },
            ["Farfalla__Perno_AlaPost_R"] = {
                ["membri"] = {
                    "Farfalla__Ala_Posteriore__AlaPost_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.2793,
                        ["asse"] = "Y",
                        ["cyc"] = 2,
                        ["ph"] = 0.15,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Gatto"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Gatto__Luce_01"] = {
                ["b0"] = 0.712,
                ["b1"] = 1.006,
                ["c"] = {0.6652, 0.5838, 1.0},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 6.85,
            },
        },
        ["parti"] = {
            ["Gatto__Ala_Luce_Post__AlaPost_L"] = {
                ["ali"] = true,
                ["e"] = 5.2,
                ["k"] = "tex",
            },
            ["Gatto__Ala_Luce_Post__AlaPost_R"] = {
                ["ali"] = true,
                ["e"] = 5.2,
                ["k"] = "tex",
            },
            ["Gatto__Ala_Luce__AlaAnt_L"] = {
                ["ali"] = true,
                ["e"] = 5.6,
                ["k"] = "tex",
            },
            ["Gatto__Ala_Luce__AlaAnt_R"] = {
                ["ali"] = true,
                ["e"] = 5.6,
                ["k"] = "tex",
            },
            ["Gatto__Aura_Coda"] = {
                ["c"] = {0.6652, 0.5838, 1.0},
                ["k"] = "aura",
                ["p"] = {0.444, 1.0, 1.0, 0.0},
                ["t"] = 0.85,
            },
            ["Gatto__Baffi_Luce"] = {
                ["c"] = {0.7674, 0.8267, 1.0},
                ["k"] = "neon",
                ["p"] = {0.5, 1.0, 2.0, 0.0},
            },
            ["Gatto__Coda_Luce"] = {
                ["c"] = {0.7014, 0.6262, 1.0},
                ["k"] = "neon",
                ["p"] = {0.437, 1.0, 1.0, 0.0},
            },
            ["Gatto__Iride"] = {
                ["c"] = {1.0, 0.865, 0.3811},
                ["k"] = "neon",
            },
            ["Gatto__Luna_Fronte"] = {
                ["c"] = {0.8808, 0.9063, 1.0},
                ["k"] = "neon",
            },
            ["Gatto__Naso"] = {
                ["c"] = {0.2478, 0.1517, 0.2717},
                ["k"] = "solid",
            },
            ["Gatto__Orecchio_Interno"] = {
                ["c"] = {0.7014, 0.5371, 1.0},
                ["k"] = "neon",
                ["p"] = {0.417, 1.0, 1.0, 0.5},
            },
            ["Gatto__Pelo_Notte"] = {
                ["c"] = {0.0702, 0.061, 0.1061},
                ["h"] = {0.6012, 0.5064, 1.0},
                ["k"] = "solid",
            },
            ["Gatto__Pupilla"] = {
                ["c"] = {0.0, 0.0, 0.0},
                ["k"] = "solid",
            },
        },
        ["perni"] = {
            ["Gatto__Perno_AlaAnt_L"] = {
                ["membri"] = {
                    "Gatto__Ala_Luce__AlaAnt_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1222,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Gatto__Perno_AlaAnt_R"] = {
                ["membri"] = {
                    "Gatto__Ala_Luce__AlaAnt_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1222,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Gatto__Perno_AlaPost_L"] = {
                ["membri"] = {
                    "Gatto__Ala_Luce_Post__AlaPost_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1222,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.25,
                    },
                },
            },
            ["Gatto__Perno_AlaPost_R"] = {
                ["membri"] = {
                    "Gatto__Ala_Luce_Post__AlaPost_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1222,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.25,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Gufo"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Gufo__Luce_01"] = {
                ["b0"] = 0.318,
                ["b1"] = 0.712,
                ["c"] = {1.0, 0.8808, 0.5371},
                ["cyc"] = 2,
                ["ph"] = 0.5,
                ["r"] = 6.16,
            },
            ["Gufo__Luce_02"] = {
                ["b0"] = 0.318,
                ["b1"] = 0.712,
                ["c"] = {1.0, 0.8808, 0.5371},
                ["cyc"] = 2,
                ["ph"] = 0.5,
                ["r"] = 6.16,
            },
            ["Gufo__Luce_03"] = {
                ["b0"] = 1.559,
                ["b1"] = 2.012,
                ["c"] = {1.0, 0.9309, 0.6652},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 9.2,
            },
            ["Gufo__Luce_04"] = {
                ["b0"] = 1.559,
                ["b1"] = 2.012,
                ["c"] = {1.0, 0.9309, 0.6652},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 9.2,
            },
            ["Gufo__Luce_05"] = {
                ["b0"] = 0.349,
                ["b1"] = 0.532,
                ["c"] = {1.0, 0.9063, 0.6262},
                ["cyc"] = 2,
                ["ph"] = 0.0,
                ["r"] = 5.74,
            },
        },
        ["parti"] = {
            ["Gufo__Anello_Occhio"] = {
                ["c"] = {1.0, 0.8267, 0.3133},
                ["k"] = "neon",
            },
            ["Gufo__Artigli"] = {
                ["c"] = {0.2717, 0.2478, 0.2348},
                ["k"] = "solid",
            },
            ["Gufo__Aura_Ali"] = {
                ["c"] = {1.0, 0.8095, 0.3492},
                ["k"] = "aura",
                ["p"] = {0.333, 1.0, 2.0, 0.5},
                ["t"] = 0.85,
            },
            ["Gufo__Becco"] = {
                ["c"] = {0.5371, 0.4845, 0.3811},
                ["k"] = "solid",
            },
            ["Gufo__Corteccia"] = {
                ["k"] = "tex",
            },
            ["Gufo__Disco_Facciale"] = {
                ["c"] = {0.5838, 0.4614, 0.3133},
                ["k"] = "solid",
            },
            ["Gufo__Foglia"] = {
                ["c"] = {0.1517, 0.2934, 0.1517},
                ["k"] = "solid",
            },
            ["Gufo__Occhio_Faro"] = {
                ["c"] = {1.0, 0.9777, 0.7354},
                ["k"] = "neon",
                ["p"] = {0.632, 1.0, 1.0, 0.0},
            },
            ["Gufo__Piuma_Chiara_1"] = {
                ["e"] = 8.0,
                ["k"] = "tex",
            },
            ["Gufo__Piuma_Chiara_2"] = {
                ["e"] = 8.0,
                ["k"] = "tex",
            },
            ["Gufo__Piuma_Neon_1"] = {
                ["e"] = 10.4,
                ["k"] = "tex",
            },
            ["Gufo__Piuma_Neon_2"] = {
                ["e"] = 10.4,
                ["k"] = "tex",
            },
            ["Gufo__Piuma_Neon_3"] = {
                ["e"] = 10.4,
                ["k"] = "tex",
            },
            ["Gufo__Piuma_Neon_4"] = {
                ["e"] = 10.4,
                ["k"] = "tex",
            },
            ["Gufo__Piumino"] = {
                ["c"] = {0.3811, 0.2478, 0.1428},
                ["k"] = "solid",
            },
            ["Gufo__Zampe"] = {
                ["c"] = {0.6262, 0.5657, 0.3811},
                ["k"] = "solid",
            },
        },
        ["perni"] = {},
        ["scala"] = {},
    },
    ["Libellula"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Libellula__Luce_01"] = {
                ["b0"] = 0.45,
                ["b1"] = 1.423,
                ["c"] = {1.0, 0.8808, 0.5838},
                ["cyc"] = 2,
                ["ph"] = 0.0,
                ["r"] = 7.82,
            },
            ["Libellula__Luce_02"] = {
                ["b0"] = 0.551,
                ["b1"] = 0.9,
                ["c"] = {0.5838, 0.7977, 1.0},
                ["cyc"] = 3,
                ["ph"] = 0.0,
                ["r"] = 6.6,
            },
        },
        ["parti"] = {
            ["Libellula__Ala_Circuito__AlaAnt_L"] = {
                ["ali"] = true,
                ["e"] = 16.0,
                ["k"] = "tex",
            },
            ["Libellula__Ala_Circuito__AlaAnt_R"] = {
                ["ali"] = true,
                ["e"] = 16.0,
                ["k"] = "tex",
            },
            ["Libellula__Ala_Circuito__AlaPost_L"] = {
                ["ali"] = true,
                ["e"] = 16.0,
                ["k"] = "tex",
            },
            ["Libellula__Ala_Circuito__AlaPost_R"] = {
                ["ali"] = true,
                ["e"] = 16.0,
                ["k"] = "tex",
            },
            ["Libellula__Aura_Bulbo"] = {
                ["c"] = {1.0, 0.8543, 0.4845},
                ["k"] = "aura",
                ["p"] = {0.125, 1.0, 2.0, 0.0},
                ["t"] = 0.85,
            },
            ["Libellula__Azzurro"] = {
                ["c"] = {0.2478, 0.7014, 0.9547},
                ["k"] = "solid",
            },
            ["Libellula__Bulbo"] = {
                ["c"] = {1.0, 0.9063, 0.6262},
                ["k"] = "neon",
                ["p"] = {0.167, 1.0, 2.0, 0.0},
            },
            ["Libellula__Occhi"] = {
                ["c"] = {0.1517, 0.5838, 0.8543},
                ["k"] = "solid",
            },
            ["Libellula__Oro"] = {
                ["c"] = {1.0, 0.7977, 0.3492},
                ["k"] = "neon",
                ["p"] = {0.3, 1.0, 3.0, 0.0},
            },
            ["Libellula__Zampe"] = {
                ["c"] = {0.1517, 0.1897, 0.2478},
                ["k"] = "solid",
            },
        },
        ["perni"] = {
            ["Libellula__Perno_AlaAnt_L"] = {
                ["membri"] = {
                    "Libellula__Ala_Circuito__AlaAnt_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 6,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Libellula__Perno_AlaAnt_R"] = {
                ["membri"] = {
                    "Libellula__Ala_Circuito__AlaAnt_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 6,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Libellula__Perno_AlaPost_L"] = {
                ["membri"] = {
                    "Libellula__Ala_Circuito__AlaPost_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 6,
                        ["ph"] = 1.2,
                    },
                },
            },
            ["Libellula__Perno_AlaPost_R"] = {
                ["membri"] = {
                    "Libellula__Ala_Circuito__AlaPost_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 6,
                        ["ph"] = 1.2,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Lucina"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Lucina__Luce_01"] = {
                ["b0"] = 1.684,
                ["b1"] = 2.111,
                ["c"] = {1.0, 0.865, 0.6262},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 9.42,
            },
            ["Lucina__Luce_02"] = {
                ["b0"] = 0.551,
                ["b1"] = 0.712,
                ["c"] = {1.0, 0.865, 0.5657},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 6.16,
            },
        },
        ["parti"] = {
            ["Lucina__Alette_Luce__AlettaAnt_L"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lucina__Alette_Luce__AlettaAnt_R"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lucina__Alette_Luce__AlettaPost_L"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lucina__Alette_Luce__AlettaPost_R"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lucina__Antenna__Antenna"] = {
                ["c"] = {0.5371, 0.4614, 0.3492},
                ["k"] = "solid",
            },
            ["Lucina__Attacco_Metallo__Lampadina"] = {
                ["c"] = {0.9063, 0.8808, 0.7977},
                ["k"] = "solid",
                ["metallo"] = true,
            },
            ["Lucina__Filamento__Lampadina"] = {
                ["c"] = {1.0, 0.8543, 0.5371},
                ["k"] = "neon",
                ["p"] = {0.696, 1.0, 1.0, 0.0},
            },
            ["Lucina__Guance"] = {
                ["c"] = {1.0, 0.6262, 0.6262},
                ["k"] = "neon",
            },
            ["Lucina__Luccichio"] = {
                ["c"] = {1.0, 1.0, 1.0},
                ["k"] = "neon",
            },
            ["Lucina__Luce_Lampadina__Lampadina"] = {
                ["c"] = {1.0, 0.8808, 0.5838},
                ["k"] = "aura",
                ["p"] = {0.688, 1.0, 1.0, 0.0},
                ["t"] = 0.85,
            },
            ["Lucina__Occhio_Bianco"] = {
                ["c"] = {0.9777, 0.9777, 0.964},
                ["k"] = "solid",
            },
            ["Lucina__Pelo_Soffice"] = {
                ["c"] = {1.0, 0.886, 0.5064},
                ["k"] = "solid",
            },
            ["Lucina__Pupilla"] = {
                ["c"] = {0.061, 0.061, 0.0999},
                ["k"] = "solid",
            },
            ["Lucina__Sorriso"] = {
                ["c"] = {0.3133, 0.1517, 0.1517},
                ["k"] = "solid",
            },
            ["Lucina__Vetro_Lampadina__Lampadina"] = {
                ["c"] = {1.0, 0.9063, 0.7014},
                ["k"] = "neon",
                ["p"] = {0.7, 1.0, 1.0, 0.0},
                ["t"] = 0.45,
            },
        },
        ["perni"] = {
            ["Lucina__Perno_AlettaAnt_L"] = {
                ["membri"] = {
                    "Lucina__Alette_Luce__AlettaAnt_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.384,
                        ["asse"] = "Y",
                        ["cyc"] = 8,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Lucina__Perno_AlettaAnt_R"] = {
                ["membri"] = {
                    "Lucina__Alette_Luce__AlettaAnt_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.384,
                        ["asse"] = "Y",
                        ["cyc"] = 8,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Lucina__Perno_AlettaPost_L"] = {
                ["membri"] = {
                    "Lucina__Alette_Luce__AlettaPost_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.384,
                        ["asse"] = "Y",
                        ["cyc"] = 8,
                        ["ph"] = 0.3,
                    },
                },
            },
            ["Lucina__Perno_AlettaPost_R"] = {
                ["membri"] = {
                    "Lucina__Alette_Luce__AlettaPost_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.384,
                        ["asse"] = "Y",
                        ["cyc"] = 8,
                        ["ph"] = 0.3,
                    },
                },
            },
            ["Lucina__Perno_Antenna"] = {
                ["membri"] = {
                    "Lucina__Antenna__Antenna",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1222,
                        ["asse"] = "X",
                        ["cyc"] = 2,
                        ["ph"] = 0.0,
                    },
                    {
                        ["amp"] = 0.0873,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 1.3,
                    },
                },
            },
            ["Lucina__Perno_Lampadina"] = {
                ["membri"] = {
                    "Lucina__Luce_01",
                    "Lucina__Attacco_Metallo__Lampadina",
                    "Lucina__Filamento__Lampadina",
                    "Lucina__Luce_Lampadina__Lampadina",
                    "Lucina__Vetro_Lampadina__Lampadina",
                },
                ["padre"] = "Lucina__Perno_Antenna",
                ["rot"] = {
                    {
                        ["amp"] = 0.4189,
                        ["asse"] = "X",
                        ["cyc"] = 2,
                        ["ph"] = 0.6,
                    },
                    {
                        ["amp"] = 0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.0,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Lupo"] = {
        ["bob"] = {
            ["Lupo__Lucciole__Lucciola_00"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 6.219,
            },
            ["Lupo__Lucciole__Lucciola_01"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 0.089,
            },
            ["Lupo__Lucciole__Lucciola_02"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 4.36,
            },
            ["Lupo__Lucciole__Lucciola_03"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.214,
            },
            ["Lupo__Lucciole__Lucciola_04"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.146,
            },
            ["Lupo__Lucciole__Lucciola_05"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 3.468,
            },
            ["Lupo__Lucciole__Lucciola_06"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 0.469,
            },
            ["Lupo__Lucciole__Lucciola_07"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 0.77,
            },
            ["Lupo__Lucciole__Lucciola_08"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 1.835,
            },
            ["Lupo__Lucciole__Lucciola_09"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.169,
            },
            ["Lupo__Lucciole__Lucciola_10"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.441,
            },
            ["Lupo__Lucciole__Lucciola_11"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 1.135,
            },
            ["Lupo__Lucciole__Lucciola_12"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 1.544,
            },
            ["Lupo__Lucciole__Lucciola_13"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 4.294,
            },
            ["Lupo__Lucciole__Lucciola_14"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 6.041,
            },
            ["Lupo__Lucciole__Lucciola_15"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 5.883,
            },
            ["Lupo__Lucciole__Lucciola_16"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.361,
            },
            ["Lupo__Lucciole__Lucciola_17"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 1.072,
            },
            ["Lupo__Lucciole__Lucciola_18"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 0.31,
            },
            ["Lupo__Lucciole__Lucciola_19"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 5.651,
            },
            ["Lupo__Lucciole__Lucciola_20"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 3.651,
            },
            ["Lupo__Lucciole__Lucciola_21"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 2.402,
            },
            ["Lupo__Lucciole__Lucciola_22"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 5.351,
            },
            ["Lupo__Lucciole__Lucciola_23"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 0.839,
            },
            ["Lupo__Lucciole__Lucciola_24"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 0.452,
            },
            ["Lupo__Lucciole__Lucciola_25"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 3.103,
            },
            ["Lupo__Lucciole__Lucciola_26"] = {
                ["amp"] = 0.18,
                ["cyc"] = 1,
                ["ph"] = 3.794,
            },
            ["Lupo__Lucciole__Lucciola_27"] = {
                ["amp"] = 0.18,
                ["cyc"] = 2,
                ["ph"] = 2.915,
            },
        },
        ["luci"] = {
            ["Lupo__Luce_01"] = {
                ["b0"] = 0.779,
                ["b1"] = 1.35,
                ["c"] = {0.3492, 1.0, 0.9309},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 7.65,
            },
            ["Lupo__Luce_02"] = {
                ["b0"] = 0.636,
                ["b1"] = 1.102,
                ["c"] = {0.3492, 1.0, 0.9309},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 7.07,
            },
        },
        ["parti"] = {
            ["Lupo__Ali_Delicate__Ali2_L"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lupo__Ali_Delicate__Ali2_R"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lupo__Ali_Delicate__Ali_L"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lupo__Ali_Delicate__Ali_R"] = {
                ["ali"] = true,
                ["e"] = 12.0,
                ["k"] = "tex",
            },
            ["Lupo__Corpo_Spettrale"] = {
                ["c"] = {0.7977, 0.9777, 1.0},
                ["h"] = {0.2478, 1.0, 0.9163},
                ["k"] = "ghost",
            },
            ["Lupo__Lucciole__Lucciola_00"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_01"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_02"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_03"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_04"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_05"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_06"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_07"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_08"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_09"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_10"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_11"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_12"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_13"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_14"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_15"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_16"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_17"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_18"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_19"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_20"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_21"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_22"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_23"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_24"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_25"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_26"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Lucciole__Lucciola_27"] = {
                ["c"] = {0.7354, 1.0, 0.9309},
                ["k"] = "neon",
                ["p"] = {0.25, 1.0, 3.0, 0.0},
            },
            ["Lupo__Naso"] = {
                ["c"] = {0.8808, 0.9547, 1.0},
                ["h"] = {0.2478, 1.0, 0.9163},
                ["k"] = "ghost",
            },
            ["Lupo__Occhi"] = {
                ["c"] = {0.7354, 1.0, 0.9777},
                ["k"] = "neon",
                ["p"] = {0.571, 1.0, 1.0, 0.0},
            },
        },
        ["perni"] = {
            ["Lupo__Perno_Ali2_L"] = {
                ["membri"] = {
                    "Lupo__Ali_Delicate__Ali2_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.2443,
                        ["asse"] = "Y",
                        ["cyc"] = 5,
                        ["ph"] = 0.9,
                    },
                },
            },
            ["Lupo__Perno_Ali2_R"] = {
                ["membri"] = {
                    "Lupo__Ali_Delicate__Ali2_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.2443,
                        ["asse"] = "Y",
                        ["cyc"] = 5,
                        ["ph"] = 0.9,
                    },
                },
            },
            ["Lupo__Perno_Ali_L"] = {
                ["membri"] = {
                    "Lupo__Ali_Delicate__Ali_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.2443,
                        ["asse"] = "Y",
                        ["cyc"] = 5,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Lupo__Perno_Ali_R"] = {
                ["membri"] = {
                    "Lupo__Ali_Delicate__Ali_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.2443,
                        ["asse"] = "Y",
                        ["cyc"] = 5,
                        ["ph"] = 0.0,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Mantide"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Mantide__Luce_01"] = {
                ["b0"] = 0.779,
                ["b1"] = 1.743,
                ["c"] = {1.0, 0.7354, 0.3811},
                ["cyc"] = 2,
                ["ph"] = 0.0,
                ["r"] = 8.57,
            },
            ["Mantide__Luce_02"] = {
                ["b0"] = 0.636,
                ["b1"] = 0.9,
                ["c"] = {1.0, 0.7674, 0.4845},
                ["cyc"] = 1,
                ["ph"] = 0.0,
                ["r"] = 6.6,
            },
        },
        ["parti"] = {
            ["Mantide__Addome_Pulsante"] = {
                ["c"] = {1.0, 0.5838, 0.1517},
                ["k"] = "neon",
                ["p"] = {0.154, 1.0, 2.0, 0.0},
            },
            ["Mantide__Ala_Anteriore__AlaAnteriore_L"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Mantide__Ala_Anteriore__AlaAnteriore_R"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Mantide__Ala_Vetrata__AlaPosteriore_L"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Mantide__Ala_Vetrata__AlaPosteriore_R"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Mantide__Occhi"] = {
                ["c"] = {0.5371, 0.7977, 0.2478},
                ["k"] = "solid",
            },
            ["Mantide__Punte"] = {
                ["c"] = {1.0, 0.8808, 0.5838},
                ["k"] = "neon",
            },
            ["Mantide__Smeraldo_1"] = {
                ["c"] = {0.061, 0.5657, 0.2934},
                ["k"] = "solid",
            },
            ["Mantide__Smeraldo_2"] = {
                ["c"] = {0.061, 0.5657, 0.2934},
                ["k"] = "solid",
            },
            ["Mantide__Spine"] = {
                ["c"] = {1.0, 0.8543, 0.4845},
                ["k"] = "neon",
            },
        },
        ["perni"] = {
            ["Mantide__Perno_AlaAnteriore_L"] = {
                ["membri"] = {
                    "Mantide__Ala_Anteriore__AlaAnteriore_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.0524,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.4,
                    },
                },
            },
            ["Mantide__Perno_AlaAnteriore_R"] = {
                ["membri"] = {
                    "Mantide__Ala_Anteriore__AlaAnteriore_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.0524,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.4,
                    },
                },
            },
            ["Mantide__Perno_AlaPosteriore_L"] = {
                ["membri"] = {
                    "Mantide__Ala_Vetrata__AlaPosteriore_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.0524,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Mantide__Perno_AlaPosteriore_R"] = {
                ["membri"] = {
                    "Mantide__Ala_Vetrata__AlaPosteriore_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.0524,
                        ["asse"] = "Y",
                        ["cyc"] = 1,
                        ["ph"] = 0.0,
                    },
                },
            },
        },
        ["scala"] = {},
    },
    ["Rana"] = {
        ["bob"] = {},
        ["luci"] = {
            ["Rana__Luce_01"] = {
                ["b0"] = 0.45,
                ["b1"] = 1.559,
                ["c"] = {1.0, 0.6652, 0.2478},
                ["cyc"] = 2,
                ["ph"] = 0.0,
                ["r"] = 8.14,
            },
            ["Rana__Luce_02"] = {
                ["b0"] = 0.45,
                ["b1"] = 0.779,
                ["c"] = {1.0, 0.7014, 0.3133},
                ["cyc"] = 2,
                ["ph"] = 2.1,
                ["r"] = 6.32,
            },
        },
        ["parti"] = {
            ["Rana__Ali_Insetto__AlaDorso2_L"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Ali_Insetto__AlaDorso2_R"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Ali_Insetto__AlaDorso_L"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Ali_Insetto__AlaDorso_R"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Ali_Insetto__AlaFianco_L"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Ali_Insetto__AlaFianco_R"] = {
                ["ali"] = true,
                ["e"] = 7.2,
                ["k"] = "tex",
            },
            ["Rana__Bulbilli"] = {
                ["c"] = {1.0, 0.7674, 0.3133},
                ["k"] = "neon",
                ["p"] = {0.5, 1.0, 2.0, 1.0},
            },
            ["Rana__Iride"] = {
                ["c"] = {0.9547, 0.6262, 0.1517},
                ["k"] = "neon",
            },
            ["Rana__Pelle_Bagnata_1"] = {
                ["k"] = "tex",
            },
            ["Rana__Pelle_Bagnata_2"] = {
                ["k"] = "tex",
            },
            ["Rana__Punto_Luce_0"] = {
                ["c"] = {1.0, 0.5838, 0.0999},
                ["k"] = "neon",
                ["p"] = {0.192, 1.0, 2.0, 0.0},
            },
            ["Rana__Punto_Luce_1"] = {
                ["c"] = {1.0, 0.5838, 0.0999},
                ["k"] = "neon",
                ["p"] = {0.192, 1.0, 2.0, 2.1},
            },
            ["Rana__Punto_Luce_2"] = {
                ["c"] = {1.0, 0.5838, 0.0999},
                ["k"] = "neon",
                ["p"] = {0.192, 1.0, 2.0, 4.2},
            },
            ["Rana__Pupilla"] = {
                ["c"] = {0.0, 0.0, 0.0},
                ["k"] = "solid",
            },
            ["Rana__Sacca_Vocale__SaccaVocale"] = {
                ["c"] = {1.0, 0.5657, 0.0999},
                ["k"] = "neon",
                ["p"] = {0.156, 1.0, 2.0, 0.0},
                ["t"] = 0.1,
            },
            ["Rana__Ventre"] = {
                ["c"] = {0.2717, 0.3133, 0.206},
                ["k"] = "solid",
            },
        },
        ["perni"] = {
            ["Rana__Perno_AlaDorso2_L"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaDorso2_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 0.8,
                    },
                },
            },
            ["Rana__Perno_AlaDorso2_R"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaDorso2_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 0.8,
                    },
                },
            },
            ["Rana__Perno_AlaDorso_L"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaDorso_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Rana__Perno_AlaDorso_R"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaDorso_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1745,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 0.0,
                    },
                },
            },
            ["Rana__Perno_AlaFianco_L"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaFianco_L",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = 0.1396,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 1.6,
                    },
                },
            },
            ["Rana__Perno_AlaFianco_R"] = {
                ["membri"] = {
                    "Rana__Ali_Insetto__AlaFianco_R",
                },
                ["padre"] = nil,
                ["rot"] = {
                    {
                        ["amp"] = -0.1396,
                        ["asse"] = "Y",
                        ["cyc"] = 4,
                        ["ph"] = 1.6,
                    },
                },
            },
        },
        ["scala"] = {
            ["Rana__Sacca_Vocale__SaccaVocale"] = {
                ["cyc"] = 2,
                ["hi"] = 1.12,
                ["lo"] = 0.82,
                ["ph"] = 0.0,
            },
        },
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
			elseif s.k == "solid" then
				-- colore uniforme (se l'importer non l'ha gia' preso dal file)
				if not p:FindFirstChildOfClass("SurfaceAppearance") then
					p.Color = colore(s.c)
					p.Material = s.metallo and Enum.Material.Metal or Enum.Material.SmoothPlastic
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
			if s.h then
				contorno(p, s.h)
			end
		end
	end

	for nome, l in pairs(cfg.luci) do
		local p = trova(model, nome)
		if p then
			local luce = p:FindFirstChild("Luce_Creatura") or Instance.new("PointLight")
			luce.Name = "Luce_Creatura"
			luce.Color = colore(l.c)
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

	local inst = { assi = assi, perni = {}, luci = {}, neon = {}, scala = {}, bob = {} }
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
	for _, r in ipairs(pv.rot) do
		local asse = inst.assi[r.asse]
		if asse then
			R = CFrame.fromAxisAngle(asse, r.amp * seno(r.cyc, r.ph, t)) * R
		end
	end
	local W = T * CFrame.new(pv.centro) * R * CFrame.new(-pv.centro)
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
