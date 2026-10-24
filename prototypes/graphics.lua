-- Builds sprite definitions from graphics/entity/sprites.lua, which
-- tools/blender/build_sprites.py generates from the Blender renders.
-- Without that file the mod falls back to the placeholder art.
local shared = require("shared")

local graphics = {}
local ok, sprites = pcall(require, "graphics.entity.sprites")
graphics.available = ok and type(sprites) == "table"
sprites = graphics.available and sprites or {}

local path = "__bulk-wagons__/graphics/entity/"

local function tint_for(planet)
  -- Planet looks are placeholder tints until their own renders exist.
  if planet and planet ~= shared.default_planet then return shared.placeholder_tint[planet] end
end

local function sheet(meta, extra)
  local def = {
    width = meta.width,
    height = meta.height,
    shift = meta.shift,
    scale = 0.5,
  }
  if #meta.files == 1 then
    def.filename = path .. meta.files[1]
  else
    def.filenames = {}
    for i, f in ipairs(meta.files) do
      def.filenames[i] = path .. f
    end
    def.lines_per_file = meta.lines_per_file
  end
  if meta.frame_count > 1 then def.line_length = meta.line_length end
  for k, v in pairs(extra or {}) do
    def[k] = v
  end
  return def
end

function graphics.station_picture(key, variant, planet)
  local set = sprites[key .. "-" .. variant]
  if not set then return nil end
  local tint = tint_for(planet)
  if set.base then
    return {
      layers = {
        sheet(set.base, { tint = tint }),
        sheet(set.shadow, { draw_as_shadow = true }),
      },
    }
  end
  return sheet(set.idle, { tint = tint })
end

-- The station as it stands idle (ground parts plus the overhead parts that do not
-- move), for the hidden inventory, whose window preview would show nothing otherwise.
-- offset: where that inventory sits relative to the station centre.
function graphics.preview_patch(picture, key, variant, planet, offset)
  local layers = {}
  for _, layer in pairs(picture.layers or { picture }) do
    if not layer.draw_as_shadow then layers[#layers + 1] = table.deepcopy(layer) end
  end
  local set = sprites[key .. "-" .. variant]
  if set and set.top_static then layers[#layers + 1] = sheet(set.top_static, { tint = tint_for(planet) }) end
  for _, layer in pairs(layers) do
    local shift = layer.shift or { 0, 0 }
    layer.shift = { (shift[1] or shift.x) - offset[1], (shift[2] or shift.y) - offset[2] }
  end
  return { layers = layers }
end

-- Sprite and animation prototypes the script draws on top of stations:
-- bulk-<key>-<variant>-idle, -work (looping), -extend and -retract (played once) and
-- -docked (the last extend frame), each with a _mask twin in the station colour, plus
-- -base_mask over the station picture.
function graphics.station_overlays()
  local prototypes = {}
  local function animation(name, meta, sequence)
    prototypes[#prototypes + 1] = {
      type = "animation",
      name = name,
      layers = {
        sheet(meta, { frame_count = meta.frame_count, frame_sequence = sequence, animation_speed = 0.25 }),
      },
    }
  end
  for name, set in pairs(sprites) do
    if name ~= "wagon" then
      for kind, meta in pairs(set) do
        if kind ~= "base" and kind ~= "shadow" and kind ~= "top_static" then
          if meta.frame_count > 1 then
            animation("bulk-" .. name .. "-" .. kind, meta)
            if kind:find("^extend") then
              local reversed = {}
              for i = meta.frame_count, 1, -1 do
                reversed[#reversed + 1] = i
              end
              animation("bulk-" .. name .. "-" .. kind:gsub("^extend", "retract"), meta, reversed)
              animation("bulk-" .. name .. "-" .. kind:gsub("^extend", "docked"), meta, { meta.frame_count })
            end
          else
            prototypes[#prototypes + 1] =
              { type = "sprite", name = "bulk-" .. name .. "-" .. kind, layers = { sheet(meta) } }
          end
        end
      end
    end
  end
  if #prototypes > 0 then data:extend(prototypes) end
end

-- Cargo heaps, drawn by the script on loaded wagons: bulk-wagon-load-1 (a quarter
-- full) to -4 (full), one frame per direction.
function graphics.wagon_load()
  local set = sprites.wagon
  if not (set and set.load4) then return end
  for level = 1, 4 do
    data:extend({
      {
        type = "animation",
        name = "bulk-wagon-load-" .. level,
        layers = { sheet(set["load" .. level], { frame_count = 128 }) },
      },
    })
  end
end

-- Tells the script which generated graphics exist (call once, at the end of the data stage).
function graphics.publish()
  local extend = {}
  for name, set in pairs(sprites) do
    if set.extend then extend[name] = true end
  end
  data:extend({
    {
      type = "mod-data",
      name = "bulk-wagons-graphics",
      data = { load = sprites.wagon ~= nil and sprites.wagon.load4 ~= nil, extend = extend },
    },
  })
end

function graphics.wagon_pictures(planet)
  local set = sprites.wagon
  if not set then return nil end
  local rotated =
    { direction_count = 128, back_equals_front = true, allow_low_quality_rotation = true, usage = "train" }
  local function with(extra)
    local t = {}
    for k, v in pairs(rotated) do
      t[k] = v
    end
    for k, v in pairs(extra) do
      t[k] = v
    end
    return t
  end
  return {
    rotated = {
      layers = {
        sheet(set.color, with({ tint = tint_for(planet) })),
        sheet(set.mask, with({ flags = { "mask" }, apply_runtime_tint = true })),
        sheet(set.shadow, with({ draw_as_shadow = true })),
      },
    },
  }
end

return graphics
