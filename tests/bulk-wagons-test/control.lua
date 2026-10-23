-- Headless test scene, run via tests/run.py (factorio --benchmark).
-- Every check logs "BULKTEST PASS ..." or "BULKTEST FAIL ...".

local function report(ok, what, detail)
  log(string.format("BULKTEST %s %s%s", ok and "PASS" or "FAIL", what, detail and (" (" .. detail .. ")") or ""))
end

local function count(inventory, name)
  return inventory.get_item_count(name)
end

local function line_count(belts, name)
  local n = 0
  for _, belt in pairs(belts) do
    for i = 1, 2 do
      n = n + belt.get_transport_line(i).get_item_count(name)
    end
  end
  return n
end

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

local function train(surface, vertical, fixed, loco_at, wagon_at)
  local dir = vertical and defines.direction.north or defines.direction.east
  local loco = surface.create_entity({
    name = "locomotive", force = "player", direction = dir,
    position = vertical and { fixed, loco_at } or { loco_at, fixed },
  })
  local wagon = surface.create_entity({
    name = "bulk-wagon", force = "player", direction = dir, raise_built = true,
    position = vertical and { fixed, wagon_at } or { wagon_at, fixed },
  })
  if not (wagon and wagon.valid) then
    -- the mod swapped it for the planet variant
    local at = vertical and { fixed, wagon_at } or { wagon_at, fixed }
    wagon = surface.find_entities_filtered({ type = "cargo-wagon", position = at, radius = 3 })[1]
    log("BULKDEBUG swapped wagon found: " .. tostring(wagon and wagon.name))
  end
  loco.train.manual_mode = true
  return wagon
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

