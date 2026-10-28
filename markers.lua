-- Placement markers: while a player holds a station, every free spot on a straight
-- rail nearby gets the game's rail signal placement indicator; while they hold a
-- connector, every free rim tile of the bunkers and silos nearby (on sides that still
-- take one). The engine draws those
-- only for its own signals, so the script draws the same sprite, for that player only
-- and only while the station is in the cursor, so idle players cost nothing.
local shared = require("shared")

local markers = {}

local RADIUS = 32 -- tiles around the player
local REDRAW_DISTANCE = 8 -- tiles the player moves before the markers are redrawn
local SPRITE = "utility/rail_signal_placement_indicator"

local bases = {}
for _, base in pairs(shared.all_bases) do
  for variant = 1, shared.variant_count_of(base) do
    bases[shared.variant_name(base, variant)] = base
  end
end

local function straight_rail_along(surface, position, vertical)
  local area = { { position.x - 0.5, position.y - 0.5 }, { position.x + 0.5, position.y + 0.5 } }
  for _, rail in pairs(surface.find_entities_filtered({ type = "straight-rail", area = area })) do
    local d = rail.direction
    local rail_vertical = d == defines.direction.north or d == defines.direction.south
    if rail_vertical == vertical and (rail_vertical or d == defines.direction.east or d == defines.direction.west) then
      return true
    end
  end
  return false
end

