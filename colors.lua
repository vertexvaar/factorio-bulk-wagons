-- Station colour: the script draws a mask over the station picture and over its
-- overlay, tinted like the runtime tint of rolling stock (always alpha 0.5, so the
-- colour comes out as muted as on a locomotive). A panel next to the station window
-- sets it; blueprints and copy-paste keep it (see circuit.lua).
local shared = require("shared")

local colors = {}

local PANEL = "bulk-wagons-color"
local CHANNELS = { "r", "g", "b" }

function colors.get(record) return record.color or shared.station_color end

-- Any colour (from a wagon, a train stop, a blueprint) becomes a station colour.
local function normalize(color)
  return {
    r = color.r or color[1] or 0,
    g = color.g or color[2] or 0,
    b = color.b or color[3] or 0,
    a = shared.station_color.a,
  }
end

-- Applies the record's colour to its mask objects.
function colors.apply(record)
  local color = colors.get(record)
  for _, key in pairs({ "base_mask", "mask" }) do
    local object = record[key]
    if object and object.valid then object.color = color end
  end
end

function colors.set(record, color)
  record.color = color and normalize(color) or nil
  colors.apply(record)
end

--------------------------------------------------------------------------------
-- Panel next to the station window

local function byte(value) return math.floor(value * 255 + 0.5) end

local function refresh(frame, color)
  for _, c in pairs(CHANNELS) do
    local row = frame.children[1].inner["bwc_row_" .. c]
    row["bwc_slider_" .. c].slider_value = byte(color[c])
    row["bwc_text_" .. c].text = tostring(byte(color[c]))
  end
end

function colors.open_panel(player, record)
  if player.gui.relative[PANEL] then player.gui.relative[PANEL].destroy() end
  local frame = player.gui.relative.add({
    type = "frame",
    name = PANEL,
    caption = { "bulk-wagons.color-title" },
    direction = "vertical",
    anchor = {
      gui = defines.relative_gui_type.container_gui,
      position = defines.relative_gui_position.right,
      name = record.store.name,
    },
  })
  frame.tags = { station = record.entity.unit_number }
  -- same layout as the circuit panel above it
  local outer = frame.add({ type = "frame", style = "inside_shallow_frame", direction = "vertical" })
  local inner = outer.add({ type = "flow", name = "inner", direction = "vertical" })
  inner.style.padding = { 8, 12, 12, 12 }
  inner.style.vertical_spacing = 8
  for _, c in pairs(CHANNELS) do
    local row = inner.add({ type = "flow", name = "bwc_row_" .. c, direction = "horizontal" })
    row.style.vertical_align = "center"
    row.add({ type = "label", caption = { "bulk-wagons.color-" .. c } }).style.width = 16
    row.add({
      type = "slider",
      name = "bwc_slider_" .. c,
      minimum_value = 0,
      maximum_value = 255,
      value_step = 1,
    })
    local field = row.add({ type = "textfield", name = "bwc_text_" .. c, numeric = true, lose_focus_on_confirm = true })
    field.style.width = 48
  end
  inner.add({
    type = "button",
    name = "bwc_reset",
    caption = { "bulk-wagons.color-reset" },
    tooltip = { "bulk-wagons.color-reset-tooltip" },
  })
  refresh(frame, colors.get(record))
end

function colors.close_panel(player)
  if player.gui.relative[PANEL] then player.gui.relative[PANEL].destroy() end
end

local function panel_of(element)
  local frame = element
  while frame and frame.name ~= PANEL do
    frame = frame.parent
  end
  return frame
end

-- Slider moved, number typed or reset clicked.
function colors.on_gui_event(event)
  local element = event.element
  if not (element and element.valid) or not element.name:find("^bwc_") then return end
  local frame = panel_of(element)
  local record = frame and storage.stations[frame.tags.station]
  if not record then return end
  if element.name == "bwc_reset" then
    if event.name ~= defines.events.on_gui_click then return end
    colors.set(record, nil)
    refresh(frame, colors.get(record))
    return
  end
  local channel = element.name:match("^bwc_slider_(%a)$") or element.name:match("^bwc_text_(%a)$")
  if not channel then return end
  local value = element.type == "slider" and element.slider_value or tonumber(element.text)
  if not value then return end
  value = math.max(0, math.min(255, value))
  local color = normalize(colors.get(record))
  color[channel] = value / 255
  colors.set(record, color)
  local row = frame.children[1].inner["bwc_row_" .. channel]
  if element.type == "slider" then
    row["bwc_text_" .. channel].text = tostring(byte(color[channel]))
  else
    row["bwc_slider_" .. channel].slider_value = value
  end
end

return colors
