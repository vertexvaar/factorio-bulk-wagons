local shared = require("shared")
local sounds = require("__base__.prototypes.entity.sounds")
local graphics = require("prototypes.graphics")

local wagon_slots = settings.startup["bulk-wagons-wagon-slots"].value
local gfx = "__bulk-wagons__/graphics/placeholder/"

-- Stations straddle the track. They must not collide with rails (so they can be
-- built across them) or with trains, but must block buildings and belts (via their
-- own layer, see shared.collision_layer). Players are blocked too, except on the
-- pit whose grate is walkable.
data:extend({
  { type = "collision-layer", name = shared.collision_layer },
  -- the game wants every two loaders to collide: the hidden ports and the connectors share this
  { type = "collision-layer", name = shared.loader_layer },
})
local station_mask = { layers = { [shared.collision_layer] = true, player = true, transport_belt = true, is_object = true } }
local walkable_mask = { layers = { [shared.collision_layer] = true, transport_belt = true, is_object = true } }

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
    -- the three-per-wagon stations give way to bunker and silo; leftovers still build
    hidden = true,
    subgroup = "train-transport",
    order = def.order,
    place_result = def.name,
    stack_size = 10,
  }
  return prototypes
end

-- Bunker and silo over one wagon (shared.station_size: the bunker 8 x 6, the silo 6 x 6),
-- in two variants (1: rail north-south, 2: rail east-west; the script turns them to the
-- rail). The building blocks other buildings and belts; hidden blockers
-- (shared.solid_parts) keep players and vehicles off its solid parts.
local station_mask_v2 = { layers = { [shared.collision_layer] = true, transport_belt = true } }

