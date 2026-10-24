local shared = require("shared")
local collision_mask_util = require("__core__/lualib/collision-mask-util")

-- Everything a station must not be built onto gets the station collision layer:
-- buildings, trees, rocks, cliffs (all with the object layer) except rails, plus the
-- rail signals, supports and ramps that live next to and over the track.
local NEAR_TRACK = { ["rail-signal"] = true, ["rail-chain-signal"] = true, ["rail-support"] = true, ["rail-ramp"] = true }
for type in pairs(defines.prototypes.entity) do
  for _, prototype in pairs(data.raw[type] or {}) do
    local ok, mask = pcall(collision_mask_util.get_mask, prototype)
    if ok and mask and mask.layers and (NEAR_TRACK[type] or mask.layers.object and not mask.layers.rail) then
      mask = table.deepcopy(mask)
      mask.layers[shared.collision_layer] = true
      prototype.collision_mask = mask
    end
  end
end

-- Shift + right click on rolling stock or a train stop, then Shift + left click on a
-- station copies the colour to the station.
local windows = shared.station_window_names()
for _, type in pairs({ "locomotive", "cargo-wagon", "fluid-wagon", "artillery-wagon", "train-stop" }) do
  for _, prototype in pairs(data.raw[type] or {}) do
    local list = prototype.additional_pastable_entities or {}
    for _, name in pairs(windows) do
      list[#list + 1] = name
    end
    prototype.additional_pastable_entities = list
  end
end
