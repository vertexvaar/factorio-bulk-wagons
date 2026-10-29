# Bulk Wagons

Factorio 2.1 mod (Space Age optional) that adds a bulk wagon for ores and other bulk goods, plus an unloading bunker and a loading silo that each serve a whole wagon.

- **Bulk wagon**: cargo wagon with three compartments that only accepts bulk goods (every mined resource plus ice, carbon, sulfur, uranium, holmium ore and seeds). Anything else is handed back or dropped next to the wagon. Colourable like a locomotive. While a bunker unloads it, the cargo visibly drains through the open bottom flaps.
- **Unloading bunker** (8 × 6 tiles, first research): built over a whole wagon slot, the track runs through it. Empties the stopped wagon through its flaps into its inventory. Its gratings can be walked and driven on, its rims block players and vehicles.
- **Loading silo** (6 × 6 tiles, second research): stands over a whole wagon slot and fills the stopped wagon through three chutes from its inventory. Solid beside the track. Counts as a tall building, so with tall buildings hidden the wagon under it can be clicked.
- **Bulk connectors** in every belt tier (yellow with the first research, red, blue and green with the belt research): loaders that take the belt on one rim tile of a long side of a bunker or silo and climb sideways over the next one (a bucket elevator out of the pit, a conveyor up to the silo bin), at most three per side, and work nowhere else. While one is in the cursor, the free rim tiles show green placement indicators. The arrow sets the way: pointing away from the station takes goods out, pointing at it feeds them in. They run at their tier's speed; without a belt they hold the goods back, nothing lands on the ground. Inserters work on both buildings too.
- **Wagon slots**: near a train stop, bunker and silo snap onto the slots where the wagons of a halted train stand (7 tiles apart behind the stop), and the placement indicators show the free slots. Elsewhere they keep the 1-tile grid along the track; press R to turn them.
- Stations are colourable like the wagon: colour panel next to the station window, or copy the colour from a locomotive, wagon or train stop with Shift + right/left click. The masks work like the vanilla ones, so a station in the train's colour matches it.
- Every Space Age planet gets its own look for wagon and stations; the right variant is placed automatically, the item stays the same.
- Circuit network: station contents are readable; a panel next to the station window adds an enable/disable condition, reading the docked wagon's contents and a wagon docked signal (W = 1). Blueprints keep settings and wires.
- **Update from 0.3**: the old three-per-wagon stations (pit, belt loader, portal silo) are replaced by one bunker or silo per wagon slot, with their contents, settings and colour. Where the new building has no room the old stations stay and the spot gets a map marker.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| Bulk wagon inventory slots | startup | 40 |
| Bulk wagon weight | startup | 1000 |
| Unloading bunker size (× wagon) | startup | 3 |
| Loading silo size (× wagon) | startup | 3 |
| Built-in belt speed (old stations only) | startup | express |
| Transfer rate per station (items/s) | map | 250 |
| Additional bulk items (comma separated) | map | empty |

Other mods can register bulk goods with `remote.call("bulk-wagons", "add_allowed_items", {"my-ore"})`.

## Development

Graphics are rendered with Blender from the scripts in `tools/blender` (`render_all.sh`, then `build_sprites.py`). Colour masks follow the vanilla rules (FFF #218): parts that take the colour are rendered in neutral grey (materials with `paint=True`, or objects with `mask`), their `*_mask` pass only marks where the colour goes, and `pack.py` fills the mask with half the brightness of the grey paint. The game applies the colour at alpha 0.5. `python tools/package.py` builds the portal zip.

`render_all.sh <out_dir> e1` renders a single part; `build_sprites.py` then only replaces the sprite sets found in
`<out_dir>` and keeps the others. To look at a model in Blender, `blender -b --factory-startup -P
tools/blender/save_scenes.py -- e1` (or `b1`, `b3`, `wagon`) saves the scene to `tools/blender/scenes/*.blend`; the
scripts stay the source, edits in the .blend file do not reach the sprites. Set `BULK_GPU=CUDA` when Cycles cannot
load its OptiX kernel.


`python tests/run.py` starts Factorio headless in an isolated environment, builds a test scene with the harness mod in `tests/bulk-wagons-test` and prints the `BULKTEST` results.

`python tools/make_placeholders.py` regenerates the placeholder sprites.