local function wagon_station(def)
  local prototypes = {}
  local size = shared.station_size[def.name]
  for _, planet in pairs(shared.active_planets(mods)) do
    for variant = 1, shared.variant_count_of(def.name) do
      local name = shared.variant_name(def.name, variant, planet)
      local hw, hh = size[1] / 2, size[2] / 2
      if not shared.rail_is_vertical(variant) then hw, hh = hh, hw end
      local picture = graphics.station_picture(def.sprite, variant, planet)
        or {
          filename = gfx .. def.placeholder .. "-" .. variant .. ".png",
          width = 384,
          height = 384,
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
        minable = { mining_time = 0.8, result = def.name },
        max_health = 1000,
        corpse = "big-remnants",
        dying_explosion = "big-explosion",
        collision_box = { { -hw + 0.1, -hh + 0.1 }, { hw - 0.1, hh - 0.1 } },
        selection_box = { { -hw, -hh }, { hw, hh } },
        collision_mask = station_mask_v2,
        render_layer = def.render_layer,
        tall = def.tall,
        picture = picture,
      }
      local store = window_entity(def, shared.store_name(def.name, variant, planet), hw, hh, { 0, 0 })
      -- hidden with the tall buildings, so the wagon under the silo can be clicked
      store.tall = def.tall
      -- as big as the three stations it replaces, so their goods fit on update
      store.inventory_size = math.max(1, math.floor(3 * wagon_slots * def.inventory + 0.5))
      store.inventory_type = "with_filters_and_bar"
      store.integration_patch = graphics.preview_patch(picture, def.sprite, variant, planet, store.offset)
      store.integration_patch_render_layer = def.render_layer
      store.drawing_box_vertical_extension = def.preview_height
      store.offset = nil
      prototypes[#prototypes + 1] = store
    end
  end
  -- the east-west variant only lives in the cursor (rotated with R)
  prototypes[#prototypes + 1] = {
    type = "item",
    name = shared.variant_name(def.name, 2),
    icon = def.icon,
    hidden = true,
    subgroup = "train-transport",
    order = def.order .. "-2",
    place_result = shared.variant_name(def.name, 2),
    stack_size = 10,
  }
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
    energy_required = 10,
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
  port.collision_mask = { layers = { transport_belt = true, [shared.loader_layer] = true } }
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

--------------------------------------------------------------------------------
-- Bunker and silo (0.4.0)

data:extend(wagon_station({
  name = shared.bunker,
  icon = "__bulk-wagons__/graphics/icons/unloading-bunker.png",
  sprite = "bunker",
  placeholder = "unloading-bunker",
  -- over ballast and sleepers, under the rail metal; the moving parts are drawn above
  render_layer = "ground-patch-higher2",
  order = "a[train-system]-z[bulk]-c[unloading-bunker]",
  inventory = settings.startup["bulk-wagons-pit-multiplier"].value,
  ingredients = {
    { type = "item", name = "concrete", amount = 100 },
    { type = "item", name = "steel-plate", amount = 50 },
    { type = "item", name = "iron-gear-wheel", amount = 40 },
  },
}))

data:extend(wagon_station({
  name = shared.silo,
  icon = "__bulk-wagons__/graphics/icons/loading-silo.png",
  sprite = "silo",
  placeholder = "loading-silo",
  preview_height = 4,
  render_layer = "lower-object-above-shadow",
  tall = true,
  order = "a[train-system]-z[bulk]-d[loading-silo]",
  inventory = settings.startup["bulk-wagons-loader-multiplier"].value,
  ingredients = {
    { type = "item", name = "steel-plate", amount = 80 },
    { type = "item", name = "concrete", amount = 40 },
    { type = "item", name = "iron-gear-wheel", amount = 40 },
    { type = "item", name = "advanced-circuit", amount = 10 },
  },
}))

-- Blockers for the solid parts (both orientations of every strip size).
local blockers, seen = {}, {}
for _, parts in pairs(shared.solid_parts) do
  for _, part in pairs(parts) do
    for _, size in pairs({ { part[2][1], part[2][2] }, { part[2][2], part[2][1] } }) do
      local name = shared.blocker_name(size[1], size[2])
      if not seen[name] then
        seen[name] = true
        blockers[#blockers + 1] = {
          type = "simple-entity-with-owner",
          name = name,
          hidden = true,
          flags = { "not-blueprintable", "not-deconstructable", "not-on-map", "placeable-off-grid", "no-copy-paste",
            "not-upgradable", "not-selectable-in-game" },
          selectable_in_game = false,
          collision_box = { { -size[1] / 2 + 0.05, -size[2] / 2 + 0.05 }, { size[1] / 2 - 0.05, size[2] / 2 - 0.05 } },
          collision_mask = { layers = { player = true, car = true } },
          picture = util.empty_sprite(),
        }
      end
    end
  end
end
data:extend(blockers)

-- Connectors: 1x1 loaders in each belt tier that stand on the rim of a bunker or silo
-- (the script takes back one built anywhere else). They never drop goods on the ground:
-- an output without a belt simply holds them. They do not collide with the station or
-- its blockers, only with other buildings and belts.
local connector_mask = { layers = { item = true, object = true, [shared.loader_layer] = true } }
local base_loader = data.raw["loader-1x1"]["loader-1x1"]
local previous = {}
local order = 0
for _, def in ipairs(shared.connectors) do
  local source = data.raw.loader[def.loader]
  local belt = data.raw["transport-belt"][def.belt]
  if belt then
    order = order + 1
    local icon = graphics.connector_icon(def.tier) or data.raw.item[def.loader] and data.raw.item[def.loader].icon
      or base_loader.icon
    for _, base in ipairs(shared.station_bases) do
      local loader = table.deepcopy(base_loader)
      loader.name = shared.connector_name(def, base)
      loader.hidden = false
      loader.hidden_in_factoriopedia = base ~= shared.bunker
      loader.flags = { "placeable-neutral", "player-creation" }
      loader.subgroup = "train-transport"
      loader.localised_name = { "entity-name." .. def.name }
      loader.localised_description = { "entity-description.bulk-connector" }
      loader.minable = { mining_time = 0.1, result = def.name }
      loader.placeable_by = { item = def.name, count = 1 }
      loader.max_health = 170
      loader.corpse = "small-remnants"
      loader.collision_mask = connector_mask
      -- above the station's window, which covers the whole station
      loader.selection_priority = 70
      loader.fast_replaceable_group = "bulk-connector"
      loader.allow_rail_interaction = false
      loader.container_distance = 1
      loader.speed = belt.speed
      loader.belt_animation_set = belt.belt_animation_set
      loader.icon = icon
      loader.icon_size = nil
      if source then
        loader.working_sound = source.working_sound
        loader.open_sound, loader.close_sound = source.open_sound, source.close_sound
        loader.circuit_connector = source.circuit_connector
        loader.circuit_wire_max_distance = source.circuit_wire_max_distance
        loader.max_belt_stack_size = source.max_belt_stack_size
        loader.adjustable_belt_stack_size = source.adjustable_belt_stack_size
        loader.resistances = source.resistances
      end
      loader.structure = graphics.connector_structure(def.tier, base) or loader.structure
      if previous[base] then data.raw["loader-1x1"][previous[base]].next_upgrade = loader.name end
      previous[base] = loader.name
      data:extend({ loader })
    end

    -- the 2x1 connector of 0.4, hidden: the script turns it into a 1x1 one on the rim
    if source then
      local legacy = table.deepcopy(source)
      legacy.name = def.name
      legacy.hidden = true
      legacy.minable = { mining_time = 0.1, result = def.name }
      legacy.placeable_by = { item = def.name, count = 1 }
      legacy.next_upgrade = nil
      legacy.fast_replaceable_group = nil
      legacy.allow_rail_interaction = false
      legacy.speed = belt.speed
      legacy.localised_name = { "entity-name." .. def.name }
      legacy.localised_description = { "entity-description.bulk-connector" }
      legacy.structure = graphics.legacy_connector_structure(def.tier) or legacy.structure
      legacy.icon = icon
      legacy.icon_size = nil
      data:extend({ legacy })
    end

    data:extend({
      {
        type = "item",
        name = def.name,
        icon = icon,
        subgroup = "train-transport",
        order = "a[train-system]-z[bulk]-e[connector]-" .. order,
        place_result = shared.connector_name(def, shared.bunker),
        stack_size = 50,
      },
      {
        type = "recipe",
        name = def.name,
        energy_required = 1,
        enabled = false,
        ingredients = previous.item and {
          { type = "item", name = previous.item, amount = 1 },
          { type = "item", name = def.belt, amount = 5 },
          { type = "item", name = "iron-gear-wheel", amount = 10 },
        } or {
          { type = "item", name = def.belt, amount = 5 },
          { type = "item", name = "iron-gear-wheel", amount = 5 },
          { type = "item", name = "iron-plate", amount = 5 },
        },
        results = { { type = "item", name = def.name, amount = 1 } },
      },
    })
    previous.item = def.name
  end
end
