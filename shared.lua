-- Names and geometry shared by the data and control stage.
local shared = {}

shared.wagon = "bulk-wagon"
shared.pit = "bulk-unloading-pit"
shared.loader = "bulk-loading-station"
shared.belt_loader = "bulk-belt-loader"
shared.port = "bulk-station-port"
shared.rail_port = "bulk-rail-port"

-- Since 0.4.0 one building serves a whole wagon: the unloading bunker under the
-- track and the loading silo over it, 6 x 6 tiles each, fed or emptied by connectors
-- (loaders, one per belt tier) on their long sides. The three-per-wagon stations
-- above are legacy: they keep working until the update replaces them.
shared.bunker = "bulk-unloading-bunker"
shared.silo = "bulk-loading-silo"
shared.legacy_bases = { shared.pit, shared.loader, shared.belt_loader }
shared.station_bases = { shared.bunker, shared.silo }
shared.all_bases = { shared.pit, shared.loader, shared.belt_loader, shared.bunker, shared.silo }

function shared.is_legacy(base) return base == shared.pit or base == shared.loader or base == shared.belt_loader end

-- Legacy stations come in 4 variants, one per direction of their belt port:
-- 1 = rail north-south, port east; 2 = rail east-west, port south;
-- 3 = rail north-south, port west; 4 = rail east-west, port north.
-- Bunker and silo have no port: 1 = rail north-south, 2 = rail east-west.
shared.variant_count = 4
function shared.variant_count_of(base) return shared.is_legacy(base) and 4 or 2 end

-- Half size of a bunker or silo: 3 tiles along the track and across it.
shared.station_half = 3

-- Connectors: loaders in the belt tiers that dock onto the long sides of a bunker or
-- silo. Built from the game's own (hidden) loaders; a tier exists when its loader does.
shared.connectors = {
  { name = "bulk-connector", loader = "loader", belt = "transport-belt", tech = "bulk-wagons" },
  { name = "bulk-fast-connector", loader = "fast-loader", belt = "fast-transport-belt", tech = "logistics-2" },
  { name = "bulk-express-connector", loader = "express-loader", belt = "express-transport-belt", tech = "logistics-3" },
  { name = "bulk-turbo-connector", loader = "turbo-loader", belt = "turbo-transport-belt", tech = "turbo-transport-belt" },
}

-- Rolling stock stands 7 tiles apart. A train halts with the centre of its front
-- carriage 3 tiles behind its train stop (measured), so the carriages of a halted
-- train sit at stop + back * (3 + 7 k): the wagon slots of that stop.
shared.wagon_pitch = 7
shared.first_slot = 3
-- how far behind a train stop slots are offered, in carriages
shared.slot_count = 12

-- Every planet gets its own look. Nauvis (and any planet this mod does not
-- know) uses the plain names; the others append the planet name.
shared.planets = { "nauvis", "vulcanus", "fulgora", "gleba", "aquilo" }
shared.default_planet = "nauvis"

local function with_planet(base, planet)
  if planet and planet ~= shared.default_planet then return base .. "-" .. planet end
  return base
end

function shared.variant_name(base, variant, planet)
  local name = with_planet(base, planet)
  if variant == 1 then return name end
  return name .. "-" .. variant
end

-- Planets that get their own variants; without Space Age only Nauvis.
function shared.active_planets(active_mods)
  if active_mods["space-age"] then return shared.planets end
  return { shared.default_planet }
end

-- Placeholder tints that tell the planet variants apart until real art exists.
shared.placeholder_tint = {
  nauvis = { 1, 1, 1 },
  vulcanus = { 1, 0.6, 0.4 },
  fulgora = { 0.85, 0.7, 1 },
  gleba = { 0.7, 1, 0.6 },
  aquilo = { 0.7, 0.9, 1 },
}

-- Hidden inventory container of a station, one per variant and planet (it shows the
-- station in the window preview).
function shared.store_name(base, variant, planet) return with_planet(base, planet) .. "-store-" .. variant end

-- Inventories of stations built before 0.3.0, one per rail direction.
function shared.legacy_store_name(base, vertical) return base .. (vertical and "-store-v" or "-store-h") end

