local shared = require("shared")

local TRANSFER_PERIOD = 30 -- ticks between transfer passes
local SWEEP_PERIOD = 60 -- ticks between checks for forbidden items in wagons
local OPEN_GUI_PERIOD = 10 -- ticks between checks of wagons a player has open
local PORT_NAMES = { [shared.port] = true, [shared.rail_port] = true }

-- Items that are bulk goods but not (or not always) a mined resource.
local EXTRA_BULK_ITEMS = {
  "ice", "carbon", "sulfur", "uranium-235", "uranium-238", "holmium-ore",
  "tree-seed", "jellynut-seed", "yumako-seed",
}

local planet_set = {}
for _, planet in pairs(shared.planets) do planet_set[planet] = true end

-- entity/item name -> { base = station base name, variant = 1..4, planet = name }.
-- Planet variants only exist with Space Age; exists() tells which are defined.
local variant_of = {}
-- entity name -> planet, for every bulk wagon prototype name
local wagon_planet = {}
for _, planet in pairs(shared.planets) do
  for _, base in pairs({ shared.pit, shared.loader, shared.belt_loader }) do
    for variant = 1, shared.variant_count do
      variant_of[shared.variant_name(base, variant, planet)] = { base = base, variant = variant, planet = planet }
    end
  end
  wagon_planet[shared.wagon_name(planet)] = planet
end
local wagon_names = {} -- defined wagon prototypes, filled on init/load

local function exists(name)
  return prototypes.entity[name] ~= nil
end

local function is_wagon(entity)
  return wagon_planet[entity.name] ~= nil
end

local function planet_of(surface)
  local planet = surface.planet and surface.planet.name
  if planet_set[planet] then return planet end
  return shared.default_planet
end

local function init_storage()
  storage.stations = storage.stations or {} -- unit_number -> { entity, port, base, variant }
  storage.wagons = storage.wagons or {} -- unit_number -> wagon entity
  storage.open_wagons = storage.open_wagons or {} -- player_index -> wagon entity
  storage.remote_allowed = storage.remote_allowed or {}
end

--------------------------------------------------------------------------------
-- Allowed cargo

local function build_allowed()
  local allowed = {}
  for _, resource in pairs(prototypes.get_entity_filtered({ { filter = "type", type = "resource" } })) do
    local mineable = resource.mineable_properties
    for _, product in pairs(mineable and mineable.products or {}) do
      if product.type == "item" then allowed[product.name] = true end
    end
  end
  for _, name in pairs(EXTRA_BULK_ITEMS) do
    if prototypes.item[name] then allowed[name] = true end
  end
  for name in string.gmatch(settings.global["bulk-wagons-extra-items"].value, "[^,%s]+") do
    if prototypes.item[name] then allowed[name] = true end
  end
  for name in pairs(storage.remote_allowed) do
    if prototypes.item[name] then allowed[name] = true end
  end
  storage.allowed = allowed
end

local function show_rejected(wagon, player)
  if player and player.valid then
    player.create_local_flying_text({ text = { "bulk-wagons.only-bulk" }, position = wagon.position })
  else
    rendering.draw_text({
      text = { "bulk-wagons.only-bulk" },
      surface = wagon.surface,
      target = wagon,
      color = { 1, 0.6, 0.2 },
      alignment = "center",
      forces = { wagon.force },
      time_to_live = 120,
    })
  end
end

-- Removes everything that is not a bulk good from the wagon. It goes back to
-- the player if one is given, otherwise it is spilled next to the wagon.
local function purge_wagon(wagon, player)
  local inventory = wagon.get_inventory(defines.inventory.cargo_wagon)
  if not inventory or inventory.is_empty() then return end
  local rejected = false
  for _, item in pairs(inventory.get_contents()) do
    if not storage.allowed[item.name] then
      local stack = { name = item.name, count = item.count, quality = item.quality }
      local removed = inventory.remove(stack)
      local returned = 0
      if player and player.valid then
        returned = player.insert({ name = item.name, count = removed, quality = item.quality })
      end
      if returned < removed then
        wagon.surface.spill_item_stack({
          position = wagon.position,
          stack = { name = item.name, count = removed - returned, quality = item.quality },
          enable_looted = true,
          force = wagon.force,
          allow_belts = false,
        })
      end
      rejected = true
    end
  end
  if rejected then show_rejected(wagon, player) end
end

--------------------------------------------------------------------------------
-- Stations

local function port_position(entity, variant)
  local offset = shared.rotate(shared.port_offset, variant)
  return { entity.position.x + offset[1], entity.position.y + offset[2] }
