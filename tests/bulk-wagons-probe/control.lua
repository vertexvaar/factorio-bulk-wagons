-- Loaded into a copy of a save by tests/probe.py: logs every station connector once.
local function s(v) return serpent.line(v, { comment = false }) end

local VECTORS = {
  [defines.direction.north] = { 0, -1 },
  [defines.direction.east] = { 1, 0 },
  [defines.direction.south] = { 0, 1 },
  [defines.direction.west] = { -1, 0 },
}

local function lines_of(entity)
  local out = {}
  for i = 1, entity.get_max_transport_line_index() do
    out[#out + 1] = entity.get_transport_line(i).get_item_count()
  end
  return table.concat(out, "/")
end

local function probe()
  for _, surface in pairs(game.surfaces) do
    for _, c in pairs(surface.find_entities_filtered({ type = "loader-1x1" })) do
      if c.name:find("connector") then
        local container = c.loader_container
        local docked = pcall(remote.call, "bulk-wagons", "connector_docked", c)
          and remote.call("bulk-wagons", "connector_docked", c)
        local v = VECTORS[c.direction] or { 0, 0 }
        local front = surface.find_entities_filtered({ position = { c.position.x + v[1], c.position.y + v[2] }, radius = 0.1 })
        local fronts = {}
        for _, f in pairs(front) do
          fronts[#fronts + 1] = f.name .. "@" .. f.direction .. (f.get_max_transport_line_index and f.type:find("belt") and (" lines " .. lines_of(f)) or "")
        end
        local behavior = c.get_control_behavior()
        local b = behavior and {
          enable_disable = behavior.circuit_enable_disable,
          condition = behavior.circuit_condition,
          logistic = behavior.connect_to_logistic_network,
          set_filters = behavior.circuit_set_filters,
        }
        local neighbours = c.belt_neighbours
        log(string.format(
          "BULKPROBE %s %s pos=%s dir=%s type=%s status=%s disabled_by_script=%s container=%s docked=%s lines=%s filter_mode=%s filters=%s front=[%s] neighbours in=%d out=%d behavior=%s unit=%s",
          surface.name, c.name, s(c.position), c.direction, c.loader_type, tostring(c.status), tostring(c.disabled_by_script),
          container and (container.name .. "#" .. container.unit_number .. " " .. s(container.position)
            .. " items=" .. container.get_inventory(defines.inventory.chest).get_item_count()) or "nil",
          tostring(docked), lines_of(c), tostring(c.loader_filter_mode), s(c.filter_slot_count > 0 and c.get_filter(1) or nil),
          table.concat(fronts, ", "), #neighbours.inputs, #neighbours.outputs, s(b), tostring(c.unit_number)))
      end
    end
  end
  log("BULKPROBE DONE")
end

script.on_init(function() storage.done = false end)
script.on_event(defines.events.on_tick, function()
  if storage.done then return end
  storage.done = true
  probe()
end)
