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

-- Sprite and animation prototypes the script draws on top of stations:
-- bulk-<key>-<variant>-idle, -work (looping) and -extend (played once), each with
-- a _mask twin in the station colour, plus -base_mask over the station picture.
function graphics.station_overlays()
  local prototypes = {}
  for name, set in pairs(sprites) do
    if name ~= "wagon" then
      for kind, meta in pairs(set) do
        if kind ~= "base" and kind ~= "shadow" then
          if meta.frame_count > 1 then
            prototypes[#prototypes + 1] = {
              type = "animation",
              name = "bulk-" .. name .. "-" .. kind,
              layers = { sheet(meta, { frame_count = meta.frame_count, animation_speed = 0.25 }) },
            }
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

-- Cargo heaps, drawn by the script on loaded wagons; one frame per direction.
function graphics.wagon_load()
  local set = sprites.wagon
  if not (set and set.load) then return end
  data:extend({
    {
      type = "animation",
      name = "bulk-wagon-load",
      layers = { sheet(set.load, { frame_count = 128 }) },
    },
  })
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
      data = { load = sprites.wagon ~= nil and sprites.wagon.load ~= nil, extend = extend },
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
