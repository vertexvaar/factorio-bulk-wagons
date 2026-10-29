-- Tests for the 0.4.0 stations: unloading bunker, loading silo, connectors, wagon
-- slots at train stops and the migration of the legacy stations; since 0.5.0 the 1x1
-- connectors on the station rims and the move of the 2x1 ones.
local v2 = {}

local report

local X0 = 110 -- the scene lives east of the main test scene

local function rails(surface, x, from, to)
  for y = from, to, 2 do
    surface.create_entity({ name = "straight-rail", position = { x, y }, direction = defines.direction.north, force = "player" })
  end
end

-- A train stop for northbound trains on the track at x; its wagon slots are at y + 3 + 7k.
local function stop(surface, x, y, name)
  local s = surface.create_entity({ name = "train-stop", position = { x + 2, y }, direction = defines.direction.north, force = "player" })
  s.backer_name = name
  return s
end

local function halted_train(surface, x, stop_y)
  local loco = surface.create_entity({ name = "locomotive", position = { x, stop_y + 3 }, direction = defines.direction.north, force = "player" })
  local wagon = surface.create_entity({ name = "bulk-wagon", position = { x, stop_y + 10 }, direction = defines.direction.north,
    force = "player", raise_built = true })
  if not (wagon and wagon.valid) then
    wagon = surface.find_entities_filtered({ type = "cargo-wagon", position = { x, stop_y + 10 }, radius = 3 })[1]
  end
  loco.train.manual_mode = true
  return wagon
end

-- A connector built from the item (the bunker look); the script may swap it for the silo
-- look, so the one standing there afterwards is returned.
local function connector(surface, position, direction, kind)
  surface.create_entity({ name = "bulk-connector-bunker", position = position, direction = direction, type = kind,
    force = "player", raise_built = true })
  return surface.find_entities_filtered({ type = "loader-1x1", position = position, radius = 0.1 })[1]
end

-- Fulgora: scrap goes into a bunker and out through its connectors, on a vertical and on a
-- horizontal track (as in Sam's base, a train between two locomotives).
local function setup_fulgora(s)
  local surface = game.planets.fulgora.create_surface()
  surface.request_to_generate_chunks({ 0, 0 }, 3)
  surface.force_generate_chunk_requests()
  for _, e in pairs(surface.find_entities_filtered({ area = { { -64, -64 }, { 64, 64 } } })) do
    if e.type ~= "character" then e.destroy() end
  end
  local tiles = {}
  for x = -64, 63 do
    for y = -64, 63 do tiles[#tiles + 1] = { name = "lab-dark-1", position = { x, y } } end
  end
  surface.set_tiles(tiles)
  s.fulgora = {}
  local f = s.fulgora

  -- vertical track at x = 1, like the Nauvis bunker scene
  rails(surface, 1, -41, 41)
  stop(surface, 1, -21, "Scrap N")
  f.wagon_v = halted_train(surface, 1, -21)
  f.wagon_v.get_inventory(defines.inventory.cargo_wagon).insert({ name = "scrap", count = 500 })
  f.bunker_v = remote.call("bulk-wagons", "align_station",
    surface.create_entity({ name = "bulk-unloading-bunker", position = { 1, -11 }, force = "player" }))
  f.out_v = connector(surface, { 4.5, -10.5 }, defines.direction.east, "output")
  f.belts_v = {}
  for i = 0, 5 do
    f.belts_v[#f.belts_v + 1] = surface.create_entity({ name = "transport-belt", position = { 5.5 + i, -10.5 },
      direction = defines.direction.east, force = "player" })
  end

  -- horizontal track at y = 31, eastbound: locomotive, two wagons, locomotive backwards
  for x = -41, 41, 2 do
    surface.create_entity({ name = "straight-rail", position = { x, 31 }, direction = defines.direction.east, force = "player" })
  end
  local sx = 20
  local st = surface.create_entity({ name = "train-stop", position = { sx, 33 }, direction = defines.direction.east, force = "player" })
  st.backer_name = "Scrap E"
  local front = surface.create_entity({ name = "locomotive", position = { sx - 3, 31 }, direction = defines.direction.east, force = "player" })
  f.wagons_h = {}
  for k = 1, 2 do
    local at = { sx - 3 - 7 * k, 31 }
    local w = surface.create_entity({ name = "bulk-wagon", position = at, direction = defines.direction.east, force = "player",
      raise_built = true })
    if not (w and w.valid) then w = surface.find_entities_filtered({ type = "cargo-wagon", position = at, radius = 3 })[1] end
    w.get_inventory(defines.inventory.cargo_wagon).insert({ name = "scrap", count = 500 })
    f.wagons_h[k] = w
  end
  surface.create_entity({ name = "locomotive", position = { sx - 24, 31 }, direction = defines.direction.west, force = "player" })
  front.train.manual_mode = true
  f.train_h = #front.train.carriages
  f.bunkers_h, f.outs_h, f.belts_h = {}, {}, {}
  for k = 1, 2 do
    local x = sx - 3 - 7 * k
    f.bunkers_h[k] = remote.call("bulk-wagons", "align_station",
      surface.create_entity({ name = "bulk-unloading-bunker-2", position = { x, 31 }, force = "player" }))
    local out = connector(surface, { x + 0.5, 34.5 }, defines.direction.south, "output")
    f.outs_h[k] = out
    for i = 0, 5 do
      f.belts_h[#f.belts_h + 1] = surface.create_entity({ name = "transport-belt", position = { x + 0.5, 35.5 + i },
        direction = defines.direction.south, force = "player" })
    end
  end