end

local PORT_DIRECTIONS = {
  defines.direction.east, defines.direction.south, defines.direction.west, defines.direction.north,
}
local OPPOSITE = {
  [defines.direction.east] = defines.direction.west, [defines.direction.west] = defines.direction.east,
  [defines.direction.north] = defines.direction.south, [defines.direction.south] = defines.direction.north,
}

local function create_port(entity, info)
  local outward = PORT_DIRECTIONS[info.variant]
  local is_pit = info.base == shared.pit
  -- A 1x1 loader faces the way items flow: outward when unloading, inward when loading.
  -- The belt loader's port has no inventory behind it and loads the wagon itself.
  local port = entity.surface.create_entity({
    name = info.base == shared.belt_loader and shared.rail_port or shared.port,
    position = port_position(entity, info.variant),
    direction = is_pit and outward or OPPOSITE[outward],
    type = is_pit and "output" or "input",
    force = entity.force,
    create_build_effect_smoke = false,
  })
  if port then
    port.update_connections()
    port.destructible = false
  end
  return port
end

local function register_station(entity, info)
  local record = storage.stations[entity.unit_number]
  if record and record.port and record.port.valid then return end
  record = { entity = entity, base = info.base, variant = info.variant }
  record.port = create_port(entity, info)
  storage.stations[entity.unit_number] = record
  script.register_on_object_destroyed(entity)
end

local function remove_station(unit_number, buffer)
  local record = storage.stations[unit_number]
  if not record then return end
  storage.stations[unit_number] = nil
  local port = record.port
  if port and port.valid then
    if buffer then
      for i = 1, port.get_max_transport_line_index() do
        for _, item in pairs(port.get_transport_line(i).get_contents()) do
          buffer.insert({ name = item.name, count = item.count, quality = item.quality })
        end
      end
    end
    port.destroy()
  end
end

local function straight_rail_in(surface, area)
  for _, rail in pairs(surface.find_entities_filtered({ type = "straight-rail", area = area })) do
    local d = rail.direction
    if d == defines.direction.north or d == defines.direction.south then return rail, true end
    if d == defines.direction.east or d == defines.direction.west then return rail, false end
  end
end

-- Replaces a freshly built entity by another prototype. Returns the new entity,
-- or the original one again if the replacement does not fit.
local function replace(entity, params)
  local surface = entity.surface
  local original = {
    name = entity.name, position = entity.position, direction = params.direction,
    force = entity.force, quality = entity.quality, color = params.color,
  }
  params.force, params.quality, params.create_build_effect_smoke = entity.force, entity.quality, false
  entity.destroy()
  if surface.can_place_entity(params) then
    local created = surface.create_entity(params)
    if created then return created end
  end
  log("bulk-wagons: could not swap " .. original.name .. " for " .. params.name)
  return surface.create_entity(original)
end

-- Picks the station variant for the planet it stands on. A station built by
-- hand (align) also turns and centres itself on the rail below it.
local function fit_station(entity, info, align)
  local variant = info.variant
  local position = { entity.position.x, entity.position.y }
  if align then
    local rail, vertical = straight_rail_in(entity.surface, entity.bounding_box)
    if rail then
      if vertical ~= shared.rail_is_vertical(variant) then variant = variant % shared.variant_count + 1 end
      if vertical then position[1] = rail.position.x else position[2] = rail.position.y end
    end
  end
  local name = shared.variant_name(info.base, variant, planet_of(entity.surface))
  if not exists(name) then name = shared.variant_name(info.base, variant) end
  if name == entity.name and position[1] == entity.position.x and position[2] == entity.position.y then
    return entity
  end
  return replace(entity, { name = name, position = position })
end

-- Swaps a wagon to the variant of the planet it is placed on.
local function fit_wagon(entity)
  local name = shared.wagon_name(planet_of(entity.surface))
  if name == entity.name or not exists(name) then return entity end
  return replace(entity, {
    name = name,
    position = entity.position,
    direction = math.floor(entity.orientation * 16 + 0.5) % 16,
    color = entity.color,
  })
end

