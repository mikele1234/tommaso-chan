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

--@@CICLO@@

--@@CONFIG@@

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
