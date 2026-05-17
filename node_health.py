"""Quick health-check for the Farls Danvers Solar Meshtastic node (or any local node).

Usage:
    python node_health.py            # defaults to COM9
    python node_health.py COM7       # specify a different port

Prints: battery, uptime, neighbor counts, MQTT-readiness checklist, and
whether the node is configured for meshmap visibility.
"""
import sys
import time
import meshtastic.serial_interface

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM9"

def fmt_uptime(secs):
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{int(d)}d")
    if h: parts.append(f"{int(h)}h")
    parts.append(f"{int(m)}m")
    return " ".join(parts)

def check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' -- ' + detail) if detail else ''}")
    return ok

print(f"\nConnecting to {PORT}...")
iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
time.sleep(2)

my = iface.localNode
cfg = my.localConfig
mod = my.moduleConfig
my_id = f"!{iface.myInfo.my_node_num:08x}"
me = iface.nodes.get(my_id, {})

# ---------- IDENTITY ----------
print("\n" + "=" * 64)
print("  IDENTITY")
print("=" * 64)
print(f"  Node ID:      {my_id}  (numeric: {iface.myInfo.my_node_num})")
print(f"  Long name:    {me.get('user', {}).get('longName', '?')}")
print(f"  Short name:   {me.get('user', {}).get('shortName', '?')}")
print(f"  Hardware:     {me.get('user', {}).get('hwModel', '?')}")
print(f"  Firmware:     {iface.metadata.firmware_version if hasattr(iface, 'metadata') else '?'}")
pub = cfg.security.public_key.hex() if cfg.security.public_key else ""
print(f"  Public key:   {pub[:32]}{'...' if len(pub) > 32 else ''}")

# ---------- HEALTH ----------
print("\n" + "=" * 64)
print("  HEALTH")
print("=" * 64)
metrics = me.get("deviceMetrics", {})
batt = metrics.get("batteryLevel", "?")
volt = metrics.get("voltage", "?")
ch_util = metrics.get("channelUtilization", "?")
air_tx = metrics.get("airUtilTx", "?")
uptime = metrics.get("uptimeSeconds", 0)

print(f"  Battery:      {batt}% @ {volt}V")
print(f"  Uptime:       {fmt_uptime(uptime)}")
print(f"  Channel util: {ch_util}%")
print(f"  Air-time TX:  {air_tx}%")

# ---------- MESH ----------
print("\n" + "=" * 64)
print("  MESH NEIGHBORS")
print("=" * 64)
nodes = iface.nodes
direct = [n for n in nodes.values() if n.get("hopsAway") == 0 and n.get("num") != iface.myInfo.my_node_num]
one_hop = [n for n in nodes.values() if n.get("hopsAway") == 1]
total = len(nodes) - 1  # minus ourselves
print(f"  Total nodes known:  {total}")
print(f"  Direct (0 hops):    {len(direct)}")
print(f"  1-hop neighbors:    {len(one_hop)}")
if direct:
    print("\n  Directly heard:")
    for n in direct[:8]:
        u = n.get("user", {})
        snr = n.get("snr", "?")
        last = n.get("lastHeard", 0)
        age = int(time.time() - last) if last else None
        age_str = f"{age//60}m ago" if age else "?"
        print(f"    {u.get('shortName','?'):<6} {u.get('longName','?'):<30} SNR {snr}  ({age_str})")

# ---------- MESHMAP-READINESS ----------
print("\n" + "=" * 64)
print("  MESHMAP.NET VISIBILITY CHECKLIST")
print("=" * 64)
ok_pubkey = bool(cfg.security.public_key) and pub != "8GLK6yumkBC8Iw+OSkke8n0y8wUQ7Kkd+nbdT2T8bkw"
check("Unique public key (not NomadStar default)", ok_pubkey,
      "key is still the NomadStar default! Run reset_keys.py" if not ok_pubkey else "")

check("Region set to US", cfg.lora.region == 1, f"region code = {cfg.lora.region}")

check("config_ok_to_mqtt = True", cfg.lora.config_ok_to_mqtt,
      "set with: meshtastic --set lora.config_ok_to_mqtt true")

pos = me.get("position", {})
has_pos = "latitude" in pos and "longitude" in pos
check("Position is being broadcast", has_pos,
      f"{pos.get('latitude','?')}, {pos.get('longitude','?')}" if has_pos else "no position")

check("Position is fixed (not relying on GPS)", cfg.position.fixed_position,
      "this is a stationary install -- fixed_position=True saves power and avoids drift")

# Channel uplink check via primary channel
prim = next((c for c in my.channels if c.role == 1), None)  # PRIMARY=1
if prim:
    ok_uplink = prim.settings.uplink_enabled
    check("Channel 0 uplink_enabled = True", ok_uplink,
          "set with: meshtastic --ch-index 0 --ch-set uplink_enabled true")

# Role
role_names = {0:"CLIENT", 1:"CLIENT_MUTE", 2:"ROUTER", 4:"REPEATER", 5:"TRACKER",
              6:"SENSOR", 7:"TAK", 8:"CLIENT_HIDDEN", 9:"LOST_AND_FOUND",
              10:"TAK_TRACKER", 11:"ROUTER_LATE"}
role_name = role_names.get(cfg.device.role, f"unknown({cfg.device.role})")
ok_role = cfg.device.role in (0, 11)  # CLIENT or ROUTER_LATE are both meshmap-friendly
check(f"Role = {role_name}", ok_role,
      "REPEATER role won't broadcast user info to meshmap -- use ROUTER_LATE instead" if not ok_role else "")

# ---------- LINKS ----------
print("\n" + "=" * 64)
print("  LINKS")
print("=" * 64)
print(f"  Your node on meshmap:   https://meshmap.net/?node_id={iface.myInfo.my_node_num}")
print(f"  Your local mesh area:   https://meshmap.net/#map=13/{pos.get('latitude','?')}/{pos.get('longitude','?')}")
print(f"  Web client (USB/BLE):   https://client.meshtastic.org/")

iface.close()
print("\nDone.\n")
