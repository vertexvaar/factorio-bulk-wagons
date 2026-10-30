-- Belts and buildings under a bunker or silo. A station cannot be built onto them, but
-- one that grew with an update (the bunker went from 6 to 8 tiles across the track in
-- 0.5.0) can stand on top of some. They keep working; each one gets a warning sign in
-- the world and its station a tag on the map, until it is gone or the station is.
local shared = require("shared")

local covered = {}

local SPRITE = "utility/warning_icon"
local LAYERS = { shared.collision_layer, "transport_belt" }

local own_entity = {} -- entity name -> true for this mod's own entities
local function is_own(entity)
  local known = own_entity[entity.name]
  if known == nil then
    local history = prototypes.get_history(entity.type, entity.name)
    known = history ~= nil and history.created == script.mod_name
    own_entity[entity.name] = known
  end
  return known
end

local function blocks(entity)
  if entity.type == "entity-ghost" or entity.force.name == "neutral" or is_own(entity) then return false end
  local layers = entity.prototype.collision_mask.layers
  for _, layer in pairs(LAYERS) do
    if layers[layer] then return true end
  end
  return false
end

-- Removes the signs and the map tag of a station.
function covered.forget(unit_number)
  local state = storage.covered and storage.covered[unit_number]
  if not state then return end
  for registration, entry in pairs(state.entries) do
    if entry.sprite.valid then entry.sprite.destroy() end
    storage.covered_by[registration] = nil
  end
  if state.tag and state.tag.valid then state.tag.destroy() end
  storage.covered[unit_number] = nil
end

-- Looks under a station and marks what it covers. Returns how many entities that are.
function covered.scan(record)
  storage.covered = storage.covered or {} -- station unit_number -> { tag, entries = registration -> { entity, sprite } }
  storage.covered_by = storage.covered_by or {} -- registration number -> station unit_number
  local station = record.entity
  if not station.valid or shared.is_legacy(record.base) then return 0 end
  covered.forget(station.unit_number)
  local box = station.bounding_box
  local area = { { box.left_top.x + 0.1, box.left_top.y + 0.1 }, { box.right_bottom.x - 0.1, box.right_bottom.y - 0.1 } }
  local entries, first, count = {}, nil, 0
  for _, entity in pairs(station.surface.find_entities_filtered({ area = area })) do
    if entity ~= station and blocks(entity) then
      local registration = script.register_on_object_destroyed(entity)
      entries[registration] = {
        entity = entity,
        sprite = rendering.draw_sprite({
          sprite = SPRITE,
          target = entity,
          surface = station.surface,
          render_layer = "entity-info-icon-above",
          x_scale = 0.5,
          y_scale = 0.5,
        }),
      }
      storage.covered_by[registration] = station.unit_number
      first = first or entity
      count = count + 1
    end
  end
  if count == 0 then return 0 end
  local place = first.prototype.items_to_place_this
  local tag = station.force.add_chart_tag(station.surface, {
    position = first.position,
    text = "Bulk Wagons: covered by station",
    icon = { type = "item", name = place and place[1] and place[1].name or record.base },
  })
  storage.covered[station.unit_number] = { tag = tag, entries = entries }
  return count
end

-- A covered entity is gone: its sign goes, and the map tag with the last one.
function covered.on_object_destroyed(registration)
  local owner = storage.covered_by and storage.covered_by[registration]
  if not owner then return end
  storage.covered_by[registration] = nil
  local state = storage.covered[owner]
  local entry = state and state.entries[registration]
  if not entry then return end
  if entry.sprite.valid then entry.sprite.destroy() end
  state.entries[registration] = nil
  if not next(state.entries) then covered.forget(owner) end
end

-- Number of entities currently marked under a station.
function covered.count(unit_number)
  local state = storage.covered and storage.covered[unit_number]
  return state and table_size(state.entries) or 0
end

return covered
