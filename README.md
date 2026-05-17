# Farley Mesh Fleet

**Purpose:** grid-down resilient comms between Mike (Danvers MA) and Jim (Kensington NH + Merrymeeting Lake NH) using pure-LoRa Meshtastic. Internet, WiFi, satellite, and cell are explicitly NOT in the threat model — when those go down, this still works.

🔗 **Live dashboard:** https://fructifyme.github.io/mesh-fleet/

## Fleet

| Site | Device | Role | Notes |
|---|---|---|---|
| Danvers, MA (Mike's roof) | RAK WisMesh Repeater Mini | ROUTER_LATE | Solar + 18650, hop_limit 7 |
| Jim's house + mobile | LILYGO T-Deck Plus EXT | CLIENT | Built-in screen+kbd, GPS, internal battery |
| Merrymeeting Lake (Jim's cabin) | RAK WisBlock Starter Kit | ROUTER_LATE | Fixed at the cabin, no Internet up there |

## Distance reality check (pure LoRa)

Travel corridor: **I-95 north** from Danvers to Kensington, then **Route 16 north** through Rochester / Wakefield, then **Route 11 west** to Alton / Merrymeeting Lake.

| Path | Direct distance | Status |
|---|---|---|
| Danvers → Kensington NH | 24 mi | Edge of single-hop; reachable with 2 hops + decent antennas |
| Danvers → Merrymeeting NH | 66 mi | Needs help in the middle — there's existing mesh density at the lake (3 nodes within 6 mi of cabin) but a gap between Kensington and Strafford County |

**Lake-end coverage already exists:** `KC1MUR_NewDurham` (2 mi from cabin), `GBC Wolfeboro` (4 mi), `PineconeNet-RAK3312-1` (6 mi). Jim's WisBlock should drop into that mesh as-is.

**The bottleneck is Strafford County NH** — only `Mastodon2` (Strafford) is visible there. A relay in Gonic/Rochester or Barrington would close the link.

LoRa LongFast typical real-world single-hop is 5-15 mi (much more with elevation/clear sight). Meshtastic max hop_limit is 7. The dashboard's Coverage Analysis section breaks this down with proposed relay locations + cost matrix.

## The MQTT bridge (opportunistic, not core)

When the PC is on with the node connected via USB, `mqtt_bridge.py` publishes the node's outbound packets to `mqtt.meshtastic.org` so the node also shows up on meshmap.net and the dashboard. **This is opportunistic visibility, not part of the grid-down comms path.** When the grid is down, the bridge is irrelevant — LoRa carries the message.

## How the data flows

```
Node (USB)  ──→  mqtt_bridge.py (this PC, native TCP)  ──→  mqtt.meshtastic.org:1883
                                                                       │
                                                                       ▼
                                                                 meshmap.net
                                                                       │
       refresh-fleet GitHub Action (every 5 min) ◄────── meshmap.net/nodes.json
                       │
                       ▼
                  fleet.json (in repo)
                       │
                       ▼
                  index.html (GitHub Pages)
```

The bridge is the gatekeeper. The dashboard is just a viewer of the snapshot that the GitHub Action assembles every 5 minutes.

## Why a PC bridge instead of just the phone app or web client

- `mqtt.meshtastic.org` is **TCP-only** — no WebSocket listener. So `client.meshtastic.org` (browser) physically can't publish to it.
- The Meshtastic phone app **can** publish via native TCP, but Android's background restrictions often kill the publish stream silently. Hard to debug.
- A Python script on a PC has native TCP and runs reliably — it's the most testable path. Long-term, swap for a 24/7 WiFi node (Heltec V3 ≈ $25) so the PC doesn't need to be on.

## Running the MQTT bridge

```bash
pip install meshtastic paho-mqtt
python mqtt_bridge.py            # defaults to COM9
python mqtt_bridge.py COM7       # different port
python mqtt_bridge.py --no-startup-ping COM9   # skip the test text on start
```

While the script runs, your node is on the public network. Stop it (Ctrl+C) and visibility stops within a few minutes.

To make it survive PC reboots, set it up as a Windows Scheduled Task (run at logon, with the highest privileges, and `python -u mqtt_bridge.py COM9` as the action).

## Adding a new node

1. Plug into PC via USB, identify the COM port
2. `python reset_keys.py` — regenerates unique PKI keys (needed for any node shipped with stock NomadStar firmware)
3. `python node_health.py COMx` — 7-point pre-deployment checklist
4. Import the FarleyFam channel URL via the Meshtastic phone app
5. Once the node is on meshmap, get its numeric node ID and add it to `FLEET_IDS` in `.github/workflows/refresh-fleet.yml`. The dashboard picks it up automatically within 5 min.

## Adding a mobile/tracker node to the dashboard

Edit the `SITES` array near the top of `index.html`'s `<script>` tag and add a new entry with `mobile: true, type: "tracker"`. The dashboard auto-renders a live trail as position updates arrive between polls.

## Privacy

- The FarleyFam channel PSK is **never** committed to this repo
- Stored in browser localStorage only — entered once per device via the ⚙ Settings dialog
- Encrypted messages travel through public MQTT but are unreadable without the PSK

## Files

| File | Purpose |
|---|---|
| `index.html` | The dashboard (static, hosted via GitHub Pages) |
| `mqtt_bridge.py` | PC-side MQTT gateway — bridges USB node ↔ `mqtt.meshtastic.org:1883` |
| `node_health.py` | USB-connected diagnostic — runs 7-point meshmap visibility check |
| `reset_keys.py` | Force PKI key regen (workaround for meshtastic CLI bug) |
| `.github/workflows/refresh-fleet.yml` | Runs every 5 min, pulls meshmap data, commits `fleet.json` |
| `fleet.json` | Auto-generated by the workflow — read by the dashboard |

## Hardware notes

The Danvers node is a **RAKwireless WisMesh Repeater Mini** (RAK4631 / nRF52840), flashed with the NomadStar Meteor Pro firmware build. nRF52840 has no WiFi, so the firmware's MQTT module must operate in **proxy-to-client mode** — it sends MQTT publishes via the USB/BLE connection to a connected client (phone app, web client, or this PC's `mqtt_bridge.py`).
