-- Circuit network features of the stations: an enable condition, reading the contents
-- of a docked wagon (plus a "wagon docked" signal), the settings panel next to the
-- station window, and keeping settings and wires (and the station colour) in
-- blueprints and copy-paste.
--
-- A station's wires attach to its hidden inventory ("store"). A hidden constant
-- combinator, wired to the store by script, puts the wagon readings on that network.
local shared = require("shared")

local circuit = {}

local RED = defines.wire_connector_id.circuit_red
local GREEN = defines.wire_connector_id.circuit_green
local COMPARATORS = { ">", "<", "=", "≥", "≤", "≠" }
local PANEL = "bulk-wagons-circuit"
local TAG = "bulk_wagons"

local function default_settings()
  return {
    enable = false,
    signal = { type = "virtual", name = "signal-W" },
    comparator = ">",
    constant = 0,
    read_wagon = false,
    docked_signal = false,
  }
end

function circuit.settings(record)
  record.settings = record.settings or default_settings()
  return record.settings
end

--------------------------------------------------------------------------------
-- Hidden combinator

function circuit.attach(record)
  local store = record.store
  if not (store and store.valid) then return end
  if record.signals and record.signals.valid then return end
  local combinator = store.surface.create_entity({
    name = shared.signals,
    position = store.position,
    force = store.force,
    create_build_effect_smoke = false,
  })
  if not combinator then return end
  combinator.destructible = false
  for _, id in pairs({ RED, GREEN }) do
    combinator
      .get_wire_connector(id, true)
      .connect_to(store.get_wire_connector(id, true), false, defines.wire_origin.script)
  end
  record.signals = combinator
end

function circuit.detach(record)
  if record.signals and record.signals.valid then record.signals.destroy() end
  record.signals = nil
end

local function compare(a, op, b)
  if op == ">" then return a > b end
  if op == "<" then return a < b end
  if op == "=" then return a == b end
  if op == "≥" then return a >= b end
  if op == "≤" then return a <= b end
  return a ~= b
end

-- Whether the station may work. Without the enable condition switched on it always may.
function circuit.enabled(record)
  local s = circuit.settings(record)
  if not s.enable or not s.signal then return true end
  local store = record.store
  if not (store and store.valid) then return true end
  local value = store.get_signal(s.signal, RED, GREEN) or 0
  return compare(value, s.comparator, s.constant or 0)
end

