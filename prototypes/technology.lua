local shared = require("shared")

data:extend({
  {
    type = "technology",
    name = "bulk-wagons",
    icons = {
      { icon = "__base__/graphics/technology/railway.png", icon_size = 256, tint = { r = 1, g = 0.75, b = 0.6 } },
    },
    effects = {
      { type = "unlock-recipe", recipe = shared.wagon },
      { type = "unlock-recipe", recipe = shared.bunker },
      { type = "unlock-recipe", recipe = "bulk-connector" },
    },
    prerequisites = { "railway", "concrete" },
    unit = {
      count = 150,
      ingredients = {
        { "automation-science-pack", 1 },
        { "logistic-science-pack", 1 },
      },
      time = 30,
    },
  },
  {
    type = "technology",
    name = "bulk-wagons-silo",
    icons = {
      { icon = "__base__/graphics/technology/railway.png", icon_size = 256, tint = { r = 0.7, g = 0.8, b = 1 } },
    },
    effects = {
      { type = "unlock-recipe", recipe = shared.silo },
    },
    prerequisites = { "bulk-wagons", "advanced-circuit" },
    unit = {
      count = 200,
      ingredients = {
        { "automation-science-pack", 1 },
        { "logistic-science-pack", 1 },
      },
      time = 30,
    },
  },
})

-- The faster connectors come with the belt tier they run at.
for _, def in pairs(shared.connectors) do
  local tech = data.raw.technology[def.tech]
  if def.tech ~= "bulk-wagons" and tech and data.raw.recipe[def.name] then
    tech.effects = tech.effects or {}
    table.insert(tech.effects, { type = "unlock-recipe", recipe = def.name })
  end
end

data:extend({
  {
    type = "custom-input",
    name = "bulk-wagons-rotate",
    key_sequence = "",
    linked_game_control = "rotate",
  },
  {
    type = "custom-input",
    name = "bulk-wagons-reverse-rotate",
    key_sequence = "",
    linked_game_control = "reverse-rotate",
  },
})
