import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from bleak import BleakScanner, BleakClient

class BluetoothLEScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BLE Scanner & Data Receiver")
        self.root.geometry("900x500")

        # Bluetooth Scanner Section
        self.left_frame = tk.Frame(root)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)

        self.label = tk.Label(self.left_frame, text="Bluetooth Low Energy Scanner", font=("Arial", 14, "bold"))
        self.label.pack(pady=5)

        self.listbox = tk.Listbox(self.left_frame, font=("Arial", 12), height=15)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        self.scan_button = ttk.Button(self.left_frame, text="Scan for BLE Devices", command=self.start_scan)
        self.scan_button.pack(pady=5)

        self.connect_button = ttk.Button(self.left_frame, text="Connect & Receive Data", command=self.connect_to_device)
        self.connect_button.pack(pady=5)

        # Right Panel for Device Info & Services
        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.BOTH, expand=True)

        self.info_label = tk.Label(self.right_frame, text="Selected Device Info", font=("Arial", 12, "bold"))
        self.info_label.pack(pady=5)

        self.device_info = tk.Text(self.right_frame, height=10, width=50, font=("Arial", 12))
        self.device_info.pack(padx=5, pady=5)

        self.services_label = tk.Label(self.right_frame, text="Services & Characteristics", font=("Arial", 12, "bold"))
        self.services_label.pack(pady=5)

        self.services_text = tk.Text(self.right_frame, height=10, width=50, font=("Arial", 12))
        self.services_text.pack(padx=5, pady=5)

        self.devices = {}  # Store device addresses & advertisement data

    def start_scan(self):
        self.listbox.delete(0, tk.END)
        self.listbox.insert(tk.END, "Scanning for BLE devices...")
        thread = threading.Thread(target=self.scan_ble_devices, daemon=True)
        thread.start()

    def scan_ble_devices(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_scan_ble())

    async def async_scan_ble(self):
        try:
            devices = await BleakScanner.discover()
            self.listbox.delete(0, tk.END)
            self.devices.clear()
            
            if devices:
                for device in devices:
                    display_name = f"{device.name or 'Unknown'} ({device.address})"
                    self.listbox.insert(tk.END, display_name)
                    self.devices[display_name] = {
                        "address": device.address,
                        "uuids": device.metadata.get("uuids", []),
                        "manufacturer_data": device.metadata.get("manufacturer_data", {})
                    }
            else:
                self.listbox.insert(tk.END, "No BLE devices found.")
        except Exception as e:
            self.listbox.insert(tk.END, f"Error: {e}")

    def connect_to_device(self):
        selected_index = self.listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No Device Selected", "Please select a device from the list.")
            return

        device_name = self.listbox.get(selected_index)
        device_info = self.devices.get(device_name)

        if not device_info:
            messagebox.showerror("Connection Error", "Invalid device selected.")
            return

        self.device_info.delete("1.0", tk.END)
        self.device_info.insert(tk.END, f"Device: {device_name}\n")
        self.device_info.insert(tk.END, f"MAC Address: {device_info['address']}\n")
        self.device_info.insert(tk.END, f"UUIDs:\n")

        for uuid in device_info['uuids']:
            self.device_info.insert(tk.END, f"  - {uuid}\n")

        self.device_info.insert(tk.END, "\nManufacturer Data:\n")
        for key, value in device_info["manufacturer_data"].items():
            self.device_info.insert(tk.END, f"  - {key}: {value}\n")

        # Clear services info
        self.services_text.delete("1.0", tk.END)
        self.services_text.insert(tk.END, f"Connecting to {device_name}...\n")

        thread = threading.Thread(target=self.read_ble_data, args=(device_info["address"],), daemon=True)
        thread.start()

    def read_ble_data(self, device_address):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_read_ble_data(device_address))

    async def async_read_ble_data(self, device_address):
        try:
            async with BleakClient(device_address) as client:
                services = await client.get_services()
                self.services_text.insert(tk.END, "Connected! Services detected:\n")

                for service in services:
                    self.services_text.insert(tk.END, f"\n[Service] {service.uuid}\n")
                    for characteristic in service.characteristics:
                        props = ", ".join(characteristic.properties)
                        self.services_text.insert(tk.END, f"  - {characteristic.uuid} ({props})\n")

                        # Attempt to read characteristic data
                        if "read" in characteristic.properties:
                            try:
                                data = await client.read_gatt_char(characteristic.uuid)
                                self.services_text.insert(tk.END, f"    * Data: {data.hex()}\n")
                            except Exception as e:
                                self.services_text.insert(tk.END, f"    * Error reading: {e}\n")

        except Exception as e:
            self.services_text.insert(tk.END, f"Connection Failed: {e}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothLEScannerApp(root)
    root.mainloop()
