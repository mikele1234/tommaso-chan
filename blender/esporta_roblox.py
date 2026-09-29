# -*- coding: utf-8 -*-
"""
ESPORTAZIONE DELLE CREATURE LUMINOSE PER ROBLOX STUDIO

Costruisce ogni creatura con `creature_luminose.py` e la prepara per Roblox:

  * curve, metaball e modificatori diventano mesh normali;
  * ali, piume e foglie ricevono un minimo di spessore (su Roblox le mesh
    piatte si vedono da un lato solo);
  * i materiali procedurali vengono "cotti" (bake) in texture: colore con
    trasparenza, mappa emissiva (Roblox la trasforma in Emissive Mask) e,
    dove serve, normal map;
  * i pezzi con lo stesso materiale vengono uniti, restando sotto il limite
    di 20.000 triangoli per mesh di Roblox;
  * luci e perni delle animazioni diventano piccoli marcatori invisibili,
    usati dallo script Luau per ricreare luci, Neon e animazioni.

Risultato (nella cartella di uscita):
    modelli/<nn>_<nome>.glb        un file per creatura, texture incluse
    CreatureLuminose.client.lua    LocalScript con luci, Neon e animazioni

USO
    blender --background --python blender/esporta_roblox.py -- --uscita roblox
    opzioni: --creatura gatto   (solo una)   --scala 3   (metri Blender -> stud)
"""

import bpy
import bmesh
import importlib.util
import math
import os
import sys

import numpy as np
from mathutils import Matrix, Vector

QUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "creature_luminose", os.path.join(QUI, "creature_luminose.py"))
CL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CL)

# Fattore di scala: 1 metro in Blender -> SCALA stud su Roblox.
# Con 3 le creature sono alte 3-7 stud (un avatar Roblox e' circa 5 stud).
SCALA = 3.0
MAX_TRIANGOLI = 19000          # Roblox: massimo 20.000 per mesh
SPESSORE = 0.004               # spessore dato alle superfici piatte (metri)

