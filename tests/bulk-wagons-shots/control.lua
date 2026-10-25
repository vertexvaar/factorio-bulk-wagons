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

local function train(surface, vertical, fixed, at, wagons, color)
  local dir = vertical and defines.direction.north or defines.direction.east
  local function pos(c) return vertical and { fixed, c } or { c, fixed } end
  local loco = surface.create_entity({ name = "locomotive", force = "player", direction = dir, position = pos(at) })
  loco.color = color
  local list = {}
  for i = 1, wagons do
    local w = surface.create_entity({
      name = "bulk-wagon", force = "player", direction = dir, raise_built = true,
      position = pos(at + (vertical and 7 or -7) * i),
    })
    if not (w and w.valid) then
      w = surface.find_entities_filtered({ type = "cargo-wagon", position = pos(at + (vertical and 7 or -7) * i), radius = 3 })[1]
    end
    w.color = color
    log("BULKSHOT wagon color " .. serpent.line(w.color))
    list[#list + 1] = w
  end
  loco.train.manual_mode = true
  return list
end

local function station(surface, name, position)
  return surface.create_entity({ name = name, position = position, force = "player", raise_built = true })
end

local function belt_run(surface, start, step, n, direction)
  local belts = {}
  for i = 0, n - 1 do
    belts[#belts + 1] = surface.create_entity({
      name = "transport-belt", force = "player", direction = direction,
      position = { start[1] + step[1] * i, start[2] + step[2] * i },
    })
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

  -- vertical line: wagon over a pit (unloading), one over the silo, one over the belt loader
  rail_line(surface, true, 1, -61, 61)
  local wagons = train(surface, true, 1, -30, 3, { r = 0.56, g = 0.23, b = 0.15, a = 0.5 })
  -- wagon i is centred at -30 + 7 i; its compartments are at centre -1.3, 0, +1.3
  local y1, y2, y3 = -23, -16, -9
  local s = {}
  s.pit = station(surface, "bulk-unloading-pit", { 1, y1 + 1 })
  s.silo = station(surface, "bulk-loading-station", { 1, y2 - 1 })
  s.belt = station(surface, "bulk-belt-loader", { 1, y3 + 1 })
  wagons[1].get_inventory(defines.inventory.cargo_wagon).insert({ name = "iron-ore", count = 2000 })
  remote.call("bulk-wagons", "get_inventory", s.silo).insert({ name = "coal", count = 2000 })
  s.out_belts = belt_run(surface, { 4.5, y1 + 0.5 }, { 1, 0 }, 6, defines.direction.east)
  s.in_belts = belt_run(surface, { 10.5, y3 + 0.5 }, { -1, 0 }, 7, defines.direction.west)

  -- horizontal line with all three stations rotated, an empty train standing still
  rail_line(surface, false, 21, -61, 61)
  local hw = train(surface, false, 21, 20, 2, { r = 0.18, g = 0.43, b = 0.66, a = 0.5 })
  -- station colours: pit and silo in the train's blue, the belt loader yellow, the last silo keeps the default
  local colored = {
    { station(surface, "bulk-unloading-pit-2", { 13, 21 }), { r = 0.18, g = 0.43, b = 0.66 } },
    { station(surface, "bulk-loading-station-2", { 5, 21 }), { r = 0.18, g = 0.43, b = 0.66 } },
    { station(surface, "bulk-belt-loader-4", { -9, 21 }), { r = 0.95, g = 0.75, b = 0.1 } },
    { station(surface, "bulk-loading-station-2", { -21, 21 }), nil },
  }
  for _, entry in pairs(colored) do
    if entry[2] then remote.call("bulk-wagons", "station_color", entry[1], entry[2]) end
  end
  -- side by side with vanilla: locomotive, cargo wagon, bulk wagon, locomotive
  rail_line(surface, true, 31, -61, 61)
  local cmp = {}
  for i, name in ipairs({ "locomotive", "cargo-wagon", "bulk-wagon", "locomotive" }) do
    cmp[i] = surface.create_entity({
      name = name, force = "player", position = { 31, -21 + 7 * i },
      direction = i == 4 and defines.direction.south or defines.direction.north, raise_built = true,
    })
  end
  cmp[3].get_inventory(defines.inventory.cargo_wagon).insert({ name = "iron-ore", count = 400 }) -- a quarter full
  -- a loaded wagon on east-west track, for the heap's fit in that direction
  rail_line(surface, false, -28, 35, 61)
  local loaded = train(surface, false, -28, 46, 1, { r = 0.56, g = 0.23, b = 0.15, a = 0.5 })
  loaded[1].get_inventory(defines.inventory.cargo_wagon).insert({ name = "iron-ore", count = 2000 })
  -- pits in a row on both track directions, for the seams between them and the track ends
  rail_line(surface, true, -51, -15, 15)
  for _, y in pairs({ -2, 0, 2 }) do
    station(surface, "bulk-unloading-pit", { -51, y })
  end
  rail_line(surface, false, 7, -45, -27)
  for _, x in pairs({ -39, -37, -35 }) do
    station(surface, "bulk-unloading-pit-2", { x, 7 })
  end
  storage.s = s
  storage.hw = hw
end

script.on_event(defines.events.on_tick, function(event)
  if not storage.s then
    setup()
    storage.start = game.tick
    return
  end
  local s = storage.s
  for i = 1, 2 do
    local line = s.in_belts[1].get_transport_line(i)
    if line.can_insert_at_back() then line.insert_at_back({ name = "stone", count = 1 }) end
  end
  local age = game.tick - storage.start
  local shots = {
    [150] = { "vertical", { 3, -16 } },
    [151] = { "horizontal", { 0, 19 } },
    [152] = { "pit-close", { 3, -22 } },
    [153] = { "train-compare", { 31, -3 } },
    [154] = { "pit-row", { -51, 0 } },
    [155] = { "pit-row-h", { -37, 7 } },
  }
  local shot = shots[age]
  if shot then
    game.take_screenshot({
      surface = game.surfaces.nauvis,
      position = shot[2],
      resolution = shot[1] == "train-compare" and { 1080, 1920 } or { 1920, 1080 },
      zoom = (shot[1] == "pit-close" or shot[1]:find("pit-row")) and 2 or 1,
      path = "bulk-shots/" .. shot[1] .. ".png",
      show_entity_info = false,
      daytime = 0,
      allow_in_replay = true,
      anti_alias = true,
    })
    log("BULKSHOT " .. shot[1])
  end
end)
