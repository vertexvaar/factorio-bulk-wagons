local shared = require("shared")

local slots = settings.startup["bulk-wagons-wagon-slots"].value

-- Placeholder: reuses the vanilla cargo wagon artwork (incl. its colour mask)
-- until the final sprites exist.
local wagon = table.deepcopy(data.raw["cargo-wagon"]["cargo-wagon"])
wagon.name = shared.wagon
wagon.icons = { { icon = "__base__/graphics/icons/cargo-wagon.png", tint = { r = 1, g = 0.75, b = 0.6 } } }
wagon.icon = nil
wagon.inventory_size = slots
wagon.minable = { mining_time = 0.5, result = shared.wagon }
wagon.color = { r = 0.56, g = 0.23, b = 0.15, a = 1 }
wagon.allow_manual_color = true
wagon.factoriopedia_simulation = nil

local item = table.deepcopy(data.raw["item-with-entity-data"]["cargo-wagon"])
item.name = shared.wagon
item.icons = wagon.icons
item.icon = nil
item.place_result = shared.wagon
item.order = "c[rolling-stock]-b[cargo-wagon]-b[bulk-wagon]"

data:extend({
  wagon,
  item,
  {
    type = "recipe",
    name = shared.wagon,
    energy_required = 1,
    enabled = false,
    ingredients = {
      { type = "item", name = "iron-gear-wheel", amount = 10 },
      { type = "item", name = "iron-plate", amount = 10 },
      { type = "item", name = "steel-plate", amount = 25 },
    },
    results = { { type = "item", name = shared.wagon, amount = 1 } },
  },
})
