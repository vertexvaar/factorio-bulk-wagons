local shared = require("shared")
local sounds = require("__base__.prototypes.entity.sounds")
local graphics = require("prototypes.graphics")

local wagon_slots = settings.startup["bulk-wagons-wagon-slots"].value
local gfx = "__bulk-wagons__/graphics/placeholder/"

-- Stations straddle the track. They must not collide with rails (so they can be
-- built across them) or with trains, but must block buildings and belts (via their
-- own layer, see shared.collision_layer). Players are blocked too, except on the
-- pit whose grate is walkable.
data:extend({ { type = "collision-layer", name = shared.collision_layer } })
local station_mask = {
  layers = { [shared.collision_layer] = true, player = true, transport_belt = true, water_tile = true, is_object = true },
}
local walkable_mask =
  { layers = { [shared.collision_layer] = true, transport_belt = true, water_tile = true, is_object = true } }

-- A station is a visual entity (simple-entity-with-owner: draws on a chosen render
-- layer, rotates through its variants, shows in ghosts and blueprints). Stations with
-- an inventory get a hidden container on top, created by the script, which takes
-- the mouse (higher selection priority), the GUI, inserters and circuit wires.
-- Hidden container that takes the mouse (higher selection priority), the GUI,
-- inserters and circuit wires of a station. offset: its position relative to the
-- station centre; its selection box still covers the whole station.
local function window_entity(def, name, half_w, half_h, offset)
  return {
    type = "container",
    name = name,
    icon = def.icon,
    flags = {
      "placeable-neutral",
      "player-creation",
      "not-blueprintable",
      "not-deconstructable",
      "placeable-off-grid",
    },
    hidden = true,
    localised_name = { "entity-name." .. def.name },
    localised_description = { "entity-description." .. def.name },
    placeable_by = { item = def.name, count = 1 },
    minable = { mining_time = 0.5, result = def.name },
    selection_priority = 60,
    max_health = 500,
    open_sound = sounds.metallic_chest_open,
    close_sound = sounds.metallic_chest_close,
    collision_box = { { -half_w + 0.1, -half_h + 0.1 }, { half_w - 0.1, half_h - 0.1 } },
    selection_box = {
      { -half_w - offset[1], -half_h - offset[2] },
      { half_w - offset[1], half_h - offset[2] },
    },
    collision_mask = { layers = {} },
    circuit_wire_max_distance = 9,
    picture = util.empty_sprite(),
    offset = offset, -- removed again before data:extend
  }
end

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

      local picture = graphics.station_picture(def.sprite, variant, planet)
        or {
          filename = gfx .. def.placeholder .. "-" .. variant .. ".png",
          width = vertical and 384 or 128,
          height = vertical and 128 or 384,
          scale = 0.5,
          tint = shared.placeholder_tint[planet],
        }
      prototypes[#prototypes + 1] = {
        type = "simple-entity-with-owner",
        name = name,
        icon = def.icon,
        flags = { "placeable-neutral", "player-creation" },
        hidden_in_factoriopedia = variant ~= 1 or planet ~= shared.default_planet,
        placeable_by = { item = def.name, count = 1 },
        minable = { mining_time = 0.5, result = def.name },
        max_health = 500,
        corpse = "medium-remnants",
        dying_explosion = "medium-explosion",
        collision_box = { { -half_w + 0.1, -half_h + 0.1 }, { half_w - 0.1, half_h - 0.1 } },
        selection_box = { { -half_w, -half_h }, { half_w, half_h } },
        collision_mask = def.walkable and walkable_mask or station_mask,
        -- snaps to the rail grid: the centre lands on a straight rail's centre, like rail
        -- signals in their slots, so three stations line up under one wagon
        build_grid_size = 2,
        render_layer = def.render_layer,
        picture = picture,
      }

      -- the station's window: its inventory, or the belt loader's control box
      local store
      if def.inventory then
        store = window_entity(def, shared.store_name(def.name, variant, planet), half_w, half_h, { 0, 0 })
        store.inventory_size = math.max(1, math.floor(wagon_slots * def.inventory + 0.5))
        store.inventory_type = "with_filters_and_bar"
      else
        local off = shared.rotate(shared.control_offset, variant)
        store = window_entity(def, shared.control_name(variant, planet), half_w, half_h, off)
        store.collision_box = { { -0.4, -0.4 }, { 0.4, 0.4 } }
        -- nothing to store: the window only carries the preview, wires and panels
        store.inventory_size = 0
      end
      store.integration_patch = graphics.preview_patch(picture, def.sprite, variant, planet, store.offset)
      store.integration_patch_render_layer = def.render_layer
      store.drawing_box_vertical_extension = def.preview_height
      store.offset = nil
      prototypes[#prototypes + 1] = store
    end
  end

  if def.inventory then
    -- inventories of stations built before 0.3.0
    for _, vertical in pairs({ true, false }) do
      local half_w, half_h = 3, 1
      if not vertical then
        half_w, half_h = 1, 3
      end
      local store = window_entity(def, shared.legacy_store_name(def.name, vertical), half_w, half_h, { 0, 0 })
      store.inventory_size = math.max(1, math.floor(wagon_slots * def.inventory + 0.5))
      store.inventory_type = "with_filters_and_bar"
      store.offset = nil
      prototypes[#prototypes + 1] = store
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
  icon = "__bulk-wagons__/graphics/icons/unloading-pit.png",
  sprite = "e1",
  placeholder = "unloading-pit",
  -- over ballast and sleepers, under the rail metal
  render_layer = "ground-patch-higher2",
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
  icon = "__bulk-wagons__/graphics/icons/belt-loader.png",
  sprite = "b3",
  placeholder = "belt-loader",
  preview_height = 2,
  render_layer = "lower-object-above-shadow",
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
  icon = "__bulk-wagons__/graphics/icons/loading-station.png",
  sprite = "b1",
  placeholder = "loading-station",
  preview_height = 3.5,
  render_layer = "lower-object-above-shadow",
  order = "a[train-system]-z[bulk]-b[loading-station]",
  inventory = settings.startup["bulk-wagons-loader-multiplier"].value,
  ingredients = {
    { type = "item", name = "steel-plate", amount = 30 },
    { type = "item", name = "iron-gear-wheel", amount = 20 },
    { type = "item", name = "advanced-circuit", amount = 5 },
    { type = "item", name = "fast-transport-belt", amount = 10 },
  },
}))

-- Hidden constant combinator wired to a station's inventory: carries the wagon readings.
local signals = table.deepcopy(data.raw["constant-combinator"]["constant-combinator"])
signals.name = shared.signals
signals.hidden = true
signals.flags =
  { "not-blueprintable", "not-deconstructable", "not-on-map", "placeable-off-grid", "no-copy-paste", "not-upgradable" }
signals.selectable_in_game = false
signals.minable = nil
signals.collision_mask = { layers = {} }
signals.collision_box = { { -0.1, -0.1 }, { 0.1, 0.1 } }
signals.sprites = util.empty_sprite()
signals.activity_led_sprites = util.empty_sprite()
signals.draw_circuit_wires = false
signals.circuit_wire_max_distance = 9
data:extend({ signals })

graphics.station_overlays()

-- Built-in belt ports: hidden 1x1 loaders the script places at the station's port tile.
-- Only their belt shows; the housing is part of the station artwork.
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
  if graphics.available then
    port.structure = { direction_in = util.empty_sprite(), direction_out = util.empty_sprite() }
  end
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
