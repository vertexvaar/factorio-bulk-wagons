local shared = require("shared")

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