end

function v2.setup(s, report_fn)
  report = report_fn
  local surface = game.surfaces.nauvis
  surface.request_to_generate_chunks({ X0 + 30, 0 }, 3)
  surface.force_generate_chunk_requests()
  local area = { { X0 - 10, -60 }, { X0 + 70, 60 } }
  for _, e in pairs(surface.find_entities_filtered({ area = area })) do
    if e.type ~= "character" then e.destroy() end
  end
  local tiles = {}
  for x = X0 - 10, X0 + 69 do
    for y = -60, 59 do tiles[#tiles + 1] = { name = "lab-dark-1", position = { x, y } } end
  end
  surface.set_tiles(tiles)

  -- bunker under a halted wagon: placed a bit off, it snaps onto the wagon slot
  local xb = X0 + 1
  rails(surface, xb, -41, 41)
  stop(surface, xb, -21, "Bunker")
  s.bunker_wagon = halted_train(surface, xb, -21)
  s.bunker_wagon.get_inventory(defines.inventory.cargo_wagon).insert({ name = "iron-ore", count = 500 })
  local bunker = surface.create_entity({ name = "bulk-unloading-bunker", position = { xb, -9 }, force = "player" })
  s.bunker = remote.call("bulk-wagons", "align_station", bunker)
  -- connectors on the rims of both long sides, outputting onto belts running away from it
  s.out_east = connector(surface, { xb + 3.5, -10.5 }, defines.direction.east, "output")
  s.out_west = connector(surface, { xb - 3.5, -10.5 }, defines.direction.west, "output")
  s.belt_east = {}
  for i = 0, 5 do
    s.belt_east[#s.belt_east + 1] = surface.create_entity({ name = "transport-belt", position = { xb + 4.5 + i, -10.5 },
      direction = defines.direction.east, force = "player" })
  end
  -- a connector off the rim: next to the bunker's end, it must not count as docked
  s.end_connector = connector(surface, { xb + 2.5, -15.5 }, defines.direction.north, "output")
  -- whichever way it is built, the arrow decides: away from the station = output; along
  -- the track the bunker's way (output)
  s.arrow_ok = true
  s.arrow_detail = {}
  local cases = {
    { defines.direction.west, "input", "output", defines.direction.west },
    { defines.direction.west, "output", "output", defines.direction.west },
    { defines.direction.east, "output", "input", defines.direction.east },
    { defines.direction.north, "input", "output", defines.direction.west },
  }
  for k, case in pairs(cases) do
    -- connectors on the west side take the rim tile north of them as well
    local c = connector(surface, { xb - 3.5, k < 4 and -12.5 or -8.5 }, case[1], case[2])
    local ok = c and c.loader_type == case[3] and c.direction == case[4]
      and remote.call("bulk-wagons", "connector_docked", c)
    s.arrow_ok = s.arrow_ok and ok
    s.arrow_detail[#s.arrow_detail + 1] = c and (c.direction .. c.loader_type .. tostring(c.loader_container and c.loader_container.name)) or "none"
    if c and k < 3 then c.destroy({ raise_destroy = true }) end
  end
  -- the west side now holds out_west and two more: a fourth is refused, the east side has room
  s.west_full = remote.call("bulk-wagons", "connector_allowed", surface, { x = xb - 3.5, y = -8.5 })
  s.east_free = remote.call("bulk-wagons", "connector_allowed", surface, { x = xb + 3.5, y = -12.5 })
  -- the bunker's elevator needs the next rim tile clockwise: the last one on the east side has none
  s.east_end = remote.call("bulk-wagons", "connector_allowed", surface, { x = xb + 3.5, y = -8.5 })
  s.grating = remote.call("bulk-wagons", "connector_allowed", surface, { x = xb + 2.5, y = -8.5 })

  -- silo over an empty halted wagon, filled by script
  local xs = X0 + 21
  rails(surface, xs, -41, 41)
  stop(surface, xs, -21, "Silo")
  s.silo_wagon = halted_train(surface, xs, -21)
  local silo = surface.create_entity({ name = "bulk-loading-silo", position = { xs, -11 }, force = "player" })
  s.silo = remote.call("bulk-wagons", "align_station", silo)
  remote.call("bulk-wagons", "get_inventory", s.silo).insert({ name = "coal", count = 600 })
  -- an input connector (arrow towards the silo) takes the silo's look
  s.in_west = connector(surface, { xs - 2.5, -10.5 }, defines.direction.east, "input")

  -- 0.4 connectors beside a bunker and a silo, moved onto the rims by the update
  local xc = X0 + 31
  rails(surface, xc, -41, 41)
  stop(surface, xc, -21, "Connectors")
  s.mig_bunker = remote.call("bulk-wagons", "align_station",
    surface.create_entity({ name = "bulk-unloading-bunker", position = { xc, -11 }, force = "player" }))
  s.mig_silo = remote.call("bulk-wagons", "align_station",
    surface.create_entity({ name = "bulk-loading-silo", position = { xc, -4 }, force = "player" }))
  -- where 0.4 docked them: 2 tiles long, right beside the old 6-tile-wide station
  s.old_out = surface.create_entity({ name = "bulk-connector", position = { xc + 4, -12.5 }, direction = defines.direction.east,
    type = "output", force = "player" })
  s.old_out.set_filter(1, { name = "iron-ore" })
  s.old_in = surface.create_entity({ name = "bulk-fast-connector", position = { xc - 4, -3.5 }, direction = defines.direction.east,
    type = "input", force = "player" })

  -- migration: three pits under a wagon slot, a lone loader at a wagon end
  local xm = X0 + 41
  rails(surface, xm, -41, 41)
  stop(surface, xm, -21, "Old")
  local function legacy(name, y)
    local e = surface.create_entity({ name = name, position = { xm, y }, force = "player", raise_built = true })
    return remote.call("bulk-wagons", "align_station", e)
  end
  s.old = { legacy("bulk-unloading-pit", -13), legacy("bulk-unloading-pit", -11), legacy("bulk-unloading-pit", -9) }
  -- all three pits full: the bunker must hold all of it
  s.old_total = 0
  for _, pit in pairs(s.old) do
    s.old_total = s.old_total + remote.call("bulk-wagons", "get_inventory", pit).insert({ name = "stone", count = 1000000 })
  end
  s.old_loader = legacy("bulk-loading-station", -2)

  if game.planets.fulgora then setup_fulgora(s) end
end

function v2.after_setup(s)
  -- a ghost placed by hand a bit off the wagon slot, turned the wrong way: robots must build it on the slot
  local surface = game.surfaces.nauvis
  local xg = X0 + 61
  rails(surface, xg, -41, 41)
  stop(surface, xg, -21, "Ghost")
  local ghost = surface.create_entity({ name = "entity-ghost", inner_name = "bulk-loading-silo-2", position = { xg, -9 }, force = "player" })
  s.ghost = remote.call("bulk-wagons", "snap_ghost", ghost)
  -- goods spilled around the silo, as the 0.4.0 update did, come back in
  local surface = game.surfaces.nauvis
  s.recovered_before = remote.call("bulk-wagons", "get_inventory", s.silo).get_item_count("coal")
  surface.spill_item_stack({ position = { s.silo.position.x + 6, s.silo.position.y }, stack = { name = "coal", count = 500 } })
  remote.call("bulk-wagons", "recover_spilled", { { s.silo.position.x - 5, -30 }, { s.silo.position.x + 5, 10 } })
  s.recovered = remote.call("bulk-wagons", "get_inventory", s.silo).get_item_count("coal") - s.recovered_before
  -- migrate on demand (a fresh game counts as migrated)
  remote.call("bulk-wagons", "migrate_legacy", { { X0 + 35, -60 }, { X0 + 60, 60 } })
  remote.call("bulk-wagons", "migrate_connectors")
end

function v2.check(s)
  local surface = game.surfaces.nauvis
  local g = s.ghost
  report(g and g.valid and g.ghost_name == "bulk-loading-silo" and g.position.x == X0 + 61 and g.position.y == -11,
    "a hand-placed ghost snaps onto the wagon slot and turns to the rail",
    g and g.valid and (g.ghost_name .. " " .. serpent.line(g.position)) or "gone")
  local xb = X0 + 1
  report(s.bunker and s.bunker.valid and s.bunker.position.y == -11 and s.bunker.position.x == xb,
    "bunker snaps onto the wagon slot of the train stop", s.bunker and s.bunker.valid and serpent.line(s.bunker.position) or "gone")
  local wagon_left = s.bunker_wagon.get_inventory(defines.inventory.cargo_wagon).get_item_count("iron-ore")
  report(wagon_left == 0, "bunker empties the wagon", wagon_left .. " left")
  local on_belt = 0
  for _, belt in pairs(s.belt_east) do
    for i = 1, 2 do on_belt = on_belt + belt.get_transport_line(i).get_item_count("iron-ore") end
  end
  report(on_belt > 0, "east connector puts ore on its belt", on_belt .. " on the belt")
  local held = 0
  for i = 1, 2 do held = held + s.out_west.get_transport_line(i).get_item_count("iron-ore") end
  report(held > 0 and #surface.find_entities_filtered({ type = "item-entity", area = { { xb - 8, -16 }, { xb + 12, -6 } } }) == 0,
    "connector without a belt holds the ore, nothing on the ground", held .. " held")
  report(s.out_east.loader_container ~= nil and s.out_east.loader_container == remote.call("bulk-wagons", "get_store", s.bunker),
    "connector docks onto the bunker inventory")
  report(s.arrow_ok, "the arrow sets input or output, along the track the station's way", table.concat(s.arrow_detail, " "))
  report(remote.call("bulk-wagons", "connector_docked", s.out_east) and not remote.call("bulk-wagons", "connector_docked", s.end_connector),
    "only the rim counts as docking point")
  report(s.west_full == "bulk-wagons.side-full" and s.east_free == true and s.grating == "bulk-wagons.needs-station",
    "at most three connectors per side, only on the rim", tostring(s.west_full) .. " " .. tostring(s.east_free) .. " " .. tostring(s.grating))
  report(s.east_end == "bulk-wagons.needs-room" and #surface.find_entities_filtered({ name = "bulk-connector-slot",
      position = { xb + 3.5, -9.5 }, radius = 0.1 }) == 1,
    "a bunker connector takes the next rim tile clockwise as well", tostring(s.east_end))
  -- collision: rim blocks the player, gratings and track do not
  local function walkable(x, y) return surface.can_place_entity({ name = "character", position = { x, y } }) end
  report(not walkable(xb + 3.5, -11) and not walkable(xb - 3.5, -9) and walkable(xb + 2.5, -11) and walkable(xb - 1.5, -12),
    "bunker rim blocks players, its gratings do not")
  report(surface.can_place_entity({ name = "bulk-connector-bunker", position = { xb + 3.5, -8.5 }, force = "player" }),
    "a connector fits onto the bunker rim")
  local tall = prototypes.entity["bulk-loading-silo"]
  report(tall ~= nil, "silo prototype exists")
  report(not surface.can_place_entity({ name = "stone-furnace", position = { xb + 1.5, -11 } }), "bunker blocks buildings")

  local xs = X0 + 21
  report(s.silo and s.silo.valid and s.silo.position.y == -11, "silo snaps onto the wagon slot")
  local coal = s.silo_wagon.get_inventory(defines.inventory.cargo_wagon).get_item_count("coal")
  report(coal > 0, "silo fills the wagon", coal .. " coal")
  report(not walkable(xs + 1.5, -11) and not walkable(xs - 2.5, -9), "silo blocks players beside the track")
  local in_west = surface.find_entities_filtered({ type = "loader-1x1", position = { xs - 2.5, -10.5 }, radius = 0.1 })[1]
  report(in_west and in_west.name == "bulk-connector-silo" and in_west.loader_type == "input"
    and in_west.loader_container == remote.call("bulk-wagons", "get_store", s.silo),
    "a connector on the silo takes the chute look and feeds the silo", in_west and in_west.name or "none")
  local slot = surface.find_entities_filtered({ name = "bulk-connector-slot", position = { xs - 2.5, -11.5 }, radius = 0.1 })[1]
  local function allowed(x, y) return tostring(remote.call("bulk-wagons", "connector_allowed", surface, { x = x, y = y })) end
  local checks = { allowed(xs - 2.5, -11.5), allowed(xs - 2.5, -13.5), allowed(xs - 2.5, -8.5), allowed(xs + 2.5, -8.5),
    allowed(xs + 2.5, -9.5) }
  report(slot ~= nil and checks[1] == "bulk-wagons.needs-room" and checks[2] == "bulk-wagons.needs-room"
    and checks[3] == "true" and checks[4] == "bulk-wagons.needs-room" and checks[5] == "true",
    "a silo connector takes the next rim tile clockwise as well", table.concat(checks, " "))

  local xc = X0 + 31
  local function loader_at(x, y) return surface.find_entities_filtered({ type = "loader-1x1", position = { x, y }, radius = 0.1 })[1] end
  local function belt_at(x, y) return surface.find_entities_filtered({ type = "transport-belt", position = { x, y }, radius = 0.1 })[1] end
  local out = loader_at(xc + 3.5, -12.5)
  report(not s.old_out.valid and out and out.name == "bulk-connector-bunker" and out.loader_type == "output"
    and out.direction == defines.direction.east and out.get_filter(1) and out.get_filter(1).name == "iron-ore"
    and belt_at(xc + 4.5, -12.5) ~= nil and remote.call("bulk-wagons", "connector_docked", out),
    "a 0.4 connector beside a bunker moves onto its rim, keeps its filter, a belt fills the gap",
    out and (out.name .. " " .. out.loader_type .. " " .. out.direction) or "none")
  local inp = loader_at(xc - 2.5, -3.5)
  local b1, b2 = belt_at(xc - 3.5, -3.5), belt_at(xc - 4.5, -3.5)
  report(not s.old_in.valid and inp and inp.name == "bulk-fast-connector-silo" and inp.loader_type == "input"
    and b1 and b2 and b1.name == "fast-transport-belt" and b1.direction == defines.direction.east
    and remote.call("bulk-wagons", "connector_docked", inp),
    "a 0.4 connector beside a silo moves onto its rim, two belts of its tier fill the gap",
    inp and (inp.name .. " " .. inp.loader_type) or "none")

  local xm = X0 + 41
  local bunkers = surface.find_entities_filtered({ name = "bulk-unloading-bunker", area = { { xm - 4, -15 }, { xm + 4, -7 } } })
  local pits = surface.find_entities_filtered({ name = "bulk-unloading-pit", area = { { xm - 4, -20 }, { xm + 4, 0 } } })
  report(#bunkers == 1 and #pits == 0 and bunkers[1].position.y == -11, "three pits become one bunker on their wagon slot",
    #bunkers .. " bunkers, " .. #pits .. " pits")
  local stone = bunkers[1] and remote.call("bulk-wagons", "get_inventory", bunkers[1]).get_item_count("stone") or 0
  report(stone == s.old_total, "the goods of three full pits fit into the bunker", stone .. " of " .. s.old_total .. " stone")
  local loose = surface.find_entities_filtered({ type = "item-entity", area = { { xm - 20, -30 }, { xm + 20, 10 } } })
  report(#loose == 0, "nothing spilled on update", #loose .. " stacks on the ground")
  report(s.recovered == 500, "spilled goods around a silo are taken back in", s.recovered .. " coal recovered")
  local silos = surface.find_entities_filtered({ name = "bulk-loading-silo", area = { { xm - 4, -8 }, { xm + 4, 4 } } })
  report(#silos == 1 and silos[1].position.y == -4, "a loader at a wagon end becomes a silo on that wagon's slot",
    #silos == 1 and serpent.line(silos[1].position) or (#silos .. " silos"))
  local f = s.fulgora
  if f then
    local function on(belts, name)
      local n = 0
      for _, belt in pairs(belts) do
        for i = 1, 2 do n = n + belt.get_transport_line(i).get_item_count(name) end
      end
      return n
    end
    local function describe(bunker, out, wagon)
      local store = bunker and bunker.valid and remote.call("bulk-wagons", "get_store", bunker)
      return string.format("bunker=%s store=%s stored=%s docked=%s wagon=%s left=%s",
        bunker and bunker.valid and bunker.name or "none", store and store.name or "none",
        store and store.get_inventory(defines.inventory.chest).get_item_count("scrap") or "-",
        tostring(out and out.valid and remote.call("bulk-wagons", "connector_docked", out)),
        wagon.valid and wagon.name or "gone", wagon.valid and wagon.get_inventory(defines.inventory.cargo_wagon).get_item_count("scrap") or "-")
    end
    report(remote.call("bulk-wagons", "is_allowed", "scrap"), "scrap counts as bulk goods")
    local left = f.wagon_v.get_inventory(defines.inventory.cargo_wagon).get_item_count("scrap")
    local out = on(f.belts_v, "scrap")
    report(left == 0 and out > 0, "Fulgora bunker unloads scrap onto the belt", describe(f.bunker_v, f.out_v, f.wagon_v) .. " belt=" .. out)
    local details, ok = {}, f.train_h == 4
    for k = 1, 2 do
      local wagon = f.wagons_h[k]
      ok = ok and wagon.get_inventory(defines.inventory.cargo_wagon).get_item_count("scrap") == 0
      details[#details + 1] = describe(f.bunkers_h[k], f.outs_h[k], wagon)
    end
    local out_h = on(f.belts_h, "scrap")
    report(ok and out_h > 0, "two Fulgora bunkers on a horizontal track unload scrap",
      "carriages=" .. f.train_h .. " " .. table.concat(details, " | ") .. " belts=" .. out_h)
  end
end

return v2
