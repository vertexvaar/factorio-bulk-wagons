local shared = require("shared")
local circuit = require("circuit")
local colors = require("colors")
local markers = require("markers")

local TRANSFER_PERIOD = 12 -- ticks between transfer passes (small steps, so goods flow steadily)
local SWEEP_PERIOD = 60 -- ticks between checks for forbidden items in wagons
local OPEN_GUI_PERIOD = 10 -- ticks between checks of wagons a player has open
local PORT_NAMES = { [shared.port] = true, [shared.rail_port] = true }
local STORE_NAMES = {}
for _, name in pairs(shared.station_window_names()) do
  STORE_NAMES[name] = true
end

-- Items that are bulk goods but not (or not always) a mined resource.
local EXTRA_BULK_ITEMS = {
  "ice",
  "carbon",
  "sulfur",
  "uranium-235",
  "uranium-238",
  "holmium-ore",
  "tree-seed",
  "jellynut-seed",
  "yumako-seed",
}

local planet_set = {}
for _, planet in pairs(shared.planets) do
  planet_set[planet] = true
end

-- entity/item name -> { base = station base name, variant = 1..4, planet = name }.
-- Planet variants only exist with Space Age; exists() tells which are defined.
local variant_of = {}
-- entity name -> planet, for every bulk wagon prototype name
local wagon_planet = {}
for _, planet in pairs(shared.planets) do
  for _, base in pairs(shared.all_bases) do
    for variant = 1, shared.variant_count_of(base) do
      variant_of[shared.variant_name(base, variant, planet)] = { base = base, variant = variant, planet = planet }
    end
  end
  wagon_planet[shared.wagon_name(planet)] = planet
end
local wagon_names = {} -- defined wagon prototypes, filled on init/load

local function exists(name) return prototypes.entity[name] ~= nil end

local function is_wagon(entity) return wagon_planet[entity.name] ~= nil end

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
  storage.store_owner = storage.store_owner or {} -- store unit_number -> station unit_number
  storage.pending_wires = storage.pending_wires or {} -- position key -> wires waiting for an entity
  storage.cargo = storage.cargo or {} -- wagon unit_number -> { wagon, render, frame, item }
  storage.drained = storage.drained or {} -- wagon unit_number -> tick a pit last took goods out
  storage.ghost_checks = storage.ghost_checks or {} -- station ghosts placed by hand, checked next tick
  -- the data stage reports which generated graphics exist
  local info = prototypes.mod_data["bulk-wagons-graphics"]
  storage.has_load_animation = info ~= nil and info.data.load == true
  storage.has_extend = info and info.data.extend or {} -- "<key>-<variant>" -> true
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
  defines.direction.east,
  defines.direction.south,
  defines.direction.west,
  defines.direction.north,
}
local OPPOSITE = {
  [defines.direction.east] = defines.direction.west,
  [defines.direction.west] = defines.direction.east,
  [defines.direction.north] = defines.direction.south,
  [defines.direction.south] = defines.direction.north,
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

local HAS_STORE = { [shared.pit] = true, [shared.loader] = true, [shared.belt_loader] = true, [shared.bunker] = true,
  [shared.silo] = true }
-- stations that take goods out of the wagon
local UNLOADS = { [shared.pit] = true, [shared.bunker] = true }
local SPRITE_KEY = { [shared.pit] = "e1", [shared.belt_loader] = "b3", [shared.loader] = "b1", [shared.bunker] = "bunker",
  [shared.silo] = "silo" }
-- the bunker's moving parts stand beside the track, under the wagons
local OVERLAY_LAYER = { e1 = "rail-chain-signal-metal", b3 = "higher-object-under", b1 = "higher-object-under",
  bunker = "lower-object-above-shadow", silo = "higher-object-under" }
local CONNECTORS = {}
for _, def in pairs(shared.connectors) do
  CONNECTORS[def.name] = true
end
-- just above the station picture ("lower-object-above-shadow")
local BASE_MASK_LAYER = "lower-object-overlay"
local ANIMATION_SPEED = 0.25
local EXTEND_TICKS = 32 -- 8 frames at a quarter frame per tick

-- Name and position of a station's hidden inventory (the belt loader's is a small
-- control box without usable slots, see shared.control_name).
local function store_spec(entity, info)
  local name_of = info.base == shared.belt_loader and function(planet) return shared.control_name(info.variant, planet) end
    or function(planet) return shared.store_name(info.base, info.variant, planet) end
  -- without Space Age only the Nauvis one exists
  local name = exists(name_of(info.planet)) and name_of(info.planet) or name_of(nil)
  if info.base == shared.belt_loader then
    local off = shared.rotate(shared.control_offset, info.variant)
    return name, { entity.position.x + off[1], entity.position.y + off[2] }
  end
  return name, entity.position
end

local function create_store(entity, info)
  local name, position = store_spec(entity, info)
  local store = entity.surface.find_entities_filtered({ name = name, position = position, radius = 0.1, limit = 1 })[1]
    or entity.surface.create_entity({
      name = name,
      position = position,
      force = entity.force,
      create_build_effect_smoke = false,
    })
  if store then
    store.destructible = false
    storage.store_owner[store.unit_number] = entity.unit_number

  end
  return store
end

local function destroy(record, key)
  if record[key] and record[key].valid then record[key].destroy() end
  record[key] = nil
end