CREATURE_RBX = {
    #  chiave      file                    prefisso dei pezzi su Roblox
    "mantide":   ("01_mante_luce",        "Mantide"),
    "gatto":     ("02_gattoluna",         "Gatto"),
    "gufo":      ("03_gufo_scintilla",    "Gufo"),
    "rana":      ("04_ranabuio",          "Rana"),
    "farfalla":  ("05_farfalla_glow",     "Farfalla"),
    "libellula": ("06_libellula_fulmine", "Libellula"),
    "lupo":      ("07_lupo_luce",         "Lupo"),
    "falena":    ("08_lucina_farfallina", "Lucina"),
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


def mat_of(ob):
    for slot in ob.material_slots:
        if slot.material is not None:
            return slot.material
    return None


# ============================================================================
# Bake delle texture
# ============================================================================

def new_image(name, res, non_color=False):
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
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

    # salva su disco: colore (+ trasparenza) PNG, emissione e normali JPEG
    os.makedirs(texdir, exist_ok=True)
    saved = {}
    if "color" in done:
        img = done["color"]
        if "alpha" in done:
            px = pixels(img)
            px[:, 3] = pixels(done["alpha"])[:, 0]
            rgba = bpy.data.images.new(base + "_colore", res, res, alpha=True)
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
        if kind in ("aura", "ghost"):
            nb.set(bsdf, 'Alpha', 0.4)
            CL.set_transparent(mat)
    nb.output(bsdf.outputs[0])
    return mat


# ============================================================================
# Unione dei pezzi (con suddivisione sotto il limite di triangoli)
# ============================================================================

def join_chunks(meshes):
    """meshes: lista di mesh gia' in coordinate mondo. Restituisce liste di bmesh."""
    chunks, cur, cur_t = [], None, 0
    for me in meshes:
        t = tris(me)
        if cur is None or cur_t + t > MAX_TRIANGOLI:
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
# Esportazione di una creatura
# ============================================================================

def export_creature(key, outdir, texroot, scala):
    fname, P = CREATURE_RBX[key]
    title = CL.CREATURE[key][0]
    CL.clear_scene()
    CL.setup_render("CYCLES")
    CL.build_one(key)
    anims = list(CL.ANIMAZIONI)
    rest_pose()
    coll = bpy.data.collections[title]
    objs = list(coll.all_objects)
    texdir = os.path.join(texroot, fname)
    S = Matrix.Scale(scala, 4)

    # --- chi si anima e come --------------------------------------------------
    def ptr(x):
        return x.as_pointer()

    rot = {}          # pivot -> lista di (asse, amp, cyc, ph)
    own = {}          # oggetto -> ('scala'|'bob', meta)
    light_pulse = {}  # dati luce -> meta
    for a in anims:
        o = a["owner"]
        if a["tipo"] == "rot":
            rot.setdefault(ptr(o), (o, []))[1].append(("XYZ"[a["index"]], a["amp"], a["cyc"], a["ph"]))
        elif a["tipo"] in ("scala", "bob"):
            own[ptr(o)] = (a["tipo"], a)
        elif a["tipo"] == "luce":
            light_pulse[ptr(o)] = a

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
    finals = []       # (nome, mesh in coordinate mondo NON scalate, gruppo, materiale export)
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
        cfg["perni"][pivot_names[o.name]] = {
            "padre": pivot_names[par.name] if par is not None else None,
            "rot": [{"asse": ax, "amp": round(amp, 4), "cyc": cyc, "ph": round(ph, 3)}
                    for ax, amp, cyc, ph in sorted(lst)],
            "membri": [],
        }
    n_light = 0
    for ob in objs:
        if ob.type != 'LIGHT':
            continue
        n_light += 1
        mname = "%s__Luce_%02d" % (P, n_light)
        finals.append((mname, marker_mesh(ob.matrix_world.translation, marker_size), group_of(ob), None))
        e = ob.data.energy
        pulse = light_pulse.get(ptr(ob.data))
        lo, hi = (pulse["lo"], pulse["hi"]) if pulse else (e, e)
        cfg["luci"][mname] = {
            "c": srgb(ob.data.color),
            "b0": round(min(5.0, max(0.15, 0.45 * math.sqrt(lo))), 3),
            "b1": round(min(5.0, max(0.15, 0.45 * math.sqrt(hi))), 3),
            "cyc": pulse["cyc"] if pulse else 1,
            "ph": round(pulse["ph"], 3) if pulse else 0.0,
            "r": round(min(60.0, scala * (1.5 + 0.35 * math.sqrt(max(lo, hi)))), 2),
        }

    # --- bake dei materiali che lo richiedono (sugli oggetti originali) -----------
    baked = {}
    for ob in objs:
        if ob.type != 'MESH':
            continue
        m = mat_of(ob)
        if m is None or m.get("rbx_kind") != "bake" or m.name in baked:
            continue
        if m.get("rbx_wing") and not ob.name.endswith("_R"):
            continue                        # l'ala sinistra usa la stessa texture (specchiata)
        if (m.get("rbx_wing") or m.get("rbx_uv_only")) and ob.data.uv_layers:
            res = 1024 if m.get("rbx_wing") else 512
            baked[m.name] = bake_textures(m, ob, res, texdir, short(m.name))

    # --- mesh finali: curve -> mesh, modificatori applicati, spessore ----------
    dg = bpy.context.evaluated_depsgraph_get()
    pieces = {}       # (gruppo, materiale) -> lista di mesh
    for ob in objs:
        if ob.type not in ('MESH', 'CURVE'):
            continue
        m = mat_of(ob)
        if m is None or m.get("rbx_kind") == "drop":
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        me.transform(ob.matrix_world)
        if is_open(me):
            tmp = bpy.data.objects.new("tmp_spessore", me)
            bpy.context.scene.collection.objects.link(tmp)
            sd = tmp.modifiers.new("Spessore", 'SOLIDIFY')
            sd.thickness = SPESSORE
            sd.offset = 0.0
            dg2 = bpy.context.evaluated_depsgraph_get()
            me2 = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg2))
            bpy.data.objects.remove(tmp)
            me = me2
        pieces.setdefault((group_of(ob), m.name), []).append(me)

    # per i materiali uniti con UV nuove (pelle, corteccia) si fa il bake dopo l'unione
    for (grp, mname), mes in sorted(pieces.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        src = bpy.data.materials[mname]
        kind = src.get("rbx_kind", "solid")
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
            tex = baked.get(mname)
            if kind == "bake" and tex is None:
                ob = new_object(name + "_bake", me)
                smart_uv(ob)
                tex = bake_textures(src, ob, 1024, texdir, short(name))
                bpy.data.objects.remove(ob)
            finals.append((name, me, grp, (src, tex)))

    # --- impostazioni per lo script Luau --------------------------------------------
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
        src, tex = info
        kind = src.get("rbx_kind", "solid")
        s = {}
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

    os.makedirs(os.path.join(outdir, "modelli"), exist_ok=True)
    path = os.path.join(outdir, "modelli", fname + ".glb")
    select_only(export_obs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_image_format='AUTO', export_animations=False,
        export_lights=False, export_cameras=False, export_extras=False,
        export_materials='EXPORT', export_texcoords=True, export_normals=True)
    tot = sum(tris(o.data) for o in export_obs)
    big = max(tris(o.data) for o in export_obs)
    print("[roblox] %-22s %3d pezzi  %6d triangoli (max %5d per pezzo)  -> %s"
          % (fname, len(export_obs), tot, big, path))
    return P, cfg


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


def write_lua(outdir, configs):
    with open(os.path.join(QUI, "roblox_template.lua"), encoding="utf-8") as f:
        tpl = f.read()
    body = "local CONFIG = " + lua_value(configs) + "\n"
    ciclo = CL.ANIM_FRAMES / 24.0
    lua = tpl.replace("--@@CONFIG@@", body).replace("--@@CICLO@@", "local CICLO = %.3f" % ciclo)
    path = os.path.join(outdir, "CreatureLuminose.client.lua")
    with open(path, "w", encoding="utf-8") as f:
        f.write(lua)
    print("[roblox] script Luau ->", path)


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
    keys = [opts["creatura"]] if "creatura" in opts else list(CREATURE_RBX)
    configs = {}
    for k in keys:
        prefix, cfg = export_creature(k, outdir, texroot, scala)
        configs[prefix] = cfg
    write_lua(outdir, configs)


if __name__ == "__main__":
    main()
