-- Names and geometry shared by the data and control stage.
local shared = {}

shared.wagon = "bulk-wagon"
shared.pit = "bulk-unloading-pit"
shared.loader = "bulk-loading-station"
shared.belt_loader = "bulk-belt-loader"
shared.port = "bulk-station-port"
shared.rail_port = "bulk-rail-port"

-- Each station comes in 4 variants, one per direction of its belt port:
-- 1 = rail north-south, port east; 2 = rail east-west, port south;
-- 3 = rail north-south, port west; 4 = rail east-west, port north.
shared.variant_count = 4

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

-- Hidden inventory container of a station, one per rail direction.
function shared.store_name(base, vertical) return base .. (vertical and "-store-v" or "-store-h") end

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
