# Procedural layer channel selection

For manifest schema 2.0, an overlay can opt in to explicit channel
participation with `affects`. The first (base) layer always initializes all
channels. Omitting `affects` preserves the original all-channel behavior
and control layout.

```json
{
  "id": "GripPolish",
  "name": "Grip polish",
  "mask": "Grip",
  "affects": ["roughness"],
  "values": {"roughness": 0.15}
}
```

List only the channels the layer may alter. Each listed channel is driven
by its `channels` signal binding, if present, or its `values` constant.
Unlisted channels carry the previous socket forward unchanged; they have
no editable layer constant. Retain a channel in `affects` to write an
explicit zero. A signal binding outside `affects` is invalid. A selected
channel with no signal or constant uses the channel default. Values of
unselected channels can exist in normalized documents and remain inert.

To migrate an old overlay, choose the channels it was intended to affect,
list them explicitly, and compare maps with the legacy recipe. An edited
live constant cannot be silently discarded when making a channel
inactive or changing it to a signal on an explicit overlay.

## Reproduce

```sh
python -m unittest discover -s tests -p test_layer_channel_routing.py -v
```

The host test executes the actual graph build loop with recording sockets.
For 0, 0.5 and 1 mask weights it expects roughness 0.34, 0.245 and 0.15,
with all other channels equal to the underlying steel. It also checks
explicit zero, signal routing, old recipes and the live-edit merge guard.

Native verification: run the paired toolbox fixtures through a compatible
blenderctl backend in a disposable project; compare the metallic and base
color exports against the unedited control, then cold-open the project and
repeat from the exported maps. Keep native output and host results separate.
