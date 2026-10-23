local shared = require("shared")
local sounds = require("__base__.prototypes.entity.sounds")

local wagon_slots = settings.startup["bulk-wagons-wagon-slots"].value
local gfx = "__bulk-wagons__/graphics/placeholder/"

-- Stations straddle the track. They must not collide with rails (so they can be
-- built across them) or with trains, but must block buildings, belts and players.
local station_mask = { layers = { player = true, is_object = true, transport_belt = true } }

local function station_variants(def)
  local prototypes = {}
  for variant = 1, shared.variant_count do
    local name = shared.variant_name(def.name, variant)
    local vertical = shared.rail_is_vertical(variant)
    local half_w, half_h = 3, 1
    if not vertical then half_w, half_h = 1, 3 end

    prototypes[#prototypes + 1] = {
      type = "container",
      name = name,
      icon = def.icon,
      flags = { "placeable-neutral", "player-creation" },
      hidden_in_factoriopedia = variant ~= 1,
      placeable_by = { item = def.name, count = 1 },
      minable = { mining_time = 0.5, result = def.name },
      max_health = 500,
      corpse = "medium-remnants",
      dying_explosion = "medium-explosion",
      open_sound = sounds.metallic_chest_open,
      close_sound = sounds.metallic_chest_close,
      collision_box = { { -half_w + 0.1, -half_h + 0.1 }, { half_w - 0.1, half_h - 0.1 } },
      selection_box = { { -half_w, -half_h }, { half_w, half_h } },
      collision_mask = station_mask,
      inventory_size = math.max(1, math.floor(wagon_slots * def.multiplier + 0.5)),
      inventory_type = "with_filters_and_bar",
      picture = {
        filename = gfx .. def.sprite .. "-" .. variant .. ".png",
        width = vertical and 384 or 128,
        height = vertical and 128 or 384,
        scale = 0.5,
      },
      circuit_wire_max_distance = 9,
    }

    if variant ~= 1 then
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
  order = "a[train-system]-z[bulk]-b[unloading-pit]",
  multiplier = settings.startup["bulk-wagons-pit-multiplier"].value,
  ingredients = {
    { type = "item", name = "concrete", amount = 40 },
    { type = "item", name = "steel-plate", amount = 20 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "transport-belt", amount = 10 },
  },
}))

data:extend(station_variants({
  name = shared.loader,
  icon = gfx .. "loading-station-icon.png",
  sprite = "loading-station",
  order = "a[train-system]-z[bulk]-a[loading-station]",
  multiplier = settings.startup["bulk-wagons-loader-multiplier"].value,
  ingredients = {
    { type = "item", name = "steel-plate", amount = 30 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "electronic-circuit", amount = 10 },
    { type = "item", name = "transport-belt", amount = 10 },
  },
}))

-- Built-in belt port: a hidden 1x1 loader the script places at the station's port tile.
local belt = data.raw["transport-belt"][settings.startup["bulk-wagons-port-belt"].value]
  or data.raw["transport-belt"]["express-transport-belt"]

local port = table.deepcopy(data.raw["loader-1x1"]["loader-1x1"])
port.name = "bulk-station" .. shared.port_suffix
port.hidden = true
port.flags = { "not-blueprintable", "not-deconstructable", "not-on-map", "placeable-off-grid", "no-copy-paste", "not-upgradable" }
port.selectable_in_game = false
port.minable = nil
port.collision_mask = { layers = { transport_belt = true } }
port.speed = belt.speed
port.belt_animation_set = belt.belt_animation_set
port.container_distance = 1
port.allow_rail_interaction = false
port.filter_count = 0
data:extend({ port })
