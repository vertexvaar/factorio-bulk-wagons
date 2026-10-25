-- Placement markers: while a player holds a station, every free spot on a straight
-- rail nearby gets the game's rail signal placement indicator. The engine draws those
-- only for its own signals, so the script draws the same sprite, for that player only
-- and only while the station is in the cursor, so idle players cost nothing.
local shared = require("shared")

local markers = {}

local RADIUS = 32 -- tiles around the player
local REDRAW_DISTANCE = 8 -- tiles the player moves before the markers are redrawn
local SPRITE = "utility/rail_signal_placement_indicator"

local bases = {}
for _, base in pairs({ shared.pit, shared.loader, shared.belt_loader }) do
  for variant = 1, shared.variant_count do
    bases[shared.variant_name(base, variant)] = base
  end
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

local function draw(player, base)
  clear(player.index)
  local surface = player.surface
  local p = player.position
  local objects = {}
  local area = { { p.x - RADIUS, p.y - RADIUS }, { p.x + RADIUS, p.y + RADIUS } }
  local seen = {}
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
  local base = player and player.connected and held_station(player)
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