-- Writes the wagon readings into the hidden combinator.
function circuit.update(record, wagon)
  local combinator = record.signals
  if not (combinator and combinator.valid) then return end
  local s = circuit.settings(record)
  local filters = {}
  if wagon and s.read_wagon then
    for _, item in pairs(wagon.get_inventory(defines.inventory.cargo_wagon).get_contents()) do
      if #filters >= 999 then break end
      filters[#filters + 1] = {
        value = { type = "item", name = item.name, quality = item.quality, comparator = "=" },
        min = item.count,
      }
    end
  end
  if wagon and s.docked_signal then
    filters[#filters + 1] =
      { value = { type = "virtual", name = "signal-W", quality = "normal", comparator = "=" }, min = 1 }
  end
  local behavior = combinator.get_or_create_control_behavior()
  local section = behavior.get_section(1) or behavior.add_section()
  section.filters = filters
end

--------------------------------------------------------------------------------
-- Blueprints, copy-paste

local function wires_of(record)
  local wires = {}
  local store = record.store
  if not (store and store.valid) then return wires end
  local origin = record.entity.position
  for _, id in pairs({ RED, GREEN }) do
    for _, connection in pairs(store.get_wire_connector(id, true).connections) do
      if connection.origin == defines.wire_origin.player then
        local target = connection.target
        local owner = target.owner
        wires[#wires + 1] = {
          id = id,
          target_id = target.wire_connector_id,
          name = owner.name,
          dx = owner.position.x - origin.x,
          dy = owner.position.y - origin.y,
        }
      end
    end
  end
  return wires
end

function circuit.to_tags(record)
  local s = circuit.settings(record)
  return {
    enable = s.enable,
    signal = s.signal,
    comparator = s.comparator,
    constant = s.constant,
    read_wagon = s.read_wagon,
    docked_signal = s.docked_signal,
    wires = wires_of(record),
    color = record.color,
  }
end

local function key(surface, x, y)
  return surface.index .. ":" .. math.floor(x * 2 + 0.5) .. ":" .. math.floor(y * 2 + 0.5)
end

local function try_connect(store, wire)
  local x, y = store.position.x, store.position.y
  local origin = wire.origin
  local tx, ty = origin.x + wire.dx, origin.y + wire.dy
  local targets = store.surface.find_entities_filtered({ position = { tx, ty }, radius = 0.1, name = wire.name })
  local target = targets[1]
  if not target then return false end
  if target.name == "entity-ghost" then return false end
  -- a wire to another station goes to that station's inventory
  local own = target.get_wire_connector(wire.target_id, true)
  if not own then return false end
  store.get_wire_connector(wire.id, true).connect_to(own, false, defines.wire_origin.player)
  return true
end

-- Applies settings from blueprint tags; wires to entities that are not built yet wait.
function circuit.from_tags(record, tags)
  local t = tags and tags[TAG]
  if not t then return end
  record.settings = {
    enable = t.enable == true,
    signal = t.signal,
    comparator = t.comparator or ">",
    constant = t.constant or 0,
    read_wagon = t.read_wagon == true,
    docked_signal = t.docked_signal == true,
  }
  record.color = t.color
  local store = record.store
  if not (store and store.valid) then return end
  for _, wire in pairs(t.wires or {}) do
    wire.origin = record.entity.position
    if not try_connect(store, wire) then
      local k = key(store.surface, wire.origin.x + wire.dx, wire.origin.y + wire.dy)
      storage.pending_wires[k] = storage.pending_wires[k] or {}
      table.insert(storage.pending_wires[k], { store = store, wire = wire, tick = game.tick })
    end
  end
end

-- Called for every built entity: connects wires that were waiting for it.
function circuit.on_any_built(entity)
  if not next(storage.pending_wires) then return end
  local k = key(entity.surface, entity.position.x, entity.position.y)
  local waiting = storage.pending_wires[k]
  if not waiting then return end
  storage.pending_wires[k] = nil
  for _, entry in pairs(waiting) do
    if entry.store.valid then try_connect(entry.store, entry.wire) end
  end
end

-- Pending wires older than an hour are dropped.
function circuit.expire_pending()
  for k, waiting in pairs(storage.pending_wires) do
    for i = #waiting, 1, -1 do
      if game.tick - waiting[i].tick > 216000 or not waiting[i].store.valid then table.remove(waiting, i) end
    end
    if #waiting == 0 then storage.pending_wires[k] = nil end
  end
end

function circuit.copy(from, to)
  local s = circuit.settings(from)
  to.settings = {
    enable = s.enable,
    signal = s.signal,
    comparator = s.comparator,
    constant = s.constant,
    read_wagon = s.read_wagon,
    docked_signal = s.docked_signal,
  }
  to.color = from.color
end

--------------------------------------------------------------------------------
-- Settings panel next to the station window

local function comparator_index(op)
  for i, c in pairs(COMPARATORS) do
    if c == op then return i end
  end
  return 1
end

function circuit.open_panel(player, record)
  local anchor = {
    gui = defines.relative_gui_type.container_gui,
    position = defines.relative_gui_position.right,
    name = record.store.name,
  }
  if player.gui.relative[PANEL] then player.gui.relative[PANEL].destroy() end
  local s = circuit.settings(record)
  local frame = player.gui.relative.add({
    type = "frame",
    name = PANEL,
    caption = { "bulk-wagons.circuit-title" },
    direction = "vertical",
    anchor = anchor,
  })
  frame.tags = { station = record.entity.unit_number }
  local inner = frame.add({ type = "frame", style = "inside_shallow_frame_with_padding", direction = "vertical" })
  inner.add({
    type = "checkbox",
    name = "bw_enable",
    caption = { "bulk-wagons.circuit-enable" },
    state = s.enable,
    tooltip = { "bulk-wagons.circuit-enable-tooltip" },
  })
  local row = inner.add({ type = "flow", name = "bw_condition", direction = "horizontal" })
  row.style.vertical_align = "center"
  row.add({ type = "choose-elem-button", name = "bw_signal", elem_type = "signal", signal = s.signal })
  row.add({
    type = "drop-down",
    name = "bw_comparator",
    items = COMPARATORS,
    selected_index = comparator_index(s.comparator),
  })
  local field = row.add({
    type = "textfield",
    name = "bw_constant",
    text = tostring(s.constant or 0),
    numeric = true,
    allow_negative = true,
  })
  field.style.width = 80
  inner.add({ type = "line" })
  inner.add({
    type = "checkbox",
    name = "bw_read_wagon",
    caption = { "bulk-wagons.circuit-read-wagon" },
    state = s.read_wagon,
    tooltip = { "bulk-wagons.circuit-read-wagon-tooltip" },
  })
  inner.add({
    type = "checkbox",
    name = "bw_docked",
    caption = { "bulk-wagons.circuit-docked" },
    state = s.docked_signal,
    tooltip = { "bulk-wagons.circuit-docked-tooltip" },
  })
end

function circuit.close_panel(player)
  if player.gui.relative[PANEL] then player.gui.relative[PANEL].destroy() end
end

local function panel_record(element)
  local frame = element
  while frame and frame.name ~= PANEL do
    frame = frame.parent
  end
  if not frame then return end
  return storage.stations[frame.tags.station]
end

function circuit.on_gui_changed(event)
  local element = event.element
  if not (element and element.valid) or not element.name:find("^bw_") then return end
  local record = panel_record(element)
  if not record then return end
  local s = circuit.settings(record)
  local name = element.name
  if name == "bw_enable" then
    s.enable = element.state
  elseif name == "bw_signal" then
    s.signal = element.elem_value
  elseif name == "bw_comparator" then
    s.comparator = COMPARATORS[element.selected_index] or ">"
  elseif name == "bw_constant" then
    s.constant = tonumber(element.text) or 0
  elseif name == "bw_read_wagon" then
    s.read_wagon = element.state
  elseif name == "bw_docked" then
    s.docked_signal = element.state
  end
end

circuit.TAG = TAG

return circuit