local function find_wagon(record)
  local station = record.entity
  local p = station.position
  local vertical = shared.rail_is_vertical(record.variant)
  local area = vertical and { { p.x - 0.5, p.y - 3 }, { p.x + 0.5, p.y + 3 } }
    or { { p.x - 3, p.y - 0.5 }, { p.x + 3, p.y + 0.5 } }
  for _, wagon in pairs(station.surface.find_entities_filtered({ name = wagon_names, area = area })) do
    local wp = wagon.position
    local along = vertical and math.abs(wp.y - p.y) or math.abs(wp.x - p.x)
    local across = vertical and math.abs(wp.x - p.x) or math.abs(wp.y - p.y)
    local quarter = wagon.orientation * 4
    local on_axis = math.abs(quarter - math.floor(quarter + 0.5)) < 0.02
    local wagon_vertical = math.floor(quarter + 0.5) % 2 == 0
    if on_axis and wagon_vertical == vertical and across < 0.3 and along <= 3
      and wagon.train and wagon.train.speed == 0 then
      return wagon
    end
  end
end

local function move_items(from, to, budget, allowed)
  for _, item in pairs(from.get_contents()) do
    if budget <= 0 then return end
    if not allowed or allowed[item.name] then
      local inserted = to.insert({ name = item.name, count = math.min(item.count, budget), quality = item.quality })
      if inserted > 0 then
        from.remove({ name = item.name, count = inserted, quality = item.quality })
        budget = budget - inserted
      end
    end
  end
end

local function transfer_pass()
  local budget = math.max(1, math.floor(settings.global["bulk-wagons-transfer-rate"].value * TRANSFER_PERIOD / 60))
  for unit_number, record in pairs(storage.stations) do
    if not record.entity.valid then
      remove_station(unit_number)
    elseif record.base ~= shared.belt_loader then
      local wagon = find_wagon(record)
      if wagon then
        local station_inventory = record.entity.get_inventory(defines.inventory.chest)
        local wagon_inventory = wagon.get_inventory(defines.inventory.cargo_wagon)
        if record.base == shared.pit then
          move_items(wagon_inventory, station_inventory, budget, nil)
        else
          move_items(station_inventory, wagon_inventory, budget, storage.allowed)
        end
      end
    end
  end
end

--------------------------------------------------------------------------------
-- Build / remove events

local function on_built(event)
  local entity = event.entity or event.destination
  if not (entity and entity.valid) then return end
  if PORT_NAMES[entity.name] then
    -- Ports are owned by their station; a cloned port is replaced when the station is registered.
    if event.destination then entity.destroy() end
    return
  end
  local cloned = event.destination ~= nil
  if is_wagon(entity) then
    if not cloned then entity = fit_wagon(entity) end
    if entity and entity.valid then storage.wagons[entity.unit_number] = entity end
    return
  end
  local info = variant_of[entity.name]
  if not info then return end
  if not cloned then
    entity = fit_station(entity, info, event.name == defines.events.on_built_entity)
    if not (entity and entity.valid) then return end
    info = variant_of[entity.name]
  end
  register_station(entity, info)
end

local function on_removed(event)
  local entity = event.entity
  if not (entity and entity.valid) then return end
  if is_wagon(entity) then
    storage.wagons[entity.unit_number] = nil
  elseif variant_of[entity.name] then
    remove_station(entity.unit_number, event.buffer)
  end
end

local function on_object_destroyed(event)
  if event.type == defines.target_type.entity and event.useful_id then
    remove_station(event.useful_id)
  end
end

--------------------------------------------------------------------------------
-- Rotating the station in the cursor

local function rotate_cursor(event, step)
  local player = game.get_player(event.player_index)
  if not player then return end
  local stack = player.cursor_stack
  local ghost = player.cursor_ghost
  local name
  if stack and stack.valid_for_read then
    name = stack.name
  elseif ghost then
    name = ghost.name.name
  end
  local info = name and variant_of[name]
  if not info then return end
  local next_name = shared.variant_name(info.base, (info.variant - 1 + step) % shared.variant_count + 1)
  if stack and stack.valid_for_read then
    stack.set_stack({ name = next_name, count = stack.count, quality = stack.quality })
  else
    player.cursor_ghost = { name = next_name, quality = ghost.quality }
  end
end

-- Rotated variants only live in the cursor; anything that lands in the
-- inventory is turned back into the normal item.
local normalizing = false
local function normalize_inventory(event)
  if normalizing then return end
  local player = game.get_player(event.player_index)
  local inventory = player and player.get_main_inventory()
  if not inventory then return end
  normalizing = true
  for _, item in pairs(inventory.get_contents()) do
    local info = variant_of[item.name]
    if info and (info.variant ~= 1 or info.planet ~= shared.default_planet) then
      local removed = inventory.remove({ name = item.name, count = item.count, quality = item.quality })
      local inserted = inventory.insert({ name = info.base, count = removed, quality = item.quality })
      if inserted < removed then
        player.surface.spill_item_stack({
          position = player.position,
          stack = { name = info.base, count = removed - inserted, quality = item.quality },
        })
      end
    end
  end
  normalizing = false
