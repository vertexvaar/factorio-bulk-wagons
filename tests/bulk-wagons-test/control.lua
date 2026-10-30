-- Headless test scene, run via tests/run.py (factorio --benchmark).
-- Every check logs "BULKTEST PASS ..." or "BULKTEST FAIL ...".

local function report(ok, what, detail)
  log(string.format("BULKTEST %s %s%s", ok and "PASS" or "FAIL", what, detail and (" (" .. detail .. ")") or ""))
end

local v2 = require("v2")

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
  s.store_b = surface.find_entities_filtered({ name = "bulk-loading-station-store-1", position = { 21, -13 } })[1]
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

  -- Scene G: silo controlled by the circuit network. Enabled while A > 0 from a
  -- constant combinator, reads the docked wagon's contents and outputs W.
  rail_line(surface, true, -41, -41, 41)
  s.wagon_g = train(surface, true, -41, -20, -13)
  s.wagon_g.get_inventory(defines.inventory.cargo_wagon).insert({ name = "stone", count = 7 })
  s.silo_g = surface.create_entity({ name = "bulk-loading-station", position = { -41, -13 }, force = "player", raise_built = true })
  remote.call("bulk-wagons", "get_inventory", s.silo_g).insert({ name = "coal", count = 100 })
  remote.call("bulk-wagons", "circuit_settings", s.silo_g, {
    enable = true, signal = { type = "virtual", name = "signal-A" }, comparator = ">", constant = 0,
    read_wagon = true, docked_signal = true,
  })
  s.store_g = remote.call("bulk-wagons", "get_store", s.silo_g)
  s.cc_g = surface.create_entity({ name = "constant-combinator", position = { -36.5, -10.5 }, force = "player" })
  s.cc_g.get_wire_connector(defines.wire_connector_id.circuit_red, true)
    .connect_to(s.store_g.get_wire_connector(defines.wire_connector_id.circuit_red, true))

  -- Scene H: a silo built from a blueprint ghost keeps its settings and wire.
  s.cc_h = surface.create_entity({ name = "constant-combinator", position = { -52.5, -30.5 }, force = "player" })
  local ghost = surface.create_entity({
    name = "entity-ghost", inner_name = "bulk-loading-station", position = { -57, -33 }, force = "player",
    tags = { bulk_wagons = {
      enable = true, signal = { type = "virtual", name = "signal-B" }, comparator = "≥", constant = 5, read_wagon = true,
      wires = { { id = defines.wire_connector_id.circuit_green, target_id = defines.wire_connector_id.circuit_green,
        name = "constant-combinator", dx = 4.5, dy = 2.5 } },
    } },
  })
  local _, revived = ghost.revive({ raise_revive = true })
  s.silo_h = revived
  if s.silo_h then
    local settings = remote.call("bulk-wagons", "circuit_settings", s.silo_h)
    report(settings and settings.enable and settings.constant == 5 and settings.comparator == "≥" and settings.read_wagon,
      "blueprint tags restore circuit settings")
    local store = remote.call("bulk-wagons", "get_store", s.silo_h)
    local connections = store and store.get_wire_connector(defines.wire_connector_id.circuit_green, true).connections or {}
    local wired = false
    for _, c in pairs(connections) do
      if c.target.owner == s.cc_h then wired = true end
    end
    report(wired, "blueprint tags restore circuit wires", #connections .. " green connections")
  else
    report(false, "blueprint ghost revives")
  end

  -- Scene E: a station dropped crosswise and off-centre next to the horizontal track
  -- turns and centres itself, as it does when a player builds it.
  local skewed = surface.create_entity({ name = "bulk-loading-station", position = { 7, 30 }, force = "player" })
  s.aligned = remote.call("bulk-wagons", "align_station", skewed)
  report(s.aligned and s.aligned.valid and s.aligned.name == "bulk-loading-station-2"
    and s.aligned.position.x == 7 and s.aligned.position.y == 31, "station turns and centres on rail",
    s.aligned and s.aligned.valid and (s.aligned.name .. " at " .. s.aligned.position.x .. "," .. s.aligned.position.y) or "gone")
  local ports = surface.find_entities_filtered({ name = "bulk-station-port", area = { { 4, 28 }, { 10, 36 } } })
  report(#ports == 1 and ports[1].loader_container ~= nil and ports[1].loader_container.name == "bulk-loading-station-store-2", "aligned station has its port", #ports .. " ports")

  -- Scene F: placement. Stations go across the track, three in a row, but not onto buildings.
  local row = {}
  for i, x in ipairs({ 25, 27, 29 }) do
    local spec = { name = "bulk-unloading-pit-2", position = { x, 31 }, force = "player", raise_built = true }
    row[i] = surface.can_place_entity(spec) and surface.create_entity(spec)
  end
  report(row[1] and row[2] and row[3] and true, "three stations fit side by side on the rail")
  surface.create_entity({ name = "assembling-machine-1", position = { 36.5, 28.5 }, force = "player" })
  report(not surface.can_place_entity({ name = "bulk-loading-station-2", position = { 37, 31 }, force = "player" }),
    "station collides with buildings")
  report(not surface.can_place_entity({ name = "bulk-loading-station-2", position = { 27, 31 }, force = "player" }),
    "stations do not overlap")
  local colored = remote.call("bulk-wagons", "station_color", row[1], { r = 1, g = 0, b = 0 })
  report(colored and colored.r == 1 and colored.a == 0.5, "station colour is stored at alpha 0.5")

  -- Scene I: three silos side by side load one wagon together, and three belt
  -- loaders, each fed its own ore, load another.
  rail_line(surface, true, 61, -41, 41)
  s.wagon_i = train(surface, true, 61, -20, -13)
  s.silos_i = {}
  for i, y in ipairs({ -15, -13, -11 }) do
    local silo = surface.create_entity({ name = "bulk-loading-station", position = { 61, y }, force = "player", raise_built = true })
    s.silos_i[i] = silo
    if silo then remote.call("bulk-wagons", "get_inventory", silo).insert({ name = "coal", count = 300 }) end
  end
  rail_line(surface, true, 71, -41, 41)
  s.wagon_j = train(surface, true, 71, -20, -13)
  s.j_feeds = {}
  for i, y in ipairs({ -15, -13, -11 }) do
    surface.create_entity({ name = "bulk-belt-loader", position = { 71, y }, force = "player", raise_built = true })
    s.j_feeds[i] = { belts = belt_run(surface, { 80.5, y - 0.5 }, { -1, 0 }, 7, defines.direction.west),
      item = ({ "iron-ore", "copper-ore", "stone" })[i] }
  end

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
  local runs = { { s.in_belts, "copper-ore" }, { s.f_belts, "copper-ore" } }
  for _, f in pairs(s.j_feeds) do
    runs[#runs + 1] = { f.belts, f.item }
  end
  for _, run in pairs(runs) do
    for i = 1, 2 do
      local line = run[1][1].get_transport_line(i)
      if line.can_insert_at_back() then line.insert_at_back({ name = run[2], count = 1 }) end
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
  report(s.wagon_g.get_inventory(defines.inventory.cargo_wagon).get_item_count("coal") == 100,
    "enabled station loads", s.wagon_g.get_inventory(defines.inventory.cargo_wagon).get_item_count("coal") .. " coal")
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

  local wagon_i = s.wagon_i.get_inventory(defines.inventory.cargo_wagon)
  local emptied = 0
  for _, silo in pairs(s.silos_i) do
    if silo.valid and remote.call("bulk-wagons", "get_inventory", silo).is_empty() then emptied = emptied + 1 end
  end
  report(emptied == 3 and count(wagon_i, "coal") == 900, "three silos load one wagon together",
    emptied .. " silos empty, " .. count(wagon_i, "coal") .. " coal")
  local wagon_j = s.wagon_j.get_inventory(defines.inventory.cargo_wagon)
  local got = {}
  for _, f in pairs(s.j_feeds) do
    got[#got + 1] = f.item .. "=" .. count(wagon_j, f.item)
  end
  report(count(wagon_j, "iron-ore") > 0 and count(wagon_j, "copper-ore") > 0 and count(wagon_j, "stone") > 0,
    "three belt loaders load one wagon together", table.concat(got, " "))

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
  -- a wagon over a working pit shows its heaps draining through the open flaps
  if not storage.saw_drain and age < 400 then
    for _, object in pairs(rendering.get_all_objects("bulk-wagons")) do
      if object.type == "animation" and object.animation:find("^bulk%-wagon%-drain%-") then storage.saw_drain = true end
    end
  end
  if age == 40 then check_moving() end
  if age == 60 then
    local red = defines.wire_connector_id.circuit_red
    local store = storage.scene.store_g
    report(store.get_signal({ type = "item", name = "stone" }, red) == 7, "circuit reads docked wagon contents",
      tostring(store.get_signal({ type = "item", name = "stone" }, red)))
    report(store.get_signal({ type = "virtual", name = "signal-W" }, red) == 1, "circuit outputs wagon docked signal")
  end
  if age == 200 then
    local s = storage.scene
    report(remote.call("bulk-wagons", "get_inventory", s.silo_g).get_item_count("coal") == 100,
      "disabled station does not load")
    local section = s.cc_g.get_or_create_control_behavior().get_section(1)
    section.set_slot(1, { value = { type = "virtual", name = "signal-A", quality = "normal", comparator = "=" }, min = 1 })
  end
  if age == 2 then
    storage.v2 = {}
    v2.setup(storage.v2, report)
  end
  if age == 3 then v2.after_setup(storage.v2) end
  if age == 300 then v2.fill_fulgora(storage.v2) end
  if age == 1 then
    -- stations side by side along the track, as a player places them
    local surface = game.surfaces.nauvis
    -- outside the cleared scene: trees and rocks of the random map would get in the way
    for _, e in pairs(surface.find_entities_filtered({ area = { { 67.5, -10 }, { 94.5, 10 } } })) do
      if e.type == "tree" or e.type == "simple-entity" or e.type == "cliff" then e.destroy() end
    end
    local tiles = {}
    for x = 66, 96 do
      for y = -12, 11 do tiles[#tiles + 1] = { name = "lab-dark-1", position = { x, y } } end
    end
    surface.set_tiles(tiles)
    for i, base in pairs({ "bulk-belt-loader", "bulk-loading-station", "bulk-unloading-pit" }) do
      local x = 61 + 10 * i
      for y = -9, 9, 2 do
        surface.create_entity({ name = "straight-rail", position = { x, y }, direction = defines.direction.north, force = "player" })
      end
      surface.create_entity({ name = base, position = { x, 0 }, force = "player", raise_built = true })
      local function fits(dy)
        return surface.can_place_entity({ name = base, position = { x, dy }, force = "player",
          build_check_type = defines.build_check_type.manual })
      end
      report(fits(2) and fits(-2) and fits(3) and not fits(1), base .. " fits right next to another on the 1-tile grid")
    end
  end
  if age == 600 then
    check()
    v2.check(storage.v2)
    report(storage.saw_drain == true, "unloading wagon shows draining heaps")
    report(helpers.is_valid_sprite_path("utility/rail_signal_placement_indicator"), "placement indicator sprite exists")
    log("BULKTEST DONE")
  end
end)
