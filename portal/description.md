A bulk wagon for ores and other bulk goods, plus an unloading bunker and a loading silo that each serve a whole wagon. Trains halt, the goods pour through the wagon's bottom flaps or down three chutes, and belts carry them on through connectors in every belt tier. Factorio 2.1, Space Age optional.

![Unloading bunkers under a halted train](https://raw.githubusercontent.com/vertexvaar/factorio-bulk-wagons/main/previews/portal/1-overview.png)

## The bulk wagon

- A cargo wagon with three compartments that only takes bulk goods: every mined resource plus ice, carbon, sulfur, uranium, holmium ore and seeds. Anything else is handed back or dropped next to the wagon.
- 40 slots by default, weight like the vanilla cargo wagon (both startup settings).
- Colourable like a locomotive. While a bunker unloads it, you see the heap drain through the open flaps.
- Tilts on rail ramps and runs on elevated rails (Space Age), with its load visible.

## Unloading bunker and loading silo

- **Unloading bunker** (8 × 6 tiles, first research): built over a whole wagon slot, the track runs through it. It empties the halted wagon into its own inventory. Its gratings can be walked and driven on.
- **Loading silo** (6 × 6 tiles, second research): stands over a whole wagon slot and fills the halted wagon through three chutes. Counts as a tall building, so with tall buildings hidden you can click the wagon under it.
- Near a train stop, both snap onto the wagon slots of a halted train (7 tiles apart behind the stop), and green indicators show the free slots. Elsewhere they keep the 1-tile grid along the track; press R to turn them.

![A bunker empties a wagon through its flaps](https://raw.githubusercontent.com/vertexvaar/factorio-bulk-wagons/main/previews/portal/2-bunker.png)

## Bulk connectors

- One per belt tier: yellow with the first research, red, blue and green with the belt research.
- A connector takes the belt on one rim tile of a long side and climbs sideways over the next one: a bucket elevator out of the bunker pit, a conveyor up to the silo bin. Up to three per side.
- On a bunker they always take goods out, on a silo they always feed it, whichever way you place them. They run at their belt tier's speed; without a belt they hold the goods back, nothing lands on the ground.
- With a connector in the cursor, the free rim tiles show green placement indicators. Inserters work on both buildings too.

![Loading silos fed by connectors](https://raw.githubusercontent.com/vertexvaar/factorio-bulk-wagons/main/previews/portal/3-silo.png)

![Bunker connectors on blue belts](https://raw.githubusercontent.com/vertexvaar/factorio-bulk-wagons/main/previews/portal/4-connectors.png)

## Circuit network and colours

- Station contents are readable. A panel next to the station window adds an enable/disable condition, reading the docked wagon's contents and a wagon docked signal (W = 1).
- Stations take a colour like the wagon: colour panel next to the station window, or copy it from a locomotive, wagon or train stop with Shift + right/left click. A station in the train's colour matches it.
- Blueprints keep settings, colours and wires.
- With Space Age every planet gives wagon and stations its own look; the right variant is placed automatically.

![Unloading bunker on Fulgora](https://raw.githubusercontent.com/vertexvaar/factorio-bulk-wagons/main/previews/portal/5-fulgora.png)

## Performance

Stations only work while a train with bulk wagons halts on them. A halting train wakes the stations under its wagons, they move the goods, and they go back to sleep once the train has left. Manually driven trains are noticed as well. An idle station costs nothing per tick.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| Bulk wagon inventory slots | startup | 40 |
| Bulk wagon weight | startup | 1000 |
| Unloading bunker size (× wagon) | startup | 3 |
| Loading silo size (× wagon) | startup | 3 |
| Transfer rate per station (items/s) | map | 250 |
| Additional bulk items (comma separated) | map | empty |

Other mods can register bulk goods with `remote.call("bulk-wagons", "add_allowed_items", {"my-ore"})`.

## Updating from 0.3

The old three-per-wagon stations (pit, belt loader, portal silo) are replaced by one bunker or silo per wagon slot, with their contents, settings and colour. Where the new building has no room, the old stations stay and the spot gets a map marker. Connectors from 0.4 move onto the rim with their filters, circuit settings and wires.

Languages: English, German. Source and issues: [GitHub](https://github.com/vertexvaar/factorio-bulk-wagons).