end

--------------------------------------------------------------------------------
-- Keeping non-bulk items out of wagons

local function on_gui_opened(event)
  local entity = event.entity
  if entity and entity.valid and is_wagon(entity) then
    storage.open_wagons[event.player_index] = entity
  end
end

local function on_gui_closed(event)
  local entity = event.entity
  storage.open_wagons[event.player_index] = nil
  if entity and entity.valid and is_wagon(entity) then
    purge_wagon(entity, game.get_player(event.player_index))
  end
end

local function on_fast_transferred(event)
  local entity = event.entity
  if event.from_player and entity and entity.valid and is_wagon(entity) then
    purge_wagon(entity, game.get_player(event.player_index))
  end
end

local function check_open_wagons()
  for player_index, wagon in pairs(storage.open_wagons) do
    if wagon.valid then
      purge_wagon(wagon, game.get_player(player_index))
    else
      storage.open_wagons[player_index] = nil
    end
  end
end

local function sweep_wagons()
  for unit_number, wagon in pairs(storage.wagons) do
    if wagon.valid then
      purge_wagon(wagon, nil)
    else
      storage.wagons[unit_number] = nil
    end
  end
end

--------------------------------------------------------------------------------
-- Setup

local function collect_wagon_names()
  for name in pairs(wagon_planet) do
    if exists(name) then wagon_names[#wagon_names + 1] = name end
  end
end

local function rescan()
  local names = {}
  for name in pairs(variant_of) do
    if exists(name) then names[#names + 1] = name end
  end
  for _, surface in pairs(game.surfaces) do
    for _, wagon in pairs(surface.find_entities_filtered({ name = wagon_names })) do
      storage.wagons[wagon.unit_number] = wagon
    end
    for _, station in pairs(surface.find_entities_filtered({ name = names })) do
      register_station(station, variant_of[station.name])
    end
  end
end

script.on_init(function()
  collect_wagon_names()
  init_storage()
  build_allowed()
end)

script.on_load(collect_wagon_names)

script.on_configuration_changed(function()
  init_storage()
  build_allowed()
  rescan()
end)

script.on_event(defines.events.on_runtime_mod_setting_changed, function(event)
  if event.setting == "bulk-wagons-extra-items" then build_allowed() end
end)

local built_events = {
  defines.events.on_built_entity,
  defines.events.on_robot_built_entity,
  defines.events.on_space_platform_built_entity,
  defines.events.script_raised_built,
  defines.events.script_raised_revive,
  defines.events.on_entity_cloned,
}
script.on_event(built_events, on_built)

local removed_events = {
  defines.events.on_player_mined_entity,
  defines.events.on_robot_mined_entity,
  defines.events.on_space_platform_mined_entity,
  defines.events.on_entity_died,
  defines.events.script_raised_destroy,
}
script.on_event(removed_events, on_removed)
script.on_event(defines.events.on_object_destroyed, on_object_destroyed)

script.on_event("bulk-wagons-rotate", function(event) rotate_cursor(event, 1) end)
script.on_event("bulk-wagons-reverse-rotate", function(event) rotate_cursor(event, -1) end)
script.on_event(defines.events.on_player_main_inventory_changed, normalize_inventory)

script.on_event(defines.events.on_gui_opened, on_gui_opened)
script.on_event(defines.events.on_gui_closed, on_gui_closed)
script.on_event(defines.events.on_player_fast_transferred, on_fast_transferred)

script.on_nth_tick(TRANSFER_PERIOD, transfer_pass)
script.on_nth_tick(SWEEP_PERIOD, sweep_wagons)
script.on_nth_tick(OPEN_GUI_PERIOD, check_open_wagons)

remote.add_interface("bulk-wagons", {
  -- Lets other mods declare their items as bulk goods.
  add_allowed_items = function(names)
    for _, name in pairs(names) do storage.remote_allowed[name] = true end
    build_allowed()
  end,
  is_allowed = function(name)
    return storage.allowed[name] == true
  end,
  -- Turns and centres a station on the rail below it, as a hand-built one would be.
  align_station = function(entity)
    local info = entity and entity.valid and variant_of[entity.name]
    if not info then return entity end
    entity = fit_station(entity, info, true)
    if entity and entity.valid then register_station(entity, variant_of[entity.name]) end
    return entity
  end,
})