-- The belt loader has no inventory; a small control box at its tower end carries the
-- circuit connection and settings window (one per variant, its selection box covers
-- the whole station). It sits away from the belt port so the port reaches the wagon.
function shared.control_name(variant, planet) return with_planet(shared.belt_loader, planet) .. "-control-" .. variant end

shared.control_offset = { -2.5, 0.5 } -- variant 1, rotated like the port

-- Collision layer of the stations. Buildings, trees, rocks, signals and the like get it
-- too (data-final-fixes.lua), rails and trains do not, so a station fits across the
-- track but not onto anything else.
shared.collision_layer = "bulk_wagons_station"

-- Hidden constant combinator that puts a station's wagon readings on its network.
shared.signals = "bulk-station-signals"

-- Entities that open a station's window (its hidden inventory or control box), for
-- every planet; not all of them exist without Space Age.
function shared.station_window_names()
  local names = {}
  for _, base in pairs({ shared.pit, shared.loader }) do
    names[#names + 1] = shared.legacy_store_name(base, true)
    names[#names + 1] = shared.legacy_store_name(base, false)
  end
  for _, planet in pairs(shared.planets) do
    for variant = 1, shared.variant_count do
      names[#names + 1] = shared.store_name(shared.pit, variant, planet)
      names[#names + 1] = shared.store_name(shared.loader, variant, planet)
      names[#names + 1] = shared.control_name(variant, planet)
    end
    for _, base in pairs(shared.station_bases) do
      for variant = 1, shared.variant_count_of(base) do
        names[#names + 1] = shared.store_name(base, variant, planet)
      end
    end
  end
  return names
end

-- Hidden blockers that keep players and vehicles off the solid parts of a bunker or
-- silo (the building itself only blocks buildings and belts, so its gratings and the
-- track stay walkable). Named by their size in tiles.
function shared.blocker_name(w, h) return "bulk-blocker-" .. w .. "x" .. h end

-- The solid strips of a station for variant 1 (rail north-south): { centre, size }.
-- The bunker's outer rim, 1 tile on either side; the silo everything beside the track.
shared.solid_parts = {
  [shared.bunker] = { { { -2.5, 0 }, { 1, 6 } }, { { 2.5, 0 }, { 1, 6 } } },
  [shared.silo] = { { { -2, 0 }, { 2, 6 } }, { { 2, 0 }, { 2, 6 } } },
}

-- Wagon slots behind every train stop near position (within radius tiles), on a
-- straight track through position. vertical: the track runs north-south. Returns the
-- along-track coordinates (y for vertical track, x otherwise).
function shared.wagon_slots(surface, position, vertical, radius)
  local slots = {}
  local area = { { position.x - radius, position.y - radius }, { position.x + radius, position.y + radius } }
  for _, stop in pairs(surface.find_entities_filtered({ type = "train-stop", area = area })) do
    local d = stop.direction
    local north, south = defines.direction.north, defines.direction.south
    local east, west = defines.direction.east, defines.direction.west
    local stop_vertical = d == north or d == south
    local on_axis = stop_vertical or d == east or d == west
    -- the stop stands 2 tiles beside its rail
    local across = vertical and math.abs(stop.position.x - position.x) or math.abs(stop.position.y - position.y)
    if on_axis and stop_vertical == vertical and math.abs(across - 2) < 0.6 then
      local along = vertical and stop.position.y or stop.position.x
      -- the train travels in the stop's direction; its carriages trail behind
      local back = (d == north or d == west) and 1 or -1
      for k = 0, shared.slot_count - 1 do
        slots[#slots + 1] = along + back * (shared.first_slot + shared.wagon_pitch * k)
      end
    end
  end
  return slots
end

-- Default station colour. Like rolling stock, colours are applied at alpha 0.5.
shared.station_color = { r = 0.45, g = 0.5, b = 0.22, a = 0.5 }

function shared.wagon_name(planet) return with_planet(shared.wagon, planet) end

-- Rotates a vector clockwise by (variant - 1) quarter turns.
function shared.rotate(vec, variant)
  local x, y = vec[1], vec[2]
  for _ = 2, variant do
    x, y = -y, x
  end
  return { x, y }
end

-- Rail runs north-south for odd variants.
function shared.rail_is_vertical(variant) return variant % 2 == 1 end

-- Position of the built-in belt port relative to the station centre (variant 1).
shared.port_offset = { 2.5, -0.5 }

return shared
