# Farley Mesh Fleet

Live dashboard for the family's Meshtastic mesh network.

🔗 **Live dashboard:** https://fructifyme.github.io/mesh-fleet/

## Fleet

| Site | Device | WiFi | GPS | MQTT path |
|---|---|---|---|---|
| Danvers, MA (Mike's roof) | RAK WisMesh Repeater Mini | ❌ | ❌ fixed | via neighbor gateways |
| Jim's house + mobile | LILYGO T-Deck Plus EXT | ✅ | ✅ | direct (home WiFi); GPS trail when mobile |
| Merrymeeting Lake (Jim's cabin) | RAK WisBlock Starter Kit | ❌ | ❌ fixed | only when T-Deck or hotspot is at the camp |

## What it does

- Live map of all family nodes
- Real-time MQTT feed from `mqtt.meshtastic.org` (public LongFast + private FarleyFam channels)
- Per-node battery, position, last-heard
- GPS trail rendering for mobile nodes
- Channel sharing via QR/URL
- Diagnostic + setup scripts for getting new nodes online

## Adding a new node

1. Plug into PC via USB, identify the COM port
2. `python reset_keys.py` — regenerates unique PKI keys (needed for any node shipped with stock NomadStar firmware)
3. `python node_health.py COMx` — 7-point pre-deployment checklist
4. Import the FarleyFam channel URL via the Meshtastic phone app

## Adding a mobile node to the dashboard

Edit the `SITES` array near the top of `index.html`'s `<script>` tag and add a new entry with `mobile: true, type: "tracker"`. The dashboard will auto-render a live trail as MQTT position updates arrive.

## Privacy

- The FarleyFam channel PSK is **never** committed to this repo
- Stored in browser localStorage only — entered once per device via the ⚙ Settings dialog
- Encrypted messages travel through public MQTT but are unreadable without the PSK

## Files

| File | Purpose |
|---|---|
| `index.html` | The dashboard (static, hosted via GitHub Pages) |
| `node_health.py` | USB-connected diagnostic — runs 7-point meshmap visibility check |
| `reset_keys.py` | Force PKI key regen (workaround for meshtastic CLI bug) |

## Hardware notes

The Danvers node is a **RAKwireless WisMesh Repeater Mini** (RAK4631 / nRF52840), flashed with the NomadStar Meteor Pro firmware build. nRF52840 has no WiFi — MQTT uplink is via neighbor gateway nodes on the public LongFast channel.
