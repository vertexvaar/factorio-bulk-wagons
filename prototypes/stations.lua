local shared = require("shared")
local sounds = require("__base__.prototypes.entity.sounds")

local wagon_slots = settings.startup["bulk-wagons-wagon-slots"].value
local gfx = "__bulk-wagons__/graphics/placeholder/"

-- Stations straddle the track. They must not collide with rails (so they can be
-- built across them) or with trains, but must block buildings and belts.
-- Players are blocked too, except on the pit whose grate is walkable.
local station_mask = { layers = { player = true, is_object = true, transport_belt = true } }
local walkable_mask = { layers = { is_object = true, transport_belt = true } }

local function station_variants(def)
  local prototypes = {}
  for _, planet in pairs(shared.active_planets(mods)) do
    for variant = 1, shared.variant_count do
      local name = shared.variant_name(def.name, variant, planet)
      local vertical = shared.rail_is_vertical(variant)
      local half_w, half_h = 3, 1
      if not vertical then
        half_w, half_h = 1, 3
      end

      local entity = {
        type = def.inventory and "container" or "simple-entity-with-owner",
        name = name,
        icon = def.icon,
        flags = { "placeable-neutral", "player-creation" },
        hidden_in_factoriopedia = variant ~= 1 or planet ~= shared.default_planet,
        placeable_by = { item = def.name, count = 1 },
        minable = { mining_time = 0.5, result = def.name },
        max_health = 500,
        corpse = "medium-remnants",
        dying_explosion = "medium-explosion",
        open_sound = sounds.metallic_chest_open,
        close_sound = sounds.metallic_chest_close,
        collision_box = { { -half_w + 0.1, -half_h + 0.1 }, { half_w - 0.1, half_h - 0.1 } },
        selection_box = { { -half_w, -half_h }, { half_w, half_h } },
        collision_mask = def.walkable and walkable_mask or station_mask,
        picture = {
          filename = gfx .. def.sprite .. "-" .. variant .. ".png",
          width = vertical and 384 or 128,
          height = vertical and 128 or 384,
          scale = 0.5,
          tint = shared.placeholder_tint[planet],
        },
      }
      if def.inventory then
        entity.inventory_size = math.max(1, math.floor(wagon_slots * def.inventory + 0.5))
        entity.inventory_type = "with_filters_and_bar"
        entity.circuit_wire_max_distance = 9
      end
      prototypes[#prototypes + 1] = entity
    end
  end

  for variant = 2, shared.variant_count do
    local name = shared.variant_name(def.name, variant)
    -- Rotated variants exist as items only so they can sit in the cursor.
    prototypes[#prototypes + 1] = {
      type = "item",
      name = name,
      icon = def.icon,
      hidden = true,
      subgroup = "train-transport",
      order = def.order .. "-" .. variant,
      place_result = name,
      stack_size = 10,
    }
  end

  prototypes[#prototypes + 1] = {
    type = "item",
    name = def.name,
    icon = def.icon,
    subgroup = "train-transport",
    order = def.order,
    place_result = def.name,
    stack_size = 10,
  }
  prototypes[#prototypes + 1] = {
    type = "recipe",
    name = def.name,
    energy_required = 5,
    enabled = false,
    ingredients = def.ingredients,
    results = { { type = "item", name = def.name, amount = 1 } },
  }
  return prototypes
end

data:extend(station_variants({
  name = shared.pit,
  icon = gfx .. "unloading-pit-icon.png",
  sprite = "unloading-pit",
  order = "a[train-system]-z[bulk]-c[unloading-pit]",
  inventory = settings.startup["bulk-wagons-pit-multiplier"].value,
  walkable = true,
  ingredients = {
    { type = "item", name = "concrete", amount = 40 },
    { type = "item", name = "steel-plate", amount = 20 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "transport-belt", amount = 10 },
  },
}))

-- Tier 1 loader: no inventory, the belt feeds the wagon directly.
data:extend(station_variants({
  name = shared.belt_loader,
  icon = gfx .. "belt-loader-icon.png",
  sprite = "belt-loader",
  order = "a[train-system]-z[bulk]-a[belt-loader]",
  ingredients = {
    { type = "item", name = "steel-plate", amount = 10 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "transport-belt", amount = 10 },
  },
}))

-- Tier 2 loader: portal silo with an inventory.
data:extend(station_variants({
  name = shared.loader,
  icon = gfx .. "loading-station-icon.png",
  sprite = "loading-station",
  order = "a[train-system]-z[bulk]-b[loading-station]",
  inventory = settings.startup["bulk-wagons-loader-multiplier"].value,
  ingredients = {
    { type = "item", name = "steel-plate", amount = 30 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "advanced-circuit", amount = 5 },
    { type = "item", name = "fast-transport-belt", amount = 10 },
  },
}))

-- Built-in belt ports: hidden 1x1 loaders the script places at the station's port tile.
local function make_port(name, speed, container_distance, rail_interaction)
  local port = table.deepcopy(data.raw["loader-1x1"]["loader-1x1"])
  port.name = name
  port.hidden = true
  port.flags = {
    "not-blueprintable",
    "not-deconstructable",
    "not-on-map",
    "placeable-off-grid",
    "no-copy-paste",
    "not-upgradable",
  }
  port.selectable_in_game = false
  port.minable = nil
  port.collision_mask = { layers = { transport_belt = true } }
  port.speed = speed.speed
  port.belt_animation_set = speed.belt_animation_set
  port.container_distance = container_distance
  port.allow_rail_interaction = rail_interaction
  port.filter_count = 0
  return port
end

local port_belt = data.raw["transport-belt"][settings.startup["bulk-wagons-port-belt"].value]
  or data.raw["transport-belt"]["express-transport-belt"]

-- The belt loader never throttles: its port runs at the fastest belt, so the
-- connected belt sets the pace.
local fastest = port_belt
for _, belt in pairs(data.raw["transport-belt"]) do
  if belt.speed > fastest.speed then fastest = belt end
end

data:extend({
  make_port(shared.port, port_belt, 1, false),
  -- Sits at the end of the station and reaches over the side tiles into the wagon.
  make_port(shared.rail_port, fastest, 2, true),
})
