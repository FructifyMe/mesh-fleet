"""Force a full factory-reset-device on the connected node (regenerates PKI keys).
Works around the meshtastic CLI bug where --factory-reset-device sends bool, not int."""
import time
import sys
import meshtastic.serial_interface
import meshtastic.protobuf.admin_pb2 as admin_pb2

PORT = "COM9"

print(f"Connecting to {PORT}...")
iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
time.sleep(2)

my_node = iface.localNode
print(f"Connected. Node num: {iface.myInfo.my_node_num}")
print(f"Current public key (before reset): {iface.localNode.localConfig.security.public_key.hex()[:32]}...")

print("\nSending factory_reset_device admin message (regenerates PKI keys)...")
p = admin_pb2.AdminMessage()
p.factory_reset_device = 2  # int -- magic value, anything non-zero triggers it
my_node._sendAdmin(p)

print("Admin message sent. Device will reboot.")
print("Waiting 20 seconds for reboot...")
iface.close()
time.sleep(20)

print("\nReconnecting to verify new keys...")
iface2 = meshtastic.serial_interface.SerialInterface(devPath=PORT)
time.sleep(3)
new_pub = iface2.localNode.localConfig.security.public_key.hex()
print(f"New public key (after reset): {new_pub[:32]}...")
iface2.close()
print("Done.")
