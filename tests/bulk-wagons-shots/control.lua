-- Builds a showcase scene and takes screenshots (tests/shots.py runs it with --benchmark-graphics).

local function rail_line(surface, vertical, fixed, from, to)
  for c = from, to, 2 do
    surface.create_entity({
      name = "straight-rail",
      position = vertical and { fixed, c } or { c, fixed },
      direction = vertical and defines.direction.north or defines.direction.east,
      force = "player",
    })
  end
end

-- A halted train at a train stop: the locomotive at the stop, wagons behind it on
-- the wagon slots (stop + 3 + 7 k along the track).
local function train_at_stop(surface, vertical, fixed, stop_at, wagons, color)
  local dir = vertical and defines.direction.north or defines.direction.west
  local function pos(c) return vertical and { fixed, c } or { c, fixed } end
  local stop = surface.create_entity({ name = "train-stop", direction = dir, force = "player",
    position = vertical and { fixed + 2, stop_at } or { stop_at, fixed - 2 } })
  stop.color = color
  local loco = surface.create_entity({ name = "locomotive", force = "player", direction = dir, position = pos(stop_at + 3) })
  loco.color = color
  local list = {}
  for i = 1, wagons do
    local at = stop_at + 3 + 7 * i
    local w = surface.create_entity({ name = "bulk-wagon", force = "player", direction = dir, raise_built = true, position = pos(at) })
    if not (w and w.valid) then w = surface.find_entities_filtered({ type = "cargo-wagon", position = pos(at), radius = 3 })[1] end
    w.color = color
    list[i] = w
  end
  loco.train.manual_mode = true
  return list, function(i) return stop_at + 3 + 7 * i end
end

local function station(surface, name, position)
  local e = surface.create_entity({ name = name, position = position, force = "player", raise_built = true })
  return remote.call("bulk-wagons", "align_station", e)
end

local function connector(surface, name, position, direction, kind)
  local c = surface.create_entity({ name = name, position = position, direction = direction, type = kind, force = "player",
    raise_built = true })
  if c then c.update_connections() end
  return c
end

local function belt_run(surface, name, start, step, n, direction)
  local belts = {}
  for i = 0, n - 1 do
    belts[#belts + 1] = surface.create_entity({ name = name, force = "player", direction = direction,
      position = { start[1] + step[1] * i, start[2] + step[2] * i } })
  end
  return belts
end