local function prepare(surface)
  local area = { { -64, -64 }, { 64, 64 } }
  for _, e in pairs(surface.find_entities_filtered({ area = area })) do
    if e.type ~= "character" then e.destroy() end
  end
  local tiles = {}
  for x = -64, 63 do
    for y = -64, 63 do tiles[#tiles + 1] = { name = "lab-dark-1", position = { x, y } } end
  end
  surface.set_tiles(tiles)
end

local function setup_vulcanus(s)
  local surface = game.planets.vulcanus.create_surface()
  surface.request_to_generate_chunks({ 0, 0 }, 3)
  surface.force_generate_chunk_requests()
  prepare(surface)
  rail_line(surface, true, 1, -41, 41)
  s.wagon_v = train(surface, true, 1, -20, -13)
  s.pit_v = surface.create_entity({ name = "bulk-unloading-pit", position = { 1, -13 }, force = "player", raise_built = true })
  if not (s.pit_v and s.pit_v.valid) then
    s.pit_v = surface.find_entities_filtered({ type = "simple-entity-with-owner", position = { 1, -13 } })[1]
  end
  report(s.wagon_v.name == "bulk-wagon-vulcanus", "wagon becomes Vulcanus variant", s.wagon_v.name)
  report(s.pit_v.name == "bulk-unloading-pit-vulcanus", "pit becomes Vulcanus variant", s.pit_v.name)
  report(#s.wagon_v.train.carriages == 2, "swapped wagon stays coupled", #s.wagon_v.train.carriages .. " carriages")
  s.wagon_v.get_inventory(defines.inventory.cargo_wagon).insert({ name = "tungsten-ore", count = 50 })
end

local function setup()
  local surface = game.surfaces.nauvis
  surface.request_to_generate_chunks({ 0, 0 }, 3)
  surface.force_generate_chunk_requests()
  local area = { { -64, -64 }, { 64, 64 } }
  for _, e in pairs(surface.find_entities_filtered({ area = area })) do
    if e.type ~= "character" then e.destroy() end
  end
  local tiles = {}
  for x = -64, 63 do
    for y = -64, 63 do tiles[#tiles + 1] = { name = "lab-dark-1", position = { x, y } } end
  end
  surface.set_tiles(tiles)

  local s = {}
  -- Scene A: vertical track x=1, unloading pit under the wagon, belt out east.
  rail_line(surface, true, 1, -41, 41)
  s.wagon_a = train(surface, true, 1, -20, -13)
  s.pit = surface.create_entity({ name = "bulk-unloading-pit", position = { 1, -13 }, force = "player", raise_built = true })
  local wagon_inv = s.wagon_a.get_inventory(defines.inventory.cargo_wagon)
  wagon_inv.insert({ name = "iron-ore", count = 500 })
  wagon_inv.insert({ name = "iron-plate", count = 10 })
  s.out_belts = belt_run(surface, { 4.5, -13.5 }, { 1, 0 }, 12, defines.direction.east)

  -- Scene B: vertical track x=21, loading station, belt feeding in from the east.
  rail_line(surface, true, 21, -41, 41)
  s.wagon_b = train(surface, true, 21, -20, -13)
  s.loader = surface.create_entity({ name = "bulk-loading-station", position = { 21, -13 }, force = "player", raise_built = true })
  local station_inv = remote.call("bulk-wagons", "get_inventory", s.loader)
  station_inv.insert({ name = "coal", count = 200 })
  station_inv.insert({ name = "iron-plate", count = 5 })
  s.in_belts = belt_run(surface, { 30.5, -13.5 }, { -1, 0 }, 7, defines.direction.west)
  -- circuit wire from the station's inventory to a constant combinator
  s.store_b = surface.find_entities_filtered({ name = "bulk-loading-station-store-v", position = { 21, -13 } })[1]
  s.combinator = surface.create_entity({ name = "constant-combinator", position = { 25.5, -10.5 }, force = "player" })
  local connected = s.store_b and s.store_b.get_wire_connector(defines.wire_connector_id.circuit_red, true)
    .connect_to(s.combinator.get_wire_connector(defines.wire_connector_id.circuit_red, true))
  report(connected == true, "circuit wire connects to station inventory")

  -- Scene C: horizontal track y=31, pit variant 2 (port south).
  rail_line(surface, false, 31, -41, 41)
  s.wagon_c = train(surface, false, 31, -20, -13)
  s.pit_c = surface.create_entity({ name = "bulk-unloading-pit-2", position = { -13, 31 }, force = "player", raise_built = true })
  s.wagon_c.get_inventory(defines.inventory.cargo_wagon).insert({ name = "stone", count = 100 })

  -- Scene D: moving train must not be unloaded.
  rail_line(surface, true, -21, -41, 41)
  s.wagon_d = train(surface, true, -21, -20, -13)
  s.pit_d = surface.create_entity({ name = "bulk-unloading-pit", position = { -21, -13 }, force = "player", raise_built = true })
  s.wagon_d.get_inventory(defines.inventory.cargo_wagon).insert({ name = "copper-ore", count = 100 })
  s.wagon_d.train.speed = 0.05

  -- Scene F: vertical track x=41, belt loader without inventory, belt feeding in from the east.
  rail_line(surface, true, 41, -41, 41)
  s.wagon_f = train(surface, true, 41, -20, -13)
  s.belt_loader = surface.create_entity({ name = "bulk-belt-loader", position = { 41, -13 }, force = "player", raise_built = true })
  s.f_belts = belt_run(surface, { 50.5, -13.5 }, { -1, 0 }, 7, defines.direction.west)

  -- Scene E: a station dropped crosswise and off-centre next to the horizontal track
  -- turns and centres itself, as it does when a player builds it.
  local skewed = surface.create_entity({ name = "bulk-loading-station", position = { 7, 30 }, force = "player" })
  s.aligned = remote.call("bulk-wagons", "align_station", skewed)
  report(s.aligned and s.aligned.valid and s.aligned.name == "bulk-loading-station-2"
    and s.aligned.position.x == 7 and s.aligned.position.y == 31, "station turns and centres on rail",
    s.aligned and s.aligned.valid and (s.aligned.name .. " at " .. s.aligned.position.x .. "," .. s.aligned.position.y) or "gone")
  local ports = surface.find_entities_filtered({ name = "bulk-station-port", area = { { 4, 28 }, { 10, 36 } } })
  report(#ports == 1 and ports[1].loader_container ~= nil and ports[1].loader_container.name == "bulk-loading-station-store-h", "aligned station has its port", #ports .. " ports")

  if game.planets.vulcanus then setup_vulcanus(s) end

  storage.scene = s
  storage.start = game.tick
  report(s.pit and s.pit.valid, "pit built across rail")
  report(s.loader and s.loader.valid, "loader built across rail")
  report(s.pit_c and s.pit_c.valid, "pit variant 2 built across horizontal rail")
  report(s.wagon_a and s.wagon_a.valid and s.wagon_a.train.locomotives.front_movers[1] ~= nil, "train A assembled")
end

local function feed()
  local s = storage.scene
  for _, belts in pairs({ s.in_belts, s.f_belts }) do
    for i = 1, 2 do
      local line = belts[1].get_transport_line(i)
      if line.can_insert_at_back() then line.insert_at_back({ name = "copper-ore", count = 1 }) end
    end
  end
end

local function describe()
  local s = storage.scene
  for _, key in pairs({ "wagon_a", "pit", "wagon_b", "loader", "wagon_c", "pit_c" }) do
    local e = s[key]
    log(string.format("BULKDEBUG %s %s pos=%s,%s orient=%s speed=%s", key, e.name, e.position.x, e.position.y,
      e.orientation or "-", e.train and e.train.speed or "-"))
  end
  for _, port in pairs(game.surfaces.nauvis.find_entities_filtered({ name = "bulk-station-port" })) do
    log(string.format("BULKDEBUG port pos=%s,%s dir=%s type=%s container=%s", port.position.x, port.position.y,
      port.direction, port.loader_type, port.loader_container and port.loader_container.name or "nil"))
  end
end

local function check()
  describe()
  local s = storage.scene
  local wagon_a = s.wagon_a.get_inventory(defines.inventory.cargo_wagon)
  local pit = remote.call("bulk-wagons", "get_inventory", s.pit)
  report(count(wagon_a, "iron-plate") == 0, "forbidden item removed from wagon", count(wagon_a, "iron-plate") .. " left")
  report(count(wagon_a, "iron-ore") == 0, "wagon A emptied into pit", count(wagon_a, "iron-ore") .. " left")
  local on_belt = line_count(s.out_belts, "iron-ore")
  report(on_belt > 0, "pit port puts ore on the belt", on_belt .. " on belt")
  report(count(pit, "iron-ore") + on_belt <= 500, "no items duplicated", (count(pit, "iron-ore") + on_belt) .. " total")

  local wagon_b = s.wagon_b.get_inventory(defines.inventory.cargo_wagon)
  local station = remote.call("bulk-wagons", "get_inventory", s.loader)
  report(count(wagon_b, "coal") == 200, "loading station filled wagon", count(wagon_b, "coal") .. " coal")
  report(count(wagon_b, "copper-ore") > 0, "belt feeds wagon through loading port", count(wagon_b, "copper-ore") .. " copper")
  report(count(wagon_b, "iron-plate") == 0 and count(station, "iron-plate") == 5, "loading station keeps forbidden items")
  local read = s.store_b.get_signal({ type = "item", name = "iron-plate" }, defines.wire_connector_id.circuit_red)
  report(read == 5, "circuit network reads station contents", tostring(read))

  local wagon_f = s.wagon_f.get_inventory(defines.inventory.cargo_wagon)
  s.f_count = count(wagon_f, "copper-ore")
  report(s.f_count > 0, "belt loader feeds wagon directly", s.f_count .. " copper")
  report(remote.call("bulk-wagons", "get_inventory", s.belt_loader) == nil, "belt loader has no inventory")

  if s.wagon_v then
    local wagon_v = s.wagon_v.get_inventory(defines.inventory.cargo_wagon)
    report(count(wagon_v, "tungsten-ore") == 0, "Vulcanus pit unloads", count(wagon_v, "tungsten-ore") .. " left")
  end

  local wagon_c = s.wagon_c.get_inventory(defines.inventory.cargo_wagon)
  report(count(wagon_c, "stone") == 0, "horizontal pit unloads", count(wagon_c, "stone") .. " left")

end

local function check_moving()
  local s = storage.scene
  local wagon_d = s.wagon_d.get_inventory(defines.inventory.cargo_wagon)
  report(s.wagon_d.train.speed ~= 0 and count(wagon_d, "copper-ore") == 100, "moving wagon is not unloaded",
    count(wagon_d, "copper-ore") .. " left, speed " .. s.wagon_d.train.speed)
end

script.on_event(defines.events.on_tick, function(event)
  if not storage.scene then
    setup()
    return
  end
  local age = game.tick - storage.start
  if age < 400 then feed() end
  if age == 40 then check_moving() end
  if age == 600 then
    check()
    log("BULKTEST DONE")
  end
end)
