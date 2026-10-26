-- Tests for the 0.4.0 stations: unloading bunker, loading silo, connectors, wagon
-- slots at train stops and the migration of the legacy stations.
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

local function connector(surface, position, direction, kind)
  local c = surface.create_entity({ name = "bulk-connector", position = position, direction = direction, type = kind,
    force = "player", raise_built = true })
  if c then c.update_connections() end
  return c
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
  -- connectors on both long sides, outputting onto belts running away from it
  s.out_east = connector(surface, { xb + 4, -10.5 }, defines.direction.east, "output")
  s.out_west = connector(surface, { xb - 4, -10.5 }, defines.direction.west, "output")
  s.belt_east = {}
  for i = 0, 5 do
    s.belt_east[#s.belt_east + 1] = surface.create_entity({ name = "transport-belt", position = { xb + 5.5 + i, -10.5 },
      direction = defines.direction.east, force = "player" })
  end
  -- a connector off the long sides: next to the bunker's end, it must not count as docked
  s.end_connector = connector(surface, { xb + 2.5, -15 }, defines.direction.north, "output")

  -- silo over an empty halted wagon, filled by script
  local xs = X0 + 21
  rails(surface, xs, -41, 41)
  stop(surface, xs, -21, "Silo")
  s.silo_wagon = halted_train(surface, xs, -21)
  local silo = surface.create_entity({ name = "bulk-loading-silo", position = { xs, -11 }, force = "player" })
  s.silo = remote.call("bulk-wagons", "align_station", silo)
  remote.call("bulk-wagons", "get_inventory", s.silo).insert({ name = "coal", count = 600 })
  -- an input connector with a belt feeding it
  s.in_west = connector(surface, { xs - 4, -10.5 }, defines.direction.east, "input")

  -- migration: three pits under a wagon slot, a lone loader at a wagon end
  local xm = X0 + 41
  rails(surface, xm, -41, 41)
  stop(surface, xm, -21, "Old")
  local function legacy(name, y)
    local e = surface.create_entity({ name = name, position = { xm, y }, force = "player", raise_built = true })
    return remote.call("bulk-wagons", "align_station", e)
  end
  s.old = { legacy("bulk-unloading-pit", -13), legacy("bulk-unloading-pit", -11), legacy("bulk-unloading-pit", -9) }
  remote.call("bulk-wagons", "get_inventory", s.old[2]).insert({ name = "stone", count = 321 })
  s.old_loader = legacy("bulk-loading-station", -2)
end

function v2.after_setup(s)
  -- migrate on demand (a fresh game counts as migrated)
  remote.call("bulk-wagons", "migrate_legacy", { { X0 + 30, -60 }, { X0 + 60, 60 } })
end

function v2.check(s)
  local surface = game.surfaces.nauvis
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
  report(remote.call("bulk-wagons", "connector_docked", s.out_east) and not remote.call("bulk-wagons", "connector_docked", s.end_connector),
    "only the long sides count as docking points")
  -- collision: rim blocks the player, gratings and track do not
  local function walkable(x, y) return surface.can_place_entity({ name = "character", position = { x, y } }) end
  report(not walkable(xb + 2.5, -11) and not walkable(xb - 2.5, -9) and walkable(xb + 1.5, -11) and walkable(xb - 1.5, -12),
    "bunker rim blocks players, its gratings do not")
  report(not surface.can_place_entity({ name = "stone-furnace", position = { xb + 1.5, -11 } }), "bunker blocks buildings")

  local xs = X0 + 21
  report(s.silo and s.silo.valid and s.silo.position.y == -11, "silo snaps onto the wagon slot")
  local coal = s.silo_wagon.get_inventory(defines.inventory.cargo_wagon).get_item_count("coal")
  report(coal > 0, "silo fills the wagon", coal .. " coal")
  report(not walkable(xs + 1.5, -11) and not walkable(xs - 2.5, -9), "silo blocks players beside the track")

  local xm = X0 + 41
  local bunkers = surface.find_entities_filtered({ name = "bulk-unloading-bunker", area = { { xm - 4, -15 }, { xm + 4, -7 } } })
  local pits = surface.find_entities_filtered({ name = "bulk-unloading-pit", area = { { xm - 4, -20 }, { xm + 4, 0 } } })
  report(#bunkers == 1 and #pits == 0 and bunkers[1].position.y == -11, "three pits become one bunker on their wagon slot",
    #bunkers .. " bunkers, " .. #pits .. " pits")
  local stone = bunkers[1] and remote.call("bulk-wagons", "get_inventory", bunkers[1]).get_item_count("stone") or 0
  report(stone == 321, "the pits' goods move into the bunker", stone .. " stone")
  local silos = surface.find_entities_filtered({ name = "bulk-loading-silo", area = { { xm - 4, -8 }, { xm + 4, 4 } } })
  report(#silos == 1 and silos[1].position.y == -4, "a loader at a wagon end becomes a silo on that wagon's slot",
    #silos == 1 and serpent.line(silos[1].position) or (#silos .. " silos"))
end

return v2
