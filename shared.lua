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

function shared.variant_name(base, variant)
  if variant == 1 then return base end
  return base .. "-" .. variant
end

-- Rotates a vector clockwise by (variant - 1) quarter turns.
function shared.rotate(vec, variant)
  local x, y = vec[1], vec[2]
  for _ = 2, variant do
    x, y = -y, x
  end
  return { x, y }
end

-- Rail runs north-south for odd variants.
function shared.rail_is_vertical(variant)
  return variant % 2 == 1
end

-- Position of the built-in belt port relative to the station centre (variant 1).
shared.port_offset = { 2.5, -0.5 }

return shared
