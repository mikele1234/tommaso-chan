# -*- coding: utf-8 -*-
"""
ESPORTAZIONE DELLE CREATURE LUMINOSE PER ROBLOX STUDIO

Costruisce ogni creatura delle quattro serie (creature_luminose.py,
creature_deserto.py, creature_neve.py, creature_oceano.py) e la prepara per
Roblox:

  * al massimo 20.000 triangoli PER CREATURA (in totale): la creatura viene
    ricostruita a un livello di dettaglio piu' basso finche' rientra e, se
    serve, le mesh vengono decimate;
  * curve, metaball e modificatori diventano mesh normali;
  * le ali ricevono un minimo di spessore (su Roblox le mesh piatte si vedono
    da un lato solo);
  * i materiali procedurali vengono "cotti" (bake) in texture: colore con
    trasparenza, mappa emissiva (Roblox la trasforma in Emissive Mask) e,
    dove serve, normal map;
  * i pezzi con lo stesso materiale vengono uniti;
  * luci e perni delle animazioni diventano piccoli marcatori invisibili,
    usati dallo script Luau per ricreare luci, Neon e animazioni.

Risultato (nella cartella di uscita):
    modelli/<nn>_<nome>.glb           prima serie
    modelli/deserto/<nn>_<nome>.glb   serie del deserto
    modelli/neve/<nn>_<nome>.glb      serie della neve
    modelli/oceano/<nn>_<nome>.glb    serie dell'oceano
    CreatureLuminose.client.lua       un solo LocalScript per tutte le creature

USO
    blender --background --python blender/esporta_roblox.py -- --uscita roblox
    opzioni:  --serie deserto        (solo una serie: luminose | deserto | neve | oceano)
              --creatura vipera      (solo una creatura)
              --scala 3              (1 metro di Blender = 3 stud)
              --max-triangoli 20000  (limite per creatura; 0 = nessun limite,
                                      dettaglio pieno)
"""

import bpy
import bmesh
import glob
import importlib.util
import json
import math
import os
import sys

import numpy as np
from mathutils import Matrix, Vector

QUI = os.path.dirname(os.path.abspath(__file__))


