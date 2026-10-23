# Bulk Wagons

Factorio 2.1 mod (Space Age optional) that adds a bulk wagon for ores and other bulk goods, plus a loading station and an unloading pit that are built across the track.

- **Bulk wagon**: cargo wagon with three compartments that only accepts bulk goods (every mined resource plus ice, carbon, sulfur, uranium, holmium ore and seeds). Anything else is handed back or dropped next to the wagon. Colourable like a locomotive.
- **Unloading pit** (6 × 2 tiles, across the rail): empties stopped bulk wagons above it into its inventory. Its grate is walkable. Items leave through the built-in belt port or via inserters.
- **Belt loader** (6 × 2 tiles, across the rail, first research): no inventory, loads stopped bulk wagons straight from the connected belt at that belt's speed.
- **Portal silo loading station** (6 × 2 tiles, across the rail, second research): fills stopped bulk wagons below it from its inventory, fed by the built-in belt port or inserters.
- Every Space Age planet gets its own look for wagon and stations; the right variant is placed automatically, the item stays the same.
- Station inventories (pit, silo) can be read by the circuit network.
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

Graphics are rendered with Blender from the scripts in `tools/blender` (`render_all.sh`, then `build_sprites.py`). `python tools/package.py` builds the portal zip.


`python tests/run.py` starts Factorio headless in an isolated environment, builds a test scene with the harness mod in `tests/bulk-wagons-test` and prints the `BULKTEST` results.

`python tools/make_placeholders.py` regenerates the placeholder sprites.
