"""MQTT bridge: forwards proxy messages from a USB-connected Meshtastic node
to mqtt.meshtastic.org over plain TCP, and forwards incoming MQTT back to the
node.

This makes the PC act as the MQTT gateway when:
  - The node has mqtt.enabled + mqtt.proxy_to_client_enabled = true
  - The node has no WiFi (e.g. RAK4631) AND no neighbor gateway in RF range
  - You don't want to rely on the flaky phone app

Browser-based gateways (client.meshtastic.org) can't do this because
mqtt.meshtastic.org has no WebSocket endpoint. Python's native TCP works fine.

Usage:
    pip install meshtastic paho-mqtt
    python mqtt_bridge.py            # COM9 by default
    python mqtt_bridge.py COM7       # specify another port
"""
import sys
import time
import threading
import meshtastic.serial_interface
from pubsub import pub
import paho.mqtt.client as mqtt_client

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT      = _args[0] if _args else "COM9"
BROKER    = "mqtt.meshtastic.org"
BROKER_PORT = 1883
USERNAME  = "meshdev"
PASSWORD  = "large4cats"

# Topics to subscribe to so the node receives MQTT-originated traffic.
# Default: only FarleyFam (our private family channel). LongFast is excluded
# because (a) we already hear most LongFast traffic over LoRa from local
# neighbors, and (b) the public firehose is ~40+ packets/minute and floods
# the USB link. Add LongFast back here if you want full downlink redundancy.
SUBSCRIBE_TOPICS = [
    "msh/US/2/e/FarleyFam/#",
    "msh/US/2/c/FarleyFam/#",
]

UP   = 0   # node -> mqtt
DOWN = 0   # mqtt -> node
START = time.time()
mesh_iface = None


def ts():
    return time.strftime("%H:%M:%S")


# ---------- MQTT (paho) side ----------
def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    print(f"[{ts()}] [mqtt] connected to {BROKER}:{BROKER_PORT} (rc={rc})")
    for t in SUBSCRIBE_TOPICS:
        client.subscribe(t, qos=0)
        print(f"[{ts()}] [mqtt] subscribed: {t}")

def on_mqtt_disconnect(client, userdata, rc, properties=None, reason_code=None):
    print(f"[{ts()}] [mqtt] disconnected (rc={rc}) -- will auto-reconnect")

def on_mqtt_message(client, userdata, msg):
    """Receive a packet from the broker and hand it to the node."""
    global DOWN
    DOWN += 1
    print(f"[{ts()}] [mqtt -> node]  {msg.topic}  ({len(msg.payload)}B)  total down={DOWN}")
    if mesh_iface is not None:
        try:
            mesh_iface.sendMqttClientProxyMessage(msg.topic, msg.payload)
        except Exception as e:
            print(f"[{ts()}] [mqtt -> node] FAILED: {e}")

mqtt = mqtt_client.Client(
    callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
    client_id=f"py-bridge-{int(time.time())}",
)
mqtt.username_pw_set(USERNAME, PASSWORD)
mqtt.on_connect = on_mqtt_connect
mqtt.on_disconnect = on_mqtt_disconnect
mqtt.on_message = on_mqtt_message


# ---------- meshtastic (node) side ----------
def on_proxy_from_node(proxymessage=None, interface=None, **kwargs):
    """Receive a packet from the node and publish it to the broker."""
    global UP
    UP += 1
    topic = proxymessage.topic
    data  = bytes(proxymessage.data)
    retain = bool(proxymessage.retained)
    print(f"[{ts()}] [node -> mqtt]  {topic}  ({len(data)}B retain={retain})  total up={UP}")
    try:
        mqtt.publish(topic, data, qos=0, retain=retain)
    except Exception as e:
        print(f"[{ts()}] [node -> mqtt] FAILED: {e}")

pub.subscribe(on_proxy_from_node, "meshtastic.mqttclientproxymessage")


# ---------- Status thread ----------
def status_loop():
    while True:
        time.sleep(60)
        uptime = int(time.time() - START)
        h, m = divmod(uptime // 60, 60)
        print(f"[{ts()}] [status] uptime={h}h{m:02d}m  up={UP}  down={DOWN}")


# ---------- Main ----------
print(f"[{ts()}] connecting to node on {PORT}...")
mesh_iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
time.sleep(2)
my_num = mesh_iface.myInfo.my_node_num
my_id  = f"!{my_num:08x}"
print(f"[{ts()}] node connected: {my_id}  ({my_num})")

print(f"[{ts()}] connecting MQTT to {BROKER}:{BROKER_PORT}...")
mqtt.connect(BROKER, BROKER_PORT, keepalive=60)
mqtt.loop_start()

threading.Thread(target=status_loop, daemon=True).start()

print()
print("=" * 70)
print(f"  Bridge is RUNNING.  PC = MQTT gateway for {my_id}.")
print(f"  Anything the node would publish via MQTT now flows through here.")
print(f"  Press Ctrl+C to stop.")
print("=" * 70)
print()

# Send one test text on startup so we get a definitive [node -> mqtt] event.
# (Without this we'd wait up to 30 min for the next natural position broadcast.)
if "--no-startup-ping" not in sys.argv:
    try:
        time.sleep(1)
        msg = f"bridge online {time.strftime('%H:%M')}"
        print(f"[{ts()}] [startup-ping] sending text '{msg}' on channel 0...")
        mesh_iface.sendText(msg, channelIndex=0, wantAck=False)
    except Exception as e:
        print(f"[{ts()}] [startup-ping] FAILED: {e}")

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print(f"\n[{ts()}] stopping...")
finally:
    mqtt.loop_stop()
    try: mqtt.disconnect()
    except Exception: pass
    try: mesh_iface.close()
    except Exception: pass
    print(f"[{ts()}] clean shutdown.  final tally: up={UP}  down={DOWN}")