def _carica(nome):
    if nome in sys.modules:
        return sys.modules[nome]
    spec = importlib.util.spec_from_file_location(nome, os.path.join(QUI, nome + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


CL = _carica("creature_luminose")
DS = _carica("creature_deserto")
NV = _carica("creature_neve")
OC = _carica("creature_oceano")

# Fattore di scala: 1 metro in Blender -> SCALA stud su Roblox.
SCALA = 3.0
MAX_TRIANGOLI_CREATURA = 20000     # limite richiesto per ogni creatura
MAX_TRIANGOLI_MESH = 19000         # Roblox: massimo 20.000 per singola mesh
SPESSORE = 0.004                   # spessore dato alle ali (metri)
DATI = os.path.join(QUI, "dati_roblox")   # configurazioni per lo script Luau

SERIE = {
    "luminose": {
        "registro": CL.CREATURE,
        "cartella": "modelli",
        "creature": {
            #  chiave      file                    prefisso dei pezzi su Roblox
            "mantide":   ("01_mante_luce",        "Mantide"),
            "gatto":     ("02_gattoluna",         "Gatto"),
            "gufo":      ("03_gufo_scintilla",    "Gufo"),
            "rana":      ("04_ranabuio",          "Rana"),
            "farfalla":  ("05_farfalla_glow",     "Farfalla"),
            "libellula": ("06_libellula_fulmine", "Libellula"),
            "lupo":      ("07_lupo_luce",         "Lupo"),
            "falena":    ("08_lucina_farfallina", "Lucina"),
        },
    },
    "deserto": {
        "registro": DS.CREATURE_DESERTO,
        "cartella": os.path.join("modelli", "deserto"),
        "creature": {
            "scorpione": ("01_scorpione_lanterna",  "Scorpione"),
            "fennec":    ("02_fennec_solare",       "Fennec"),
            "scarabeo":  ("03_scarabeo_fornace",    "Scarabeo"),
            "vipera":    ("04_vipera_sonaglio",     "Vipera"),
            "lucertola": ("05_lucertola_cristallo", "Lucertola"),
            "avvoltoio": ("06_avvoltoio_miraggio",  "Avvoltoio"),
            "tarantola": ("07_tarantola_brace",     "Tarantola"),
            "cactus":    ("08_cactus_chill_guy",    "Cactus"),
        },
    },
    "neve": {
        "registro": NV.CREATURE_NEVE,
        "cartella": os.path.join("modelli", "neve"),
        "creature": {
            "orso":     ("01_orso_aurora",        "Orso"),
            "pinguino": ("02_pinguino_cristallo", "Pinguino"),
            "renna":    ("03_renna_cometa",       "Renna"),
            "volpe":    ("04_volpe_ghiacciaio",   "Volpe"),
            "leopardo": ("05_leopardo_valanga",   "Leopardo"),
            "yeti":     ("06_falena_yeti",        "Yeti"),
            "civetta":  ("07_civetta_bufera",     "Civetta"),
            "pupazzo":  ("08_pupazzo_skibidi",    "Pupazzo"),
        },
    },
    "oceano": {
        "registro": OC.CREATURE_OCEANO,
        "cartella": os.path.join("modelli", "oceano"),
        "creature": {
            "medusa":     ("01_medusa_lanterna",       "Medusa"),
            "cavalluccio": ("02_cavalluccio_neon",     "Cavalluccio"),
            "granchio":   ("03_granchio_faro",         "Granchio"),
            "manta":      ("04_manta_luminescente",    "Manta"),
            "squalo":     ("05_squalo_plasma",         "Squalo"),
            "tartaruga":  ("06_tartaruga_fosforica",   "Tartaruga"),
            "pescatrice": ("07_rana_pescatrice_abisso", "Pescatrice"),
            "blobfish":   ("08_blobfish_mewing",       "Blobfish"),
        },
    },
}


# ============================================================================
# Utilita'
# ============================================================================

def srgb(c):
    """Colore lineare di Blender -> Color3 (sRGB) di Roblox."""
    out = []
    for x in list(c)[:3]:
        x = max(0.0, min(1.0, float(x)))
        out.append(round(12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055, 4))
    return out


def short(name):
    """'Mantide_AlaPosteriore_Perno_R' -> 'AlaPosteriore_R'."""
    name = name.split("_", 1)[1] if "_" in name else name
    return name.replace("_Perno", "")


def select_only(obs, active=None):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or obs[0]


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def is_open(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    res = any(not e.is_manifold for e in bm.edges)
    bm.free()
    return res


def rest_pose():
    """Toglie i driver e rimette ogni proprieta' animata al valore di riposo."""
    for owner, path, idx, val in CL.VALORI_RIPOSO:
        try:
            if idx >= 0:
                owner.driver_remove(path, idx)
                getattr(owner, path)[idx] = val
            else:
                owner.driver_remove(path)
                setattr(owner, path, val)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            pass
    bpy.context.view_layer.update()


def skip(ob):
    """Emettitori di particelle e oggetti che esistono solo in Blender."""
    return bool(ob.get("rbx_drop"))


def mat_of(ob):
    for slot in ob.material_slots:
        if slot.material is not None:
            return slot.material
    return None


def needs_thickness(ob, m):
    """Solo le ali vengono ispessite: le piume stanno appoggiate sul corpo."""
    return bool(m.get("rbx_wing")) or (m.get("rbx_kind") == "glass")


def evaluated_mesh(ob, dg):
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(ob.matrix_world)
    return me


def with_modifier(me, kind, **props):
    tmp = bpy.data.objects.new("tmp_mod", me)
    bpy.context.scene.collection.objects.link(tmp)
    md = tmp.modifiers.new("mod", kind)
    for k, v in props.items():
        setattr(md, k, v)
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    return out


# ============================================================================
# Bake delle texture
# ============================================================================

def new_image(name, res, non_color=False, alpha=False):
    w, h = (res, res) if isinstance(res, int) else (int(res[0]), int(res[1]))
    img = bpy.data.images.new(name, w, h, alpha=alpha, float_buffer=False)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img


def pixels(img):
    a = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def bake_textures(mat, ob, res, texdir, base):
    """Cuoce le uscite RBX_* del materiale sull'oggetto (che deve avere UV).
    Restituisce dict con le immagini salvate: color (RGBA), emit, normal."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1
    sc.render.bake.margin = 8
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    old_surf = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None
    old_vol = out.inputs['Volume'].links[0].from_socket if out.inputs['Volume'].is_linked else None
    if old_vol is not None:
        nt.links.remove(out.inputs['Volume'].links[0])
    tex = nt.nodes.new('ShaderNodeTexImage')
    nt.nodes.active = tex
    select_only([ob])
    done = {}
    for key, node_name, non_color in (("color", "RBX_COLOR", False), ("emit", "RBX_EMIT", False),
                                      ("alpha", "RBX_ALPHA", True)):
        nd = nt.nodes.get(node_name)
        if nd is None:
            continue
        img = new_image("%s_%s" % (base, key), res, non_color)
        tex.image = img
        nt.links.new(nd.outputs[0], out.inputs['Surface'])
        bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
        done[key] = img
    if old_surf is not None:
        nt.links.new(old_surf, out.inputs['Surface'])
    if mat.get("rbx_normal"):
        img = new_image("%s_normal" % base, res, True)
        tex.image = img
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=8, use_clear=True)
        done["normal"] = img
    nt.nodes.remove(tex)
    if old_vol is not None:
        nt.links.new(old_vol, out.inputs['Volume'])

    # salva su disco: colore (+ trasparenza) PNG, emissione JPEG, normali PNG
    os.makedirs(texdir, exist_ok=True)
    saved = {}
    if "color" in done:
        img = done["color"]
        if "alpha" in done:
            px = pixels(img)
            px[:, 3] = pixels(done["alpha"])[:, 0]
            rgba = new_image(base + "_colore", res, alpha=True)
            rgba.pixels.foreach_set(px.ravel())
            img = rgba
        saved["color"] = save_image(img, texdir, base + "_colore", 'PNG' if "alpha" in done else 'JPEG')
    if "emit" in done:
        saved["emit"] = save_image(done["emit"], texdir, base + "_emissione", 'JPEG')
    if "normal" in done:
        saved["normal"] = save_image(done["normal"], texdir, base + "_normali", 'PNG', non_color=True)
    saved["alpha"] = "alpha" in done
    return saved


def save_image(img, texdir, name, fmt, non_color=False):
    ext = ".png" if fmt == 'PNG' else ".jpg"
    path = os.path.join(texdir, name + ext)
    img.filepath_raw = path
    img.file_format = fmt
    img.save()
    loaded = bpy.data.images.load(path, check_existing=False)
    loaded.name = name
    if non_color:
        loaded.colorspace_settings.name = 'Non-Color'
    return loaded


def bake_res(m, default):
    r = m.get("rbx_res")
    if r is None:
        return default
    return [int(x) for x in r] if hasattr(r, "__len__") else int(r)


# ============================================================================
# Materiali per l'esportazione (Principled BSDF semplici, leggibili dal glTF)
# ============================================================================

def export_material(name, src, tex=None):
    mat = bpy.data.materials.new(name)
    nb = CL.NodeBuilder(mat)
    kind = src.get("rbx_kind", "solid")
    base = list(src.get("rbx_color", (0.5, 0.5, 0.5)))
    rough = float(src.get("rbx_rough", 0.5))
    metal = float(src.get("rbx_metal", 0.0))
    bsdf = nb.principled(rough=rough, metal=metal, spec=0.5)
    if tex:
        t = nb.node('ShaderNodeTexImage')
        t.image = tex["color"]
        nb.link(t.outputs['Color'], bsdf.inputs['Base Color'])
        if tex.get("alpha"):
            nb.link(t.outputs['Alpha'], bsdf.inputs['Alpha'])
            CL.set_transparent(mat)
        if tex.get("emit"):
            te = nb.node('ShaderNodeTexImage')
            te.image = tex["emit"]
            nb.link(te.outputs['Color'], nb.socket(bsdf, CL.PRINCIPLED_ALIASES['emit']))
            nb.set(bsdf, CL.PRINCIPLED_ALIASES['emit_str'], 1.0)
        if tex.get("normal"):
            tn = nb.node('ShaderNodeTexImage')
            tn.image = tex["normal"]
            nm = nb.node('ShaderNodeNormalMap')
            nb.link(tn.outputs['Color'], nm.inputs['Color'])
            nb.link(nm.outputs['Normal'], bsdf.inputs['Normal'])
    else:
        nb.set(bsdf, 'Base Color', base)
        if kind in ("neon", "aura"):
            nb.set(bsdf, CL.PRINCIPLED_ALIASES['emit'], base)
            nb.set(bsdf, CL.PRINCIPLED_ALIASES['emit_str'], 1.0)
        if kind in ("aura", "ghost", "glass"):
            nb.set(bsdf, 'Alpha', 0.4)
            CL.set_transparent(mat)
    nb.output(bsdf.outputs[0])
    return mat


# ============================================================================
# Unione dei pezzi, UV, decimazione
# ============================================================================

def join_chunks(meshes):
    """meshes: lista di mesh gia' in coordinate mondo. Restituisce liste di bmesh."""
    chunks, cur, cur_t = [], None, 0
    for me in meshes:
        t = tris(me)
        if cur is None or cur_t + t > MAX_TRIANGOLI_MESH:
            if cur is not None:
                chunks.append(cur)
            cur, cur_t = bmesh.new(), 0
        cur.from_mesh(me)
        cur_t += t
    if cur is not None:
        chunks.append(cur)
    return chunks


def smart_uv(ob):
    select_only([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')


def new_object(name, me):
    me.name = name
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def marker_mesh(loc, size):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    me = bpy.data.meshes.new("marcatore")
    bm.to_mesh(me)
    bm.free()
    return me


# ============================================================================
# Costruzione con il livello di dettaglio giusto
# ============================================================================

def build_creature(key, registry, detail):
    CL.DETTAGLIO = detail
    CL.clear_scene()
    CL.setup_render("CYCLES")
    CL.build_one(key, registry=registry)
    CL.DETTAGLIO = 1.0
    anims = list(CL.ANIMAZIONI)
    rest_pose()
    coll = bpy.data.collections[registry[key][0]]
    return anims, list(coll.all_objects)


def estimate_tris(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    tot = 0
    for ob in objs:
        if ob.type not in ('MESH', 'CURVE') or skip(ob):
            continue
        m = mat_of(ob)
        if m is None or m.get("rbx_kind") == "drop":
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        t = tris(me)
        if needs_thickness(ob, m) and is_open(me):
            t = int(t * 2.15)
        tot += t
        bpy.data.meshes.remove(me)
    return tot


# ============================================================================
# Esportazione di una creatura
# ============================================================================

def export_creature(serie, key, outdir, texroot, scala, budget):
    info = SERIE[serie]
    fname, P = info["creature"][key]
    registry = info["registro"]
    S = Matrix.Scale(scala, 4)

    # 1) livello di dettaglio: si riduce finche' la stima sta nel budget
    detail = 1.0
    for _it in range(8):
        anims, objs = build_creature(key, registry, detail)
        if budget <= 0:                          # nessun limite: dettaglio pieno
            break
        est = estimate_tris(objs) + 400          # + marcatori
        if est <= budget * 0.98 or detail <= 0.16:
            break
        detail = max(0.15, detail * max(0.45, min(0.92, math.sqrt(budget * 0.95 / est))))
    texdir = os.path.join(texroot, fname)

    # --- chi si anima e come --------------------------------------------------
    def ptr(x):
        return x.as_pointer()

    rot = {}          # pivot -> lista di (asse, amp, cyc, ph, spin, mov)
    own = {}          # oggetto -> ('scala'|'bob', meta)
    light_pulse = {}  # dati luce -> meta
    light_color = {}  # dati luce -> ciclo di colori
    for a in anims:
        o = a["owner"]
        if a["tipo"] in ("rot", "mov"):
            mov = a["tipo"] == "mov"
            rot.setdefault(ptr(o), (o, []))[1].append(
                ("XYZ"[a["index"]], a["amp"] * (scala if mov else 1.0), a["cyc"], a["ph"],
                 bool(a.get("spin")), mov))
        elif a["tipo"] in ("scala", "bob"):
            own[ptr(o)] = (a["tipo"], a)
        elif a["tipo"] == "luce":
            light_pulse[ptr(o)] = a
        elif a["tipo"] == "colore":
            light_color[ptr(o)] = a

    def group_of(ob):
        o = ob
        while o is not None:
            if ptr(o) in rot:
                return o.name
            o = o.parent
        if ptr(ob) in own:
            return ob.name
        return None

    marker_size = 0.03
    finals = []       # (nome, mesh in coordinate mondo NON scalate, gruppo, (materiale, texture) | None)
    cfg = {"parti": {}, "luci": {}, "perni": {}, "scala": {}, "bob": {}}

    # --- marcatori: radice, assi, perni, luci ---------------------------------
    finals.append((P + "__Radice", marker_mesh((0, 0, 0), marker_size), None, None))
    for i, ax in enumerate("XYZ"):
        d = Vector((0, 0, 0))
        d[i] = 0.5
        finals.append((P + "__Asse" + ax, marker_mesh(d, marker_size), None, None))
    pivot_names = {}
    for pp, (o, lst) in rot.items():
        mname = "%s__Perno_%s" % (P, short(o.name))
        pivot_names[o.name] = mname
        finals.append((mname, marker_mesh(o.matrix_world.translation, marker_size), None, None))
    for pp, (o, lst) in rot.items():
        par = o.parent
        while par is not None and ptr(par) not in rot:
            par = par.parent
        entry = []
        for ax, amp, cyc, ph, spin, mov in sorted(lst):
            r = {"asse": ax, "amp": round(amp, 4), "cyc": cyc, "ph": round(ph, 3)}
            if spin:
                r["spin"] = True
            if mov:
                r["mov"] = True           # spostamento (in stud) invece che rotazione
            entry.append(r)
        cfg["perni"][pivot_names[o.name]] = {
            "padre": pivot_names[par.name] if par is not None else None,
            "rot": entry,
            "membri": [],
        }
    n_light = 0
    for ob in objs:
        if ob.type != 'LIGHT':
            continue
        n_light += 1
        mname = "%s__Luce_%02d" % (P, n_light)
        pos = ob.matrix_world.translation
        finals.append((mname, marker_mesh(pos, marker_size), group_of(ob), None))
        e = ob.data.energy
        pulse = light_pulse.get(ptr(ob.data))
        lo, hi = (pulse["lo"], pulse["hi"]) if pulse else (e, e)
        top = 10.0 if ob.data.type == 'SPOT' else 5.0
        entry = {
            "c": srgb(ob.data.color),
            "b0": round(min(top, max(0.15, 0.45 * math.sqrt(lo))), 3),
            "b1": round(min(top, max(0.15, 0.45 * math.sqrt(hi))), 3),
            "cyc": pulse["cyc"] if pulse else 1,
            "ph": round(pulse["ph"], 3) if pulse else 0.0,
            "r": round(min(60.0, scala * (1.5 + 0.35 * math.sqrt(max(lo, hi)))), 2),
        }
        if ob.data.type == 'SPOT':
            fwd = (ob.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
            dname = mname + "_Dir"
            finals.append((dname, marker_mesh(pos + fwd * 0.5, marker_size), group_of(ob), None))
            entry["dir"] = dname
            entry["ang"] = round(min(180.0, math.degrees(ob.data.spot_size)), 1)
        cc = light_color.get(ptr(ob.data))
        if cc:
            entry["cc"] = color_cycle(cc)
        cfg["luci"][mname] = entry

    # --- bake dei materiali con UV proprie (ali, piume, serpente, carapace) -----
    baked = {}
    for ob in objs:
        if ob.type != 'MESH' or skip(ob):
            continue
        m = mat_of(ob)
        if m is None or m.get("rbx_kind") != "bake" or m.name in baked:
            continue
        if m.get("rbx_wing") and not ob.name.endswith("_R"):
            continue                        # l'ala sinistra usa la stessa texture (specchiata)
        if (m.get("rbx_wing") or m.get("rbx_uv_only")) and ob.data.uv_layers:
            res = bake_res(m, 1024 if m.get("rbx_wing") else 512)
            baked[m.name] = bake_textures(m, ob, res, texdir, short(m.name))

    # --- mesh finali: curve -> mesh, modificatori applicati, spessore alle ali --
    dg = bpy.context.evaluated_depsgraph_get()
    pieces = {}       # (gruppo, materiale) -> lista di mesh
    for ob in objs:
        if ob.type not in ('MESH', 'CURVE') or skip(ob):
            continue
        m = mat_of(ob)
        if m is None or m.get("rbx_kind") == "drop":
            continue
        me = evaluated_mesh(ob, dg)
        if needs_thickness(ob, m) and is_open(me):
            me = with_modifier(me, 'SOLIDIFY', thickness=SPESSORE, offset=0.0)
        pieces.setdefault((group_of(ob), m.name), []).append(me)

    for (grp, mname), mes in sorted(pieces.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        src = bpy.data.materials[mname]
        label = short(mname) + ("__" + short(grp) if grp else "")
        chunks = join_chunks(mes)
        for ci, bm in enumerate(chunks):
            name = "%s__%s%s" % (P, label, "_%d" % (ci + 1) if len(chunks) > 1 else "")
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            bm.free()
            for poly in me.polygons:
                poly.material_index = 0
            me.materials.clear()
            me.materials.append(src)
            finals.append((name, me, grp, [src, baked.get(mname)]))

    # --- 2) se si e' ancora sopra il budget: decimazione proporzionale ---------------
    def total():
        return sum(tris(f[1]) for f in finals)

    for _it in range(4 if budget > 0 else 0):
        tot = total()
        if tot <= budget:
            break
        fixed = sum(tris(f[1]) for f in finals if f[3] is None or tris(f[1]) < 60)
        ratio = max(0.05, (budget * 0.97 - fixed) / max(1, tot - fixed))
        for i, (name, me, grp, info) in enumerate(finals):
            if info is None or tris(me) < 60:
                continue
            finals[i] = (name, with_modifier(me, 'DECIMATE', decimate_type='COLLAPSE', ratio=ratio), grp, info)

    # --- bake dei materiali che vanno cotti dopo l'unione (UV automatiche) ------------
    for i, (name, me, grp, info) in enumerate(finals):
        if info is None:
            continue
        src, tex = info
        if src.get("rbx_kind") == "bake" and tex is None:
            ob = new_object(name + "_bake", me)
            smart_uv(ob)
            info[1] = bake_textures(src, ob, bake_res(src, 1024), texdir, short(name))
            bpy.data.objects.remove(ob)

    # --- impostazioni per lo script Luau ----------------------------------------------
    for name, me, grp, info in finals:
        if grp is not None:
            if grp in pivot_names:
                cfg["perni"][pivot_names[grp]]["membri"].append(name)
            else:
                src_ob = bpy.data.objects[grp]
                tipo, meta = own[ptr(src_ob)]
                if tipo == "scala":
                    cfg["scala"][name] = {"lo": meta["lo"], "hi": meta["hi"], "cyc": meta["cyc"],
                                          "ph": meta["ph"]}
                else:
                    cfg["bob"][name] = {"amp": round(meta["amp"] * scala, 3), "cyc": meta["cyc"],
                                        "ph": round(meta["ph"], 3)}
        if info is None:
            continue
        src = info[0]
        kind = src.get("rbx_kind", "solid")
        if kind in ("neon", "aura"):
            s = {"k": kind, "c": srgb(src["rbx_color"])}
            if kind == "aura":
                s["t"] = 0.85
            elif src.get("rbx_transp"):
                s["t"] = float(src["rbx_transp"])
            if src.get("rbx_pulse"):
                s["p"] = [round(float(x), 3) for x in src["rbx_pulse"]]
        elif kind == "ghost":
            s = {"k": "ghost", "c": srgb(src["rbx_color"])}
        elif kind == "glass":
            s = {"k": "glass", "c": srgb(src["rbx_color"]), "t": float(src.get("rbx_transp", 0.6))}
        elif kind == "bake":
            s = {"k": "tex"}
            if src.get("rbx_emit_strength"):
                s["e"] = round(min(40.0, 4.0 * float(src["rbx_emit_strength"])), 2)
            if src.get("rbx_wing"):
                s["ali"] = True
        else:
            s = {"k": "solid", "c": srgb(src.get("rbx_color", (0.5, 0.5, 0.5)))}
            if float(src.get("rbx_metal", 0.0)) > 0.5:
                s["metallo"] = True
        if src.get("rbx_material") and kind not in ("bake",):
            s["m"] = str(src["rbx_material"])
        if src.get("rbx_cycle"):
            s["cc"] = color_cycle(src["rbx_cycle"])
        if src.get("rbx_rifl"):
            s["rifl"] = float(src["rbx_rifl"])
        if src.get("rbx_highlight"):
            s["h"] = srgb(src["rbx_highlight"])
        cfg["parti"][name] = s

    # --- oggetti finali, scalati per Roblox, ed esportazione glTF --------------------
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.context.view_layer.update()
    mat_cache = {}
    marker_mat = bpy.data.materials.new("RBX_Marcatore")
    marker_mat.diffuse_color = (1, 0, 1, 1)
    export_obs = []
    for name, me, grp, info in finals:
        me.transform(S)
        me.materials.clear()
        if info is None:
            me.materials.append(marker_mat)
        else:
            src, tex = info
            key_m = (src.name, id(tex))
            if key_m not in mat_cache:
                mat_cache[key_m] = export_material("%s_%s" % (P, short(src.name)), src, tex)
            me.materials.append(mat_cache[key_m])
        export_obs.append(new_object(name, me))

    folder = os.path.join(outdir, info_dir(serie))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, fname + ".glb")
    select_only(export_obs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_image_format='AUTO', export_animations=False,
        export_lights=False, export_cameras=False, export_extras=False,
        export_materials='EXPORT', export_texcoords=True, export_normals=True)
    tot = sum(tris(o.data) for o in export_obs)
    big = max(tris(o.data) for o in export_obs)
    print("[roblox] %-24s dettaglio %.2f  %3d pezzi  %6d triangoli (max %5d per pezzo)  -> %s"
          % (fname, detail, len(export_obs), tot, big, os.path.relpath(path)))
    if 0 < budget < tot:
        print("[roblox] ATTENZIONE: %s supera il limite (%d > %d)" % (fname, tot, budget))
    return P, cfg


def color_cycle(cc):
    """Ciclo di colori per lo script Luau: tavolozza (sRGB), giri per ciclo, fase."""
    return {"pal": [srgb(list(c)) for c in cc["pal"]], "cyc": float(cc["cyc"]),
            "ph": round(float(cc["ph"]), 4)}


def info_dir(serie):
    return SERIE[serie]["cartella"]


# ============================================================================
# Script Luau
# ============================================================================

def lua_value(v, ind=0):
    pad = "    " * ind
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 4)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return '"%s"' % v.replace('"', '\\"')
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (int, float)) for x in v):
            return "{" + ", ".join(lua_value(x) for x in v) + "}"
        return "{\n" + "".join("%s    %s,\n" % (pad, lua_value(x, ind + 1)) for x in v) + pad + "}"
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = []
        for k in sorted(v):
            items.append('%s    ["%s"] = %s,\n' % (pad, k, lua_value(v[k], ind + 1)))
        return "{\n" + "".join(items) + pad + "}"
    raise TypeError(type(v))


def write_lua(outdir):
    """Unisce le configurazioni di tutte le creature esportate in un solo script."""
    configs = {}
    for path in sorted(glob.glob(os.path.join(DATI, "*.json"))):
        with open(path, encoding="utf-8") as f:
            configs[os.path.splitext(os.path.basename(path))[0]] = json.load(f)
    with open(os.path.join(QUI, "roblox_template.lua"), encoding="utf-8") as f:
        tpl = f.read()
    body = "local CONFIG = " + lua_value(configs) + "\n"
    ciclo = CL.ANIM_FRAMES / 24.0
    lua = tpl.replace("--@@CONFIG@@", body).replace("--@@CICLO@@", "local CICLO = %.3f" % ciclo)
    path = os.path.join(outdir, "CreatureLuminose.client.lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(lua)
    print("[roblox] script Luau (%d creature) -> %s" % (len(configs), os.path.relpath(path)))


# ============================================================================

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {}
    for i, a in enumerate(args):
        if a.startswith("--") and i + 1 < len(args):
            opts[a[2:]] = args[i + 1]
    outdir = os.path.abspath(opts.get("uscita", os.path.join(QUI, "..", "roblox")))
    texroot = os.path.abspath(opts.get("texture", os.path.join(outdir, "_texture_temp")))
    scala = float(opts.get("scala", SCALA))
    budget = int(opts.get("max-triangoli", MAX_TRIANGOLI_CREATURA))
    serie = [opts["serie"]] if "serie" in opts else list(SERIE)
    os.makedirs(DATI, exist_ok=True)
    for sname in serie:
        keys = list(SERIE[sname]["creature"])
        if "creatura" in opts:
            if opts["creatura"] not in keys:
                continue
            keys = [opts["creatura"]]
        for k in keys:
            prefix, cfg = export_creature(sname, k, outdir, texroot, scala, budget)
            with open(os.path.join(DATI, prefix + ".json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=1, sort_keys=True)
    write_lua(outdir)


if __name__ == "__main__":
    main()