-- Bunker and silo: an indicator on every free wagon slot of the train stops nearby.
local function slot_positions(surface, area)
  local positions = {}
  for _, stop in pairs(surface.find_entities_filtered({ type = "train-stop", area = area })) do
    local d, s = stop.direction, stop.position
    local vertical = d == defines.direction.north or d == defines.direction.south
    if vertical or d == defines.direction.east or d == defines.direction.west then
      -- the stop stands 2 tiles to the right of its track
      local line
      if d == defines.direction.north then line = { x = s.x - 2, y = s.y }
      elseif d == defines.direction.south then line = { x = s.x + 2, y = s.y }
      elseif d == defines.direction.east then line = { x = s.x, y = s.y - 2 }
      else line = { x = s.x, y = s.y + 2 } end
      for _, along in pairs(shared.wagon_slots(surface, line, vertical, 2.5)) do
        positions[#positions + 1] = { position = vertical and { x = line.x, y = along } or { x = along, y = line.y }, vertical = vertical }
      end
    end
  end
  return positions
end

local connector_items = {}
for _, def in pairs(shared.connectors) do
  connector_items[def.name] = def
end
-- Connector entity names that exist (known once the game runs).
local connector_names
local function existing_connectors()
  if not connector_names then
    connector_names = {}
    for _, name in pairs(shared.connector_names()) do
      if prototypes.entity[name] then connector_names[#connector_names + 1] = name end
    end
  end
  return connector_names
end

-- The connector tier (its shared.connectors entry) in the player's cursor, or nil.
local function held_connector(player)
  local stack = player.cursor_stack
  if stack and stack.valid_for_read then return connector_items[stack.name] end
  local ghost = player.cursor_ghost
  if ghost then return connector_items[ghost.name.name] end
end

-- The station base name in the player's cursor (item or ghost), or nil.
local function held_station(player)
  local stack = player.cursor_stack
  if stack and stack.valid_for_read then return bases[stack.name] end
  local ghost = player.cursor_ghost
  if ghost then return bases[ghost.name.name] end
end

local function clear(index)
  local state = storage.markers and storage.markers[index]
  if not state then return end
  for _, object in pairs(state.objects) do
    if object.valid then object.destroy() end
  end
  storage.markers[index] = nil
end

local function draw_connectors(player, def)
  local surface, p = player.surface, player.position
  local names = existing_connectors()
  local objects = {}
  for _, record in pairs(storage.stations or {}) do
    local e = record.entity
    if e.valid and not shared.is_legacy(record.base) and e.surface == surface
      and math.abs(e.position.x - p.x) <= RADIUS and math.abs(e.position.y - p.y) <= RADIUS
    then
      local open = {}
      for _, side in pairs({ -1, 1 }) do
        open[side] = shared.connectors_on_side(surface, e.position, record.base, record.variant, side, names)
          < shared.connectors_per_side
      end
      for _, tile in pairs(shared.rim_tiles(e.position, record.base, record.variant)) do
        local spec = { name = shared.connector_name(def, record.base), position = tile, force = player.force,
          direction = shared.outward(record.variant, tile.side), build_check_type = defines.build_check_type.manual }
        if open[tile.side] and prototypes.entity[spec.name] and surface.can_place_entity(spec) then
          objects[#objects + 1] = rendering.draw_sprite({
            sprite = SPRITE,
            orientation = shared.rail_is_vertical(record.variant) and 0.25 or 0,
            surface = surface,
            target = { x = tile.x, y = tile.y },
            players = { player },
          })
        end
      end
    end
  end
  return objects
end

local function draw(player, base)
  clear(player.index)
  if type(base) == "table" then
    -- a connector tier
    storage.markers = storage.markers or {}
    storage.markers[player.index] = { objects = draw_connectors(player, base), x = player.position.x,
      y = player.position.y, surface = player.surface.index, base = base }
    return
  end
  local surface = player.surface
  local p = player.position
  local objects = {}
  local area = { { p.x - RADIUS, p.y - RADIUS }, { p.x + RADIUS, p.y + RADIUS } }
  local seen = {}
  if not shared.is_legacy(base) then
    for _, slot in pairs(slot_positions(surface, { { p.x - 2 * RADIUS, p.y - 2 * RADIUS }, { p.x + 2 * RADIUS, p.y + 2 * RADIUS } })) do
      local position, vertical = slot.position, slot.vertical
      local key = position.x .. "," .. position.y
      if not seen[key] and math.abs(position.x - p.x) <= RADIUS and math.abs(position.y - p.y) <= RADIUS then
        seen[key] = true
        local spec = { name = shared.variant_name(base, vertical and 1 or 2), position = position, force = player.force,
          build_check_type = defines.build_check_type.manual }
        if straight_rail_along(surface, position, vertical) and surface.can_place_entity(spec) then
          objects[#objects + 1] = rendering.draw_sprite({
            sprite = SPRITE,
            orientation = vertical and 0 or 0.25,
            x_scale = 2,
            y_scale = 2,
            surface = surface,
            target = position,
            players = { player },
          })
        end
      end
    end
    storage.markers = storage.markers or {}
    storage.markers[player.index] = { objects = objects, x = p.x, y = p.y, surface = surface.index, base = base }
    return
  end
  for _, rail in pairs(surface.find_entities_filtered({ type = "straight-rail", area = area })) do
    local d = rail.direction
    local vertical = d == defines.direction.north or d == defines.direction.south
    if vertical or d == defines.direction.east or d == defines.direction.west then
      -- a station is 2 tiles long and keeps the 1-tile grid along the rail: on each
      -- 2-tile rail piece it can sit centred, or one tile further on
      for step = 0, 1 do
        local position = vertical and { x = rail.position.x, y = rail.position.y + step }
          or { x = rail.position.x + step, y = rail.position.y }
        local key = position.x .. "," .. position.y
        if not seen[key] then
          seen[key] = true
          local spec = {
            name = shared.variant_name(base, vertical and 1 or 2),
            position = position,
            force = player.force,
            build_check_type = defines.build_check_type.manual,
          }
          if surface.can_place_entity(spec) then
            objects[#objects + 1] = rendering.draw_sprite({
              sprite = SPRITE,
              orientation = vertical and 0 or 0.25,
              surface = surface,
              target = position,
              players = { player },
            })
          end
        end
      end
    end
  end
  storage.markers = storage.markers or {}
  storage.markers[player.index] = { objects = objects, x = p.x, y = p.y, surface = surface.index, base = base }
end

-- Cursor changed: start, switch or stop the markers.
function markers.refresh(player_index)
  local player = game.get_player(player_index)
  local base = player and player.connected and (held_station(player) or held_connector(player))
  if base then
    draw(player, base)
  else
    clear(player_index)
  end
end

-- Player moved: redraw once they left the marked area's middle.
function markers.on_moved(player_index)
  local state = storage.markers and storage.markers[player_index]
  if not state then return end
  local player = game.get_player(player_index)
  local p = player.position
  if player.surface.index ~= state.surface
    or math.abs(p.x - state.x) > REDRAW_DISTANCE
    or math.abs(p.y - state.y) > REDRAW_DISTANCE
  then
    draw(player, state.base)
  end
end

-- Something was built or removed: redraw for everyone who has markers up.
function markers.redraw_all()
  if not (storage.markers and next(storage.markers)) then return end
  local indices = {}
  for index in pairs(storage.markers) do
    indices[#indices + 1] = index
  end
  for _, index in pairs(indices) do
    markers.refresh(index)
  end
end

return markers
