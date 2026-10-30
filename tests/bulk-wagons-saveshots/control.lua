-- Loaded into a copy of a save by tests/save_shots.py: finds the bunkers and silos of the
-- save and takes screenshots of them, an overview of each group and a close-up of each
-- station with a wagon under it.

local BASES = { "bulk-unloading-bunker", "bulk-loading-silo" }
local MAX_SHOTS = 24
-- stations closer than this belong to one group (one overview)
local GROUP_RADIUS = 30

local function is_station(name)
  for _, base in pairs(BASES) do
    if name:sub(1, #base) == base and not name:find("-store-", 1, true) then return base end
  end
end

local function find_stations()
  local found = {}
  for _, surface in pairs(game.surfaces) do
    for _, e in pairs(surface.find_entities_filtered({ type = "simple-entity-with-owner" })) do
      local base = is_station(e.name)
      if base then
        local wagon = surface.find_entities_filtered({ type = "cargo-wagon", position = e.position, radius = 3.5 })[1]
        found[#found + 1] = { surface = surface, base = base, entity = e, position = e.position,
          docked = wagon ~= nil and wagon.name:find("bulk-wagon", 1, true) ~= nil }
        log(string.format("BULKSHOTS station %s %s %s docked=%s", surface.name, e.name,
          serpent.line(e.position), tostring(found[#found].docked)))
      end
    end
  end
  return found
end

local function groups_of(stations)
  local groups = {}
  for _, s in pairs(stations) do
    local home
    for _, g in pairs(groups) do
      local d = (g.x / g.n - s.position.x) ^ 2 + (g.y / g.n - s.position.y) ^ 2
      if g.surface == s.surface and d < GROUP_RADIUS ^ 2 then home = g break end
    end
    if not home then
      home = { surface = s.surface, x = 0, y = 0, n = 0, stations = {} }
      groups[#groups + 1] = home
    end
    home.x, home.y, home.n = home.x + s.position.x, home.y + s.position.y, home.n + 1
    home.stations[#home.stations + 1] = s
  end
  return groups
end

local function plan()
  local shots = {}
  local function add(name, surface, position, zoom)
    if #shots < MAX_SHOTS then
      shots[#shots + 1] = { name = name, surface = surface, position = position, zoom = zoom }
    end
  end
  local groups = groups_of(find_stations())
  log("BULKSHOTS groups " .. #groups)
  for i, g in pairs(groups) do
    local tag = string.format("%02d-%s", i, g.surface.name)
    add(tag .. "-overview", g.surface, { g.x / g.n, g.y / g.n }, 0.5)
    add(tag .. "-group", g.surface, { g.x / g.n, g.y / g.n }, 1)
    for j, s in pairs(g.stations) do
      if s.docked then
        local kind = s.base == "bulk-loading-silo" and "silo" or "bunker"
        add(string.format("%s-%s-%d", tag, kind, j), g.surface, s.position, 2)
      end
    end
  end
  return shots
end

script.on_event(defines.events.on_tick, function(event)
  -- a few ticks first, so heaps and fill levels are drawn
  if event.tick < (storage.start or event.tick) + 30 then
    storage.start = storage.start or event.tick
    return
  end
  if storage.done then return end
  storage.done = true
  for _, shot in pairs(plan()) do
    game.take_screenshot({
      surface = shot.surface,
      position = shot.position,
      resolution = { 1920, 1080 },
      zoom = shot.zoom,
      path = "bulk-saveshots/" .. shot.name .. ".png",
      show_entity_info = false,
      daytime = 0,
      allow_in_replay = true,
      anti_alias = true,
    })
    log("BULKSHOTS shot " .. shot.name .. " " .. serpent.line(shot.position))
  end
  log("BULKSHOTS DONE")
end)