-- Draws a still sprite or (with animated) a running animation on the station.
local function draw(record, name, layer, tint, animated)
  local params = { surface = record.entity.surface, target = record.entity, render_layer = layer, tint = tint }
  local ok, object
  if not animated then
    if not helpers.is_valid_sprite_path(name) then return end
    params.sprite = name
    ok, object = pcall(rendering.draw_sprite, params)
  else
    params.animation = name
    params.animation_speed = ANIMATION_SPEED
    -- start on the first frame now
    params.animation_offset = -(game.tick * ANIMATION_SPEED)
    ok, object = pcall(rendering.draw_animation, params)
  end
  if ok then return object end
end

-- Draws the parts that belong above trains (or the running animation of the pit),
-- and their colour mask on top.
local function draw_overlay(record, kind)
  destroy(record, "overlay")
  destroy(record, "mask")
  local key = SPRITE_KEY[record.base]
  local name = "bulk-" .. key .. "-" .. record.variant .. "-" .. kind
  local planet = variant_of[record.entity.name].planet
  local tint = planet ~= shared.default_planet and shared.placeholder_tint[planet] or nil
  record.overlay = draw(record, name, OVERLAY_LAYER[key], tint, kind ~= "idle")
  if record.overlay then
    record.mask = draw(record, name .. "_mask", OVERLAY_LAYER[key], colors.get(record), kind ~= "idle")
  end
end

-- Station states: "idle" (no wagon, chute up), "extend" (lowering onto a wagon that
-- arrived, played once), "docked" (resting on the wagon), "work" (docked and moving
-- goods: belts run) and "retract" (lifting again after the train left, played once).
local function has_extend(record) return storage.has_extend[SPRITE_KEY[record.base] .. "-" .. record.variant] end

local function show(record, state)
  record.state = state
  record.switch_at = nil
  if (state == "extend" or state == "retract") and has_extend(record) then
    record.switch_at = game.tick + EXTEND_TICKS
  elseif state == "extend" then
    state = "docked"
  elseif state == "retract" then
    state = "idle"
  end
  record.state = state
  -- without the lowering animation there is no docked picture either
  draw_overlay(record, state == "docked" and not has_extend(record) and "idle" or state)
end

local WORK_GRACE = 3 -- transfer passes without goods before the belts stop

-- Moves the station towards what the wagon below needs.
local function update_state(record, docked, working)
  if working then
    record.slack = 0
  else
    record.slack = (record.slack or 0) + 1
    working = record.state == "work" and record.slack < WORK_GRACE
  end
  record.working = working
  local state = record.state
  if docked then
    if state == "idle" or state == "retract" then
      show(record, "extend")
    elseif state == "docked" or state == "work" then
      local want = working and "work" or "docked"
      if state ~= want then show(record, want) end
    end
  elseif state == "docked" or state == "work" or state == "extend" then
    show(record, "retract")
  end
end

-- (Re)draws the colour mask over the station picture and the overlay of the current state.
local function draw_station(record)
  destroy(record, "base_mask")
  local name = "bulk-" .. SPRITE_KEY[record.base] .. "-" .. record.variant .. "-base_mask"
  record.base_mask = draw(record, name, BASE_MASK_LAYER, colors.get(record), false)
  -- a transition in progress is cut short
  local state = record.state
  if state == "extend" then state = "docked" end
  if state == "retract" or not state then state = "idle" end
  show(record, state)
end