local function setup()
  local surface = game.surfaces.nauvis
  surface.request_to_generate_chunks({ 0, 0 }, 4)
  surface.force_generate_chunk_requests()
  surface.always_day = true
  local area = { { -80, -80 }, { 80, 80 } }
  for _, e in pairs(surface.find_entities_filtered({ area = area })) do
    if e.type ~= "character" then e.destroy() end
  end
  local tiles = {}
  for x = -80, 79 do
    for y = -80, 79 do tiles[#tiles + 1] = { name = "grass-1", position = { x, y } } end
  end
  surface.set_tiles(tiles)
  surface.destroy_decoratives({ area = area })
  local s = {}
  local red = { r = 0.56, g = 0.23, b = 0.15, a = 0.5 }

  -- north-south: a bunker unloading the first wagon, a silo loading the second
  rail_line(surface, true, 1, -61, 61)
  local wagons, slot = train_at_stop(surface, true, 1, -36, 3, red)
  wagons[1].get_inventory(defines.inventory.cargo_wagon).insert({ name = "iron-ore", count = 2000 })
  s.bunker = station(surface, "bulk-unloading-bunker", { 1, slot(1) })
  -- align_station moves the station onto the wagon, which can sit half a slot off
  local yb = s.bunker.position.y
  for _, y in pairs({ yb - 2.5, yb + 0.5 }) do
    connector(surface, "bulk-connector-bunker", { 4.5, y }, defines.direction.east, "output")
    belt_run(surface, "transport-belt", { 5.5, y }, { 1, 0 }, 8, defines.direction.east)
  end
  connector(surface, "bulk-fast-connector-bunker", { -2.5, yb - 0.5 }, defines.direction.west, "output")
  belt_run(surface, "fast-transport-belt", { -3.5, yb - 0.5 }, { -1, 0 }, 8, defines.direction.west)
  s.silo = station(surface, "bulk-loading-silo", { 1, slot(2) })
  remote.call("bulk-wagons", "get_inventory", s.silo).insert({ name = "coal", count = 2500 })
  local ys = s.silo.position.y
  -- silo connectors take the next rim tile clockwise too: south on the east side, north on the west
  connector(surface, "bulk-connector-bunker", { 3.5, ys - 1.5 }, defines.direction.west, "input")
  s.in_belts = belt_run(surface, "transport-belt", { 11.5, ys - 1.5 }, { -1, 0 }, 8, defines.direction.west)
  connector(surface, "bulk-express-connector-bunker", { -1.5, ys + 1.5 }, defines.direction.east, "input")
  s.in_belts2 = belt_run(surface, "express-transport-belt", { -10.5, ys + 1.5 }, { 1, 0 }, 9, defines.direction.east)

  -- east-west: the same in the other direction, station colours in the train's blue
  local blue = { r = 0.18, g = 0.43, b = 0.66, a = 0.5 }
  rail_line(surface, false, 27, -61, 61)
  local hw, hslot = train_at_stop(surface, false, 27, -40, 3, blue)
  hw[1].get_inventory(defines.inventory.cargo_wagon).insert({ name = "copper-ore", count = 1200 })
  local b2 = station(surface, "bulk-unloading-bunker", { hslot(1), 27 })
  local s2 = station(surface, "bulk-loading-silo", { hslot(3), 27 })
  remote.call("bulk-wagons", "get_inventory", s2).insert({ name = "stone", count = 2000 })
  for _, e in pairs({ b2, s2 }) do
    remote.call("bulk-wagons", "station_color", e, { r = 0.18, g = 0.43, b = 0.66 })
  end
  connector(surface, "bulk-connector-bunker", { b2.position.x - 0.5, 30.5 }, defines.direction.south, "output")
  belt_run(surface, "transport-belt", { b2.position.x - 0.5, 31.5 }, { 0, 1 }, 6, defines.direction.south)
  connector(surface, "bulk-connector-bunker", { s2.position.x + 0.5, 29.5 }, defines.direction.north, "input")
  s.in_belts3 = belt_run(surface, "transport-belt", { s2.position.x + 0.5, 36.5 }, { 0, -1 }, 7, defines.direction.north)
  storage.s = s
end

script.on_event(defines.events.on_tick, function(event)
  if not storage.s then
    setup()
    storage.start = game.tick
    return
  end
  local s = storage.s
  for _, belts in pairs({ s.in_belts, s.in_belts2, s.in_belts3 }) do
    for i = 1, 2 do
      local line = belts[1].get_transport_line(i)
      if line.can_insert_at_back() then line.insert_at_back({ name = "stone", count = 1 }) end
    end
  end
  local age = game.tick - storage.start
  local shots = {
    [150] = { "vertical", { 1, -21 }, 1 },
    [151] = { "horizontal", { -12, 27 }, 1 },
    [152] = { "bunker-close", { 1, -27 }, 2 },
    [153] = { "silo-close", { 1, -22 }, 2 },
  }
  local shot = shots[age]
  if shot then
    game.take_screenshot({
      surface = game.surfaces.nauvis,
      position = shot[2],
      resolution = { 1920, 1080 },
      zoom = shot[3],
      path = "bulk-shots/" .. shot[1] .. ".png",
      show_entity_info = false,
      daytime = 0,
      allow_in_replay = true,
      anti_alias = true,
    })
    log("BULKSHOT " .. shot[1])
  end
end)
