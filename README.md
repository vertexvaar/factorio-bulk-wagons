# Bulk Wagons

Factorio 2.0 mod (Space Age optional) that adds a bulk wagon for ores and other bulk goods, plus a loading station and an unloading pit that are built across the track.

- **Bulk wagon**: cargo wagon with three compartments that only accepts bulk goods (every mined resource plus ice, carbon, sulfur, uranium, holmium ore and seeds). Anything else is handed back or dropped next to the wagon. Colourable like a locomotive.
- **Unloading pit** (6 × 2 tiles, across the rail): empties stopped bulk wagons above it into its inventory. Items leave through the built-in belt port or via inserters.
- **Loading station** (6 × 2 tiles, across the rail): fills stopped bulk wagons below it from its inventory, fed by the built-in belt port or inserters.
- One station per compartment, like pumps at a fluid wagon. Stations snap onto the rail when built; press R while placing to switch the port side.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| Bulk wagon inventory slots | startup | 40 |
| Unloading pit size (× wagon) | startup | 3 |
| Loading station size (× wagon) | startup | 3 |
| Built-in belt speed | startup | express |
| Transfer rate per station (items/s) | map | 240 |
| Additional bulk items (comma separated) | map | empty |

Other mods can register bulk goods with `remote.call("bulk-wagons", "add_allowed_items", {"my-ore"})`.

## Development

`python tests/run.py` starts Factorio headless in an isolated environment, builds a test scene with the harness mod in `tests/bulk-wagons-test` and prints the `BULKTEST` results.

`python tools/make_placeholders.py` regenerates the placeholder sprites.