-- Hidden blockers over the solid parts of a bunker or silo (see shared.solid_parts).
local function create_blockers(entity, info)
  local blockers = {}
  for _, part in pairs(shared.solid_parts[info.base] or {}) do
    local offset = shared.rotate(part[1], info.variant)
    local w, h = part[2][1], part[2][2]
    if not shared.rail_is_vertical(info.variant) then w, h = h, w end
    local blocker = entity.surface.create_entity({
      name = shared.blocker_name(w, h),
      position = { entity.position.x + offset[1], entity.position.y + offset[2] },
      force = entity.force,
      create_build_effect_smoke = false,
    })
    if blocker then
      blocker.destructible = false
      blockers[#blockers + 1] = blocker
    end
  end
  return blockers
end

local function register_station(entity, info)
  local record = storage.stations[entity.unit_number]
  local legacy = shared.is_legacy(info.base)
  if record and (legacy and record.port and record.port.valid or not legacy and record.store and record.store.valid) then
    return
  end
  record = { entity = entity, base = info.base, variant = info.variant }
  if HAS_STORE[info.base] then record.store = create_store(entity, info) end
  if legacy then
    record.port = create_port(entity, info)
  else
    record.blockers = create_blockers(entity, info)
  end
  storage.stations[entity.unit_number] = record
  script.register_on_object_destroyed(entity)
  circuit.attach(record)
  if record.store then circuit.on_any_built(record.store) end
  draw_station(record)
  return record
end

-- Removes a station and its helpers. With a buffer (mined), the contents of its
-- inventory and belt port go there. `removing` is the entity an event is already
-- removing; it is left alone.
local function remove_station(unit_number, buffer, removing)
  local record = storage.stations[unit_number]
  if not record then return end
  storage.stations[unit_number] = nil
  for _, key in pairs({ "overlay", "mask", "base_mask" }) do
    destroy(record, key)
  end
  circuit.detach(record)
  local store = record.store
  if store and store.valid and store ~= removing then
    storage.store_owner[store.unit_number] = nil
    if buffer then
      local inventory = store.get_inventory(defines.inventory.chest)
      for _, item in pairs(inventory.get_contents()) do
        buffer.insert({ name = item.name, count = item.count, quality = item.quality })
      end
    end
    store.destroy()
  end
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
  for _, blocker in pairs(record.blockers or {}) do
    if blocker.valid then blocker.destroy() end
  end
  if record.entity.valid and record.entity ~= removing then record.entity.destroy() end
end

local function rail_axis(direction)
  if direction == defines.direction.north or direction == defines.direction.south then return true end
  if direction == defines.direction.east or direction == defines.direction.west then return false end
end

-- The straight ground rail under the centre of a station (within a tile), and whether
-- it runs north-south. With ghosts, a rail ghost counts too.
local function straight_rail_at(surface, position, ghosts)
  local area = { { position.x - 1, position.y - 1 }, { position.x + 1, position.y + 1 } }
  for _, rail in pairs(surface.find_entities_filtered({ type = "straight-rail", area = area })) do
    local vertical = rail_axis(rail.direction)
    if vertical ~= nil then return rail, vertical end
  end
  if ghosts then
    for _, ghost in pairs(surface.find_entities_filtered({ ghost_type = "straight-rail", area = area })) do
      local vertical = rail_axis(ghost.direction)
      if vertical ~= nil then return ghost, vertical end
    end
  end
end

-- Replaces a freshly built entity by another prototype. Returns the new entity,
-- or the original one again if the replacement does not fit.
local function replace(entity, params)
  local surface = entity.surface
  local original = {
    name = entity.name,
    position = entity.position,
    direction = params.direction,
    force = entity.force,
    quality = entity.quality,
    color = params.color,
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
-- hand (align) also turns and centres itself across the rail below it; along the
-- rail it keeps the 1-tile grid, like a rail signal, so three stations line up under
-- every wagon of a train.
-- A bunker or silo within this many tiles of a wagon slot of a train stop snaps onto it.
local SLOT_SNAP = 3

-- Where a station placed at position belongs: its variant turned to the rail below it
-- and its position centred on that rail and snapped along it. ghosts: a rail ghost
-- counts too (for station ghosts placed by hand).
local function aligned(surface, position, info, ghosts)
  local variant = info.variant
  local target = { position.x, position.y }
  local rail, vertical = straight_rail_at(surface, position, ghosts)
  if rail then
    if vertical ~= shared.rail_is_vertical(variant) then variant = variant % shared.variant_count_of(info.base) + 1 end
    local along = math.floor((vertical and position.y or position.x) + 0.5)
    if not shared.is_legacy(info.base) then
      local best
      for _, slot in pairs(shared.wagon_slots(surface, position, vertical, shared.wagon_pitch * shared.slot_count)) do
        local d = math.abs(slot - along)
        if d <= SLOT_SNAP and (not best or d < math.abs(best - along)) then best = slot end
      end
      along = best or along
    end
    if vertical then
      target = { rail.position.x, along }
    else
      target = { along, rail.position.y }
    end
  end
  return variant, target
end

local function fit_station(entity, info, align)
  local variant, position = info.variant, { entity.position.x, entity.position.y }
  if align then variant, position = aligned(entity.surface, entity.position, info, false) end
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
    if
      on_axis
      and wagon_vertical == vertical
      and across < 0.3
      and along <= (shared.is_legacy(record.base) and 3 or 1.5)
      and wagon.train
      and wagon.train.speed == 0
    then
      return wagon
    end
  end
end

-- Moves up to budget items; returns how many moved.
local function move_items(from, to, budget, allowed)
  local moved = 0
  for _, item in pairs(from.get_contents()) do
    if moved >= budget then break end
    if not allowed or allowed[item.name] then
      local count = math.min(item.count, budget - moved)
      local inserted = to.insert({ name = item.name, count = count, quality = item.quality })
      if inserted > 0 then
        from.remove({ name = item.name, count = inserted, quality = item.quality })
        moved = moved + inserted
      end
    end
  end
  return moved
end

local function port_busy(record)
  local port = record.port
  if not (port and port.valid) then return false end
  for i = 1, port.get_max_transport_line_index() do
    if #port.get_transport_line(i) > 0 then return true end
  end
  return false
end

local function transfer_pass()
  local budget = math.max(1, math.floor(settings.global["bulk-wagons-transfer-rate"].value * TRANSFER_PERIOD / 60))
  for unit_number, record in pairs(storage.stations) do
    if not record.entity.valid then
      remove_station(unit_number)
    else
      local wagon = find_wagon(record)
      local store = record.store and record.store.valid and record.store.get_inventory(defines.inventory.chest)
      local enabled = circuit.enabled(record)
      circuit.update(record, wagon)
      local working = false
      if record.base == shared.belt_loader then
        -- the port loads the wagon on its own; a disabled station stops its port
        if record.port and record.port.valid then record.port.disabled_by_script = not enabled end
        working = enabled and wagon ~= nil and port_busy(record)
      elseif enabled and store and wagon then
        local wagon_inventory = wagon.get_inventory(defines.inventory.cargo_wagon)
        local moved
        if UNLOADS[record.base] then
          moved = move_items(wagon_inventory, store, budget, nil)
          if moved > 0 then storage.drained[wagon.unit_number] = game.tick end
        else
          moved = move_items(store, wagon_inventory, budget, storage.allowed)
        end
        -- the pit's extraction belt runs on while it has goods
        working = moved > 0 or record.base == shared.pit and not store.is_empty()
      end
      update_state(record, wagon ~= nil, working)
    end
  end
end

local function finish_transitions()
  for _, record in pairs(storage.stations) do
    if record.switch_at and game.tick >= record.switch_at and record.entity.valid then
      if record.state == "extend" then
        show(record, record.working and "work" or "docked")
      else
        show(record, "idle")
      end
    end
  end
end

--------------------------------------------------------------------------------
-- Build / remove events

-- Stations only go onto straight rails: one built elsewhere is taken back.
local function refuse(entity, info, player, message)
  local surface, position, quality = entity.surface, entity.position, entity.quality.name
  if player and player.valid then
    player.create_local_flying_text({ text = { message or "bulk-wagons.needs-rail" }, position = position })
    player.play_sound({ path = "utility/cannot_build" })
  end
  entity.destroy()
  local stack = { name = info.base, count = 1, quality = quality }
  local inserted = player and player.valid and player.insert(stack) or 0
  if inserted == 0 then surface.spill_item_stack({ position = position, stack = stack }) end
end

-- Whether a connector docks onto a long side of a bunker or silo (the sides along
-- the track; the ends belong to the track).
local function docked_connector(connector)
  local container = connector.loader_container
  local record = container and storage.stations[storage.store_owner[container.unit_number] or 0]
  if not (record and record.entity.valid and not shared.is_legacy(record.base)) then return false end
  local p, c = record.entity.position, connector.position
  local across = shared.rail_is_vertical(record.variant) and math.abs(c.x - p.x) or math.abs(c.y - p.y)
  return across > shared.station_half
end

-- Moves a station ghost to where a hand-built station would go (see aligned). Returns
-- the ghost now standing there; one that does not fit there stays where it is.
local function snap_ghost(ghost)
  local info = variant_of[ghost.ghost_name]
  local variant, position = aligned(ghost.surface, ghost.position, info, true)
  local name = shared.variant_name(info.base, variant)
  if name == ghost.ghost_name and position[1] == ghost.position.x and position[2] == ghost.position.y then return ghost end
  local surface, force, quality, tags = ghost.surface, ghost.force, ghost.quality, ghost.tags
  local original = { name = "entity-ghost", inner_name = ghost.ghost_name, position = ghost.position, force = force,
    quality = quality, tags = tags }
  ghost.destroy()
  local spec = { name = "entity-ghost", inner_name = name, position = position, force = force, quality = quality, tags = tags }
  local moved = surface.can_place_entity({ name = name, position = position, force = force,
    build_check_type = defines.build_check_type.manual_ghost }) and surface.create_entity(spec)
  return moved or surface.create_entity(original)
end

-- Ghosts of stations placed off the rails disappear again.
local function check_ghosts()
  if not next(storage.ghost_checks) then return end
  for _, check in pairs(storage.ghost_checks) do
    local ghost = check.ghost
    if ghost.valid and not straight_rail_at(ghost.surface, ghost.position, true) then
      local player = game.get_player(check.player_index)
      if player then player.create_local_flying_text({ text = { "bulk-wagons.needs-rail" }, position = ghost.position }) end
      ghost.destroy()
    elseif ghost.valid and check.snap then
      snap_ghost(ghost)
    end
  end
  storage.ghost_checks = {}
end

local function on_built(event)
  local entity = event.entity or event.destination
  if not (entity and entity.valid) then return end
  circuit.on_any_built(entity)
  if PORT_NAMES[entity.name] or STORE_NAMES[entity.name] or entity.name == shared.signals then
    -- Owned by their station; a cloned one is replaced when the station is registered.
    if event.destination then entity.destroy() end
    return
  end
  local cloned = event.destination ~= nil
  if CONNECTORS[entity.name] then
    -- a connector built by hand must dock onto the long side of a bunker or silo
    if event.name == defines.events.on_built_entity and not docked_connector(entity) then
      refuse(entity, { base = entity.name }, game.get_player(event.player_index), "bulk-wagons.needs-station")
    end
    return
  end
  if is_wagon(entity) then
    if not cloned then entity = fit_wagon(entity) end
    if entity and entity.valid then storage.wagons[entity.unit_number] = entity end
    return
  end
  if entity.name == "entity-ghost" and variant_of[entity.ghost_name] and event.name == defines.events.on_built_entity then
    -- checked a tick later, when the rails of the same blueprint exist as well. A ghost
    -- placed from the item (not from a blueprint, which keeps its layout) also snaps into
    -- place like a station built by hand, so robots build it there.
    local stack = event.stack
    local from_blueprint = event.record ~= nil
      or stack and stack.valid_for_read and (stack.is_blueprint or stack.is_blueprint_book)
    storage.ghost_checks[#storage.ghost_checks + 1] =
      { ghost = entity, player_index = event.player_index, snap = not from_blueprint }
    return
  end
  local info = variant_of[entity.name]
  if not info then return end
  local by_hand = event.name == defines.events.on_built_entity
  if by_hand and not straight_rail_at(entity.surface, entity.position) then
    refuse(entity, info, game.get_player(event.player_index))
    return
  end
  if not cloned then
    entity = fit_station(entity, info, by_hand)
    if not (entity and entity.valid) then return end
    info = variant_of[entity.name]
  end
  local record = register_station(entity, info)
  if record and event.tags then
    circuit.from_tags(record, event.tags)
    colors.apply(record)
  end
end

local function on_removed(event)
  local entity = event.entity
  if not (entity and entity.valid) then return end
  if is_wagon(entity) then
    storage.wagons[entity.unit_number] = nil
  elseif variant_of[entity.name] then
    remove_station(entity.unit_number, event.buffer, entity)
  elseif STORE_NAMES[entity.name] then
    -- the player mined the station through its inventory; the engine hands out the contents
    local owner = storage.store_owner[entity.unit_number]
    storage.store_owner[entity.unit_number] = nil
    if owner then remove_station(owner, event.buffer, entity) end
  end
end

local function on_object_destroyed(event)
  if event.type == defines.target_type.entity and event.useful_id then remove_station(event.useful_id) end
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
  local count = shared.variant_count_of(info.base)
  local next_name = shared.variant_name(info.base, (info.variant - 1 + step) % count + 1)
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
  elseif entity and entity.valid and STORE_NAMES[entity.name] then
    local record = storage.stations[storage.store_owner[entity.unit_number] or 0]
    if record then
      local player = game.get_player(event.player_index)
      circuit.open_panel(player, record)
      -- only graphics with colour masks can show a station colour
      local mask = "bulk-" .. SPRITE_KEY[record.base] .. "-" .. record.variant .. "-idle_mask"
      if helpers.is_valid_sprite_path(mask) then colors.open_panel(player, record) end
    end
  end
end

local function on_gui_closed(event)
  local entity = event.entity
  storage.open_wagons[event.player_index] = nil
  if entity and entity.valid and STORE_NAMES[entity.name] then
    circuit.close_panel(game.get_player(event.player_index))
    colors.close_panel(game.get_player(event.player_index))
  end
  if entity and entity.valid and is_wagon(entity) then purge_wagon(entity, game.get_player(event.player_index)) end
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

--------------------------------------------------------------------------------
-- Visible cargo: heaps in the wagon, tinted like the ore it carries

local LOAD_ANIMATION = "bulk-wagon-load-" -- .. fill level 1 to 4
local DRAIN_ANIMATION = "bulk-wagon-drain-" -- the same while a pit unloads: flaps open, craters over them
local LOAD_LEVELS = 4
local LOAD_FRAMES = 128 -- frame i shows orientation i / 256, back equals front
local CARGO_COLORS = {
  ["iron-ore"] = { 0.55, 0.62, 0.75 },
  ["copper-ore"] = { 0.88, 0.5, 0.3 },
  ["coal"] = { 0.22, 0.22, 0.22 },
  ["stone"] = { 0.82, 0.72, 0.56 },
  ["uranium-ore"] = { 0.5, 0.88, 0.35 },
  ["uranium-238"] = { 0.4, 0.7, 0.35 },
  ["uranium-235"] = { 0.3, 1.0, 0.3 },
  ["calcite"] = { 0.93, 0.91, 0.86 },
  ["tungsten-ore"] = { 0.38, 0.35, 0.45 },
  ["scrap"] = { 0.62, 0.56, 0.5 },
  ["ice"] = { 0.82, 0.92, 1.0 },
  ["carbon"] = { 0.16, 0.16, 0.16 },
  ["sulfur"] = { 0.95, 0.85, 0.3 },
  ["holmium-ore"] = { 0.88, 0.55, 0.78 },
  ["tree-seed"] = { 0.6, 0.5, 0.32 },
  ["jellynut-seed"] = { 0.85, 0.45, 0.6 },
  ["yumako-seed"] = { 0.85, 0.35, 0.3 },
}
local DEFAULT_CARGO_COLOR = { 0.6, 0.58, 0.55 }

local function load_frame(wagon) return math.floor(wagon.orientation * 2 * LOAD_FRAMES + 0.5) % LOAD_FRAMES end

-- Shows, updates or removes the cargo heaps of one wagon.
local function update_cargo(wagon)
  if not storage.has_load_animation then return end
  local unit = wagon.unit_number
  local record = storage.cargo[unit]
  local inventory = wagon.get_inventory(defines.inventory.cargo_wagon)
  -- unloading: a pit took goods out since the last sweep
  local drained = storage.drained[unit]
  local draining = drained ~= nil and game.tick - drained <= SWEEP_PERIOD + TRANSFER_PERIOD
  if drained and not draining then storage.drained[unit] = nil end
  if inventory.is_empty() then
    if record then
      if record.render.valid then record.render.destroy() end
      storage.cargo[unit] = nil
    end
    return
  end
  local top, most = nil, 0
  for _, item in pairs(inventory.get_contents()) do
    if item.count > most then
      top, most = item.name, item.count
    end
  end
  local color = CARGO_COLORS[top] or DEFAULT_CARGO_COLOR
  local frame = load_frame(wagon)
  -- fill level from the share of used slots: any goods show at least a quarter
  local used = #inventory - inventory.count_empty_stacks()
  local level = math.max(1, math.min(LOAD_LEVELS, math.ceil(used / #inventory * LOAD_LEVELS)))
  local animation = (draining and DRAIN_ANIMATION or LOAD_ANIMATION) .. level
  if not (record and record.render.valid) then
    record = {
      wagon = wagon,
      render = rendering.draw_animation({
        animation = animation,
        surface = wagon.surface,
        target = wagon,
        render_layer = "cargo-hatch",
        animation_speed = 0,
        animation_offset = frame,
        tint = color,
      }),
      frame = frame,
      item = top,
      animation = animation,
    }
    storage.cargo[unit] = record
    return
  end
  if record.animation ~= animation then
    record.render.animation = animation
    record.animation = animation
  end
  if record.frame ~= frame then
    record.render.animation_offset = frame
    record.frame = frame
  end
  if record.item ~= top then
    record.render.color = color
    record.item = top
  end
end

-- Heaps of moving wagons follow the wagon's turning on curves.
local function turn_cargo()
  for unit, record in pairs(storage.cargo) do
    local wagon = record.wagon
    if not wagon.valid then
      if record.render.valid then record.render.destroy() end
      storage.cargo[unit] = nil
    elseif wagon.train and wagon.train.speed ~= 0 then
      local frame = load_frame(wagon)
      if record.frame ~= frame then
        record.render.animation_offset = frame
        record.frame = frame
      end
    end
  end
end

local function sweep_wagons()
  for unit_number, wagon in pairs(storage.wagons) do
    if wagon.valid then
      purge_wagon(wagon, nil)
      update_cargo(wagon)
    else
      storage.wagons[unit_number] = nil
      storage.drained[unit_number] = nil
    end
  end
end

--------------------------------------------------------------------------------
-- Setup

local function collect_wagon_names()
  for i = #wagon_names, 1, -1 do
    wagon_names[i] = nil
  end
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
      -- wagons from 0.2.0 were coloured at full alpha; the masks are made for 0.5
      local c = wagon.color
      if c and c.a and c.a > 0.5 then wagon.color = { r = c.r, g = c.g, b = c.b, a = 0.5 } end
    end
    for _, station in pairs(surface.find_entities_filtered({ name = names })) do
      local info = variant_of[station.name]
      local record = register_station(station, info) or storage.stations[station.unit_number]
      -- stations from 0.1.0: the belt loader gains its control box, all gain the signal combinator
      if record and not (record.store and record.store.valid) then record.store = create_store(station, info) end
      if record then
        circuit.attach(record)
        -- stations from 0.2.0 gain their colour masks, and graphics may have changed
        draw_station(record)
      end
    end
  end
end

--------------------------------------------------------------------------------
-- 0.4.0: the three-per-wagon stations become one bunker or silo per wagon

local MIGRATE_SNAP = 3.5 -- how far a station may sit from a wagon slot and still count as on it

local function contents_of(record)
  local items = {}
  local store = record.store
  if store and store.valid and store.get_inventory(defines.inventory.chest) then
    for _, item in pairs(store.get_inventory(defines.inventory.chest).get_contents()) do
      items[#items + 1] = item
    end
  end
  local port = record.port
  if port and port.valid then
    for i = 1, port.get_max_transport_line_index() do
      for _, item in pairs(port.get_transport_line(i).get_contents()) do
        items[#items + 1] = item
      end
    end
  end
  return items
end

-- Groups the legacy stations by the wagon they serve: by the wagon slot of a nearby
-- train stop, otherwise by their spacing (up to three stations side by side).
local function inside(position, area)
  return not area or position.x >= area[1][1] and position.x <= area[2][1] and position.y >= area[1][2] and position.y <= area[2][2]
end

local function legacy_groups(area)
  local lines = {}
  for unit, record in pairs(storage.stations) do
    if shared.is_legacy(record.base) and record.entity.valid and inside(record.entity.position, area) then
      local e = record.entity
      local vertical = shared.rail_is_vertical(record.variant)
      local across = vertical and e.position.x or e.position.y
      local key = e.surface.index .. (vertical and "v" or "h") .. across
      lines[key] = lines[key] or { surface = e.surface, vertical = vertical, across = across, records = {} }
      table.insert(lines[key].records, { unit = unit, record = record, along = vertical and e.position.y or e.position.x })
    end
  end
  local groups = {}
  for _, line in pairs(lines) do
    table.sort(line.records, function(a, b) return a.along < b.along end)
    local by_slot, loose = {}, {}
    for _, entry in pairs(line.records) do
      local position = entry.record.entity.position
      local best
      for _, slot in pairs(shared.wagon_slots(line.surface, position, line.vertical, shared.wagon_pitch * shared.slot_count)) do
        if math.abs(slot - entry.along) <= MIGRATE_SNAP and (not best or math.abs(slot - entry.along) < math.abs(best - entry.along)) then
          best = slot
        end
      end
      if best then
        by_slot[best] = by_slot[best] or {}
        table.insert(by_slot[best], entry)
      else
        loose[#loose + 1] = entry
      end
    end
    for slot, entries in pairs(by_slot) do
      groups[#groups + 1] = { line = line, along = slot, entries = entries }
    end
    local current
    for _, entry in ipairs(loose) do
      if current and entry.along - current.entries[1].along <= 4 then
        table.insert(current.entries, entry)
      else
        current = { line = line, entries = { entry } }
        groups[#groups + 1] = current
      end
    end
  end
  for _, group in pairs(groups) do
    if not group.along then
      group.along = math.floor((group.entries[1].along + group.entries[#group.entries].along) / 2 + 0.5)
    end
  end
  return groups
end

local function migrate_group(group)
  local line = group.line
  local surface = line.surface
  local unloading = 0
  for _, entry in pairs(group.entries) do
    if UNLOADS[entry.record.base] then unloading = unloading + 1 end
  end
  local base = unloading * 2 >= #group.entries and shared.bunker or shared.silo
  local first = group.entries[1].record
  local force, quality = first.entity.force, first.entity.quality
  local settings, color = first.settings, first.color
  local saved, items = {}, {}
  for _, entry in pairs(group.entries) do
    local e = entry.record.entity
    saved[#saved + 1] = { name = e.name, position = e.position, record = entry.record }
    for _, item in pairs(contents_of(entry.record)) do
      items[#items + 1] = item
    end
    remove_station(entry.unit)
  end
  local position = line.vertical and { line.across, group.along } or { group.along, line.across }
  local name = shared.variant_name(base, line.vertical and 1 or 2, planet_of(surface))
  if not exists(name) then name = shared.variant_name(base, line.vertical and 1 or 2) end
  local spec = { name = name, position = position, force = force, quality = quality, create_build_effect_smoke = false }
  local entity = surface.can_place_entity(spec) and surface.create_entity(spec)
  local targets = {}
  if entity then
    local record = register_station(entity, variant_of[entity.name])
    if record then
      record.settings, record.color = settings, color
      draw_station(record)
      targets[1] = record
    end
  else
    -- no room: the old stations come back and the spot is marked on the map
    for _, old in pairs(saved) do
      local e = surface.create_entity({ name = old.name, position = old.position, force = force, quality = quality,
        create_build_effect_smoke = false })
      if e then
        local record = register_station(e, variant_of[e.name])
        if record then
          record.settings, record.color = old.record.settings, old.record.color
          draw_station(record)
          targets[#targets + 1] = record
        end
      end
    end
    force.add_chart_tag(surface, { position = position, text = "Bulk Wagons: no room", icon = { type = "item", name = base } })
    log("bulk-wagons: no room for a " .. base .. " at " .. serpent.line(position))
  end
  -- the goods go back into the new (or restored) inventories; what does not fit is spilled
  for _, item in pairs(items) do
    local left = item.count
    for _, record in pairs(targets) do
      local store = record.store
      local inventory = store and store.valid and store.get_inventory(defines.inventory.chest)
      if inventory and left > 0 then
        left = left - inventory.insert({ name = item.name, count = left, quality = item.quality })
      end
    end
    if left > 0 then
      surface.spill_item_stack({ position = position, stack = { name = item.name, count = left, quality = item.quality },
        enable_looted = true, force = force, allow_belts = false })
    end
  end
  return entity ~= nil
end

-- 0.4.0 made bunker and silo only as big as one old station, so the update spilled
-- most goods next to them. 0.4.1 triples their inventory and takes the spilled bulk
-- goods lying around each bunker and silo back in.
local RECOVER_RADIUS = 16

local function recover_spilled(area)
  if storage.recovered_041 and not area then return end
  storage.recovered_041 = true
  local recovered = 0
  for _, record in pairs(storage.stations) do
    local e, store = record.entity, record.store
    if not shared.is_legacy(record.base) and e.valid and store and store.valid and inside(e.position, area) then
      local inventory = store.get_inventory(defines.inventory.chest)
      local p = e.position
      local spilled = e.surface.find_entities_filtered({
        type = "item-entity",
        area = { { p.x - RECOVER_RADIUS, p.y - RECOVER_RADIUS }, { p.x + RECOVER_RADIUS, p.y + RECOVER_RADIUS } },
      })
      for _, item in pairs(spilled) do
        local stack = item.valid and item.stack
        if stack and stack.valid_for_read and storage.allowed[stack.name] then
          local inserted = inventory.insert(stack)
          recovered = recovered + inserted
          if inserted >= stack.count then
            item.destroy()
          elseif inserted > 0 then
            stack.count = stack.count - inserted
          end
        end
      end
    end
  end
  if recovered > 0 then log("bulk-wagons: took " .. recovered .. " spilled items back into bunkers and silos") end
end

-- area (optional, for tests): only the stations inside it, and also after the update ran
local function migrate_legacy(area)
  if storage.migrated_040 and not area then return end
  storage.migrated_040 = true
  local done, kept = 0, 0
  for _, group in pairs(legacy_groups(area)) do
    if migrate_group(group) then done = done + 1 else kept = kept + 1 end
  end
  if done + kept > 0 then log("bulk-wagons: replaced " .. done .. " wagon stations, kept " .. kept) end
end

script.on_init(function()
  collect_wagon_names()
  init_storage()
  storage.migrated_040 = true
  storage.recovered_041 = true
  build_allowed()
end)

script.on_load(collect_wagon_names)

script.on_configuration_changed(function()
  collect_wagon_names()
  init_storage()
  build_allowed()
  rescan()
  migrate_legacy()
  recover_spilled()
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
script.on_event(built_events, function(event)
  on_built(event)
  markers.redraw_all()
end)

local removed_events = {
  defines.events.on_player_mined_entity,
  defines.events.on_robot_mined_entity,
  defines.events.on_space_platform_mined_entity,
  defines.events.on_entity_died,
  defines.events.script_raised_destroy,
}
script.on_event(removed_events, function(event)
  on_removed(event)
  markers.redraw_all()
end)
script.on_event(defines.events.on_object_destroyed, on_object_destroyed)

script.on_event("bulk-wagons-rotate", function(event) rotate_cursor(event, 1) end)
script.on_event("bulk-wagons-reverse-rotate", function(event) rotate_cursor(event, -1) end)
script.on_event(defines.events.on_player_main_inventory_changed, normalize_inventory)
script.on_event(defines.events.on_player_cursor_stack_changed, function(event) markers.refresh(event.player_index) end)
script.on_event(defines.events.on_player_changed_position, function(event) markers.on_moved(event.player_index) end)
script.on_event(
  { defines.events.on_player_changed_surface, defines.events.on_player_left_game },
  function(event) markers.refresh(event.player_index) end
)

script.on_event(defines.events.on_gui_opened, on_gui_opened)
script.on_event(defines.events.on_gui_closed, on_gui_closed)
script.on_event(defines.events.on_player_fast_transferred, on_fast_transferred)
script.on_event({
  defines.events.on_gui_checked_state_changed,
  defines.events.on_gui_elem_changed,
  defines.events.on_gui_selection_state_changed,
}, circuit.on_gui_changed)
script.on_event(defines.events.on_gui_text_changed, function(event)
  circuit.on_gui_changed(event)
  colors.on_gui_event(event)
end)
script.on_event({ defines.events.on_gui_value_changed, defines.events.on_gui_click }, colors.on_gui_event)

-- Blueprints carry the circuit settings and wires of a station in its tags.
script.on_event(defines.events.on_player_setup_blueprint, function(event)
  local player = game.get_player(event.player_index)
  local blueprint = player.blueprint_to_setup
  if not (blueprint and blueprint.valid_for_read) then blueprint = player.cursor_stack end
  if not (blueprint and blueprint.valid_for_read and blueprint.is_blueprint) then return end
  local mapping = event.mapping.get()
  for index, entity in pairs(mapping) do
    local record = entity.valid and storage.stations[entity.unit_number]
    if record then blueprint.set_blueprint_entity_tag(index, circuit.TAG, circuit.to_tags(record)) end
  end
end)

-- Shift + right/left click copies circuit settings and colour between stations, and
-- the colour of rolling stock or a train stop onto a station.
script.on_event(defines.events.on_entity_settings_pasted, function(event)
  local source, destination = event.source, event.destination
  if not (source.valid and destination.valid) then return end
  local to = storage.stations[storage.store_owner[destination.unit_number] or 0]
  if not to then return end
  local from = storage.stations[storage.store_owner[source.unit_number] or 0]
  if from then
    circuit.copy(from, to)
    colors.apply(to)
  elseif source.color then
    colors.set(to, source.color)
  end
end)

script.on_nth_tick(3600, circuit.expire_pending)

script.on_nth_tick(TRANSFER_PERIOD, transfer_pass)
script.on_nth_tick(8, finish_transitions)
script.on_nth_tick(SWEEP_PERIOD, sweep_wagons)
script.on_nth_tick(2, turn_cargo)
script.on_nth_tick(1, check_ghosts)
script.on_nth_tick(OPEN_GUI_PERIOD, check_open_wagons)

remote.add_interface("bulk-wagons", {
  -- Lets other mods declare their items as bulk goods.
  add_allowed_items = function(names)
    for _, name in pairs(names) do
      storage.remote_allowed[name] = true
    end
    build_allowed()
  end,
  -- The inventory of a station (unloading pit, portal silo), nil for the belt loader.
  get_inventory = function(entity)
    local record = entity and entity.valid and storage.stations[entity.unit_number]
    if record and record.base == shared.belt_loader then return nil end
    local store = record and record.store
    return store and store.valid and store.get_inventory(defines.inventory.chest) or nil
  end,
  -- Station circuit settings (for tests and other mods): get, or replace with a table.
  circuit_settings = function(entity, settings)
    local record = entity and entity.valid and storage.stations[entity.unit_number]
    if not record then return nil end
    if settings then record.settings = settings end
    return circuit.settings(record)
  end,
  -- The entity circuit wires attach to.
  get_store = function(entity)
    local record = entity and entity.valid and storage.stations[entity.unit_number]
    return record and record.store
  end,
  is_allowed = function(name) return storage.allowed[name] == true end,
  -- Station colour: get, or set with a colour (nil resets).
  station_color = function(entity, color, reset)
    local record = entity and entity.valid and storage.stations[entity.unit_number]
    if not record then return nil end
    if color or reset then colors.set(record, color) end
    return colors.get(record)
  end,
  -- Replaces the legacy stations in area by bunkers and silos, as the 0.4.0 update does.
  migrate_legacy = function(area) migrate_legacy(area) end,
  -- Moves a station ghost where a hand-placed ghost snaps to; returns the ghost there.
  snap_ghost = function(ghost) return snap_ghost(ghost) end,
  -- Takes spilled bulk goods around the bunkers and silos in area back in, as the 0.4.1 update does.
  recover_spilled = function(area) recover_spilled(area) end,
  -- Whether a connector docks onto a long side of a bunker or silo.
  connector_docked = function(entity) return docked_connector(entity) end,
  -- Turns and centres a station on the rail below it, as a hand-built one would be.
  align_station = function(entity)
    local info = entity and entity.valid and variant_of[entity.name]
    if not info then return entity end
    entity = fit_station(entity, info, true)
    if entity and entity.valid then register_station(entity, variant_of[entity.name]) end
    return entity
  end,
})
