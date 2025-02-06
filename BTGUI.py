import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import asyncio
import threading
from bleak import BleakScanner, BleakClient

class BluetoothLEScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth LE Scanner & Data Receiver")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        self.client = None
        self.devices = {}

        # ---- Status Bar ----
        self.status_bar = tk.Label(root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # ---- Main Frames ----
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ---- LEFT PANEL (Device List & Actions) ----
        self.left_frame = tk.LabelFrame(self.main_frame, text="Scan & Connect", font=("Arial", 12, "bold"))
        self.left_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

        self.listbox = tk.Listbox(self.left_frame, font=("Arial", 12), height=12)
        self.listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        self.scan_button = ttk.Button(self.left_frame, text="Scan for BLE Devices", command=self.start_scan)
        self.scan_button.pack(pady=5)

        self.connect_button = ttk.Button(self.left_frame, text="Connect & Receive Data", command=self.connect_to_device)
        self.connect_button.pack(pady=5)

        self.disconnect_button = ttk.Button(self.left_frame, text="Disconnect", command=self.disconnect_device, state=tk.DISABLED)
        self.disconnect_button.pack(pady=5)

        self.write_button = ttk.Button(self.left_frame, text="Write Data", command=self.write_to_device, state=tk.DISABLED)
        self.write_button.pack(pady=5)

        # ---- RIGHT PANEL (Device Info & Services) ----
        self.right_frame = tk.LabelFrame(self.main_frame, text="Device Information", font=("Arial", 12, "bold"))
        self.right_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=True)

        self.info_label = tk.Label(self.right_frame, text="Device Details:", font=("Arial", 10, "bold"))
        self.info_label.pack(pady=5)

        self.device_info = tk.Text(self.right_frame, height=6, width=60, font=("Arial", 10))
        self.device_info.pack(padx=5, pady=5, fill=tk.X)

        self.services_label = tk.Label(self.right_frame, text="Services & Characteristics:", font=("Arial", 10, "bold"))
        self.services_label.pack(pady=5)

        self.services_tree = ttk.Treeview(self.right_frame, columns=("UUID", "Properties", "RSSI"), show="headings", height=8)
        self.services_tree.heading("UUID", text="UUID")
        self.services_tree.heading("Properties", text="Properties")
        self.services_tree.heading("RSSI", text="RSSI (dBm)")
        self.services_tree.column("UUID", width=250)
        self.services_tree.column("Properties", width=180)
        self.services_tree.column("RSSI", width=100)
        self.services_tree.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    # ---- STATUS BAR UPDATE ----
    def update_status(self, text):
        self.status_bar.config(text=f"Status: {text}")
        self.root.update_idletasks()

    # ---- SCANNING ----
    def start_scan(self):
        self.update_status("Scanning for BLE devices...")
        self.listbox.delete(0, tk.END)
        threading.Thread(target=self.scan_ble_devices, daemon=True).start()

    def scan_ble_devices(self):
        asyncio.run(self.async_scan_ble())

    async def async_scan_ble(self):
        try:
            self.listbox.delete(0, tk.END)
            self.devices.clear()

            def callback(device, advertisement_data):
                rssi = advertisement_data.rssi
                display_name = f"{device.name or 'Unknown'} ({device.address}) - RSSI: {rssi} dBm"
                self.devices[display_name] = {"address": device.address, "rssi": rssi}

                self.listbox.insert(tk.END, display_name)

            scanner = BleakScanner(callback)
            await scanner.start()
            await asyncio.sleep(5)  # Scan duration
            await scanner.stop()

            if not self.devices:
                self.listbox.insert(tk.END, "No BLE devices found.")

            self.update_status("Scan complete.")

        except Exception as e:
            self.update_status(f"Scan Error: {e}")

    # ---- CONNECT TO DEVICE ----
    def connect_to_device(self):
        selected_index = self.listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No Device Selected", "Please select a device.")
            return

        device_name = self.listbox.get(selected_index)
        device_info = self.devices.get(device_name)

        if not device_info:
            messagebox.showerror("Connection Error", "Invalid device selected.")
            return

        self.device_info.delete("1.0", tk.END)
        self.device_info.insert(tk.END, f"Connecting to {device_name}...\n")

        self.update_status(f"Connecting to {device_name}...")

        threading.Thread(target=self.run_async_read_ble_data, args=(device_info["address"],), daemon=True).start()

    def run_async_read_ble_data(self, device_address):
        asyncio.run(self.async_read_ble_data(device_address))

    async def async_read_ble_data(self, device_address):
        try:
            self.client = BleakClient(device_address)
            await self.client.connect()

            self.update_status(f"Connected to {device_address}")
            self.disconnect_button.config(state=tk.NORMAL)
            self.write_button.config(state=tk.NORMAL)

            self.device_info.insert(tk.END, "Connected!\n")

            services = await self.client.get_services()
            self.services_tree.delete(*self.services_tree.get_children())

            for service in services:
                for characteristic in service.characteristics:
                    props = ", ".join(characteristic.properties)
                    rssi = self.devices.get(device_address, {}).get("rssi", "N/A")
                    self.services_tree.insert("", "end", values=(characteristic.uuid, props, f"{rssi} dBm"))

        except Exception as e:
            self.device_info.insert(tk.END, f"Connection Failed: {e}\n")
            self.update_status("Connection Failed.")

    # ---- WRITE TO DEVICE ----
    def write_to_device(self):
        if not self.client or not self.client.is_connected:
            messagebox.showerror("Error", "Not connected to any device.")
            return

        uuid = simpledialog.askstring("Input", "Enter UUID of characteristic to write to:")
        data = simpledialog.askstring("Input", "Enter data to write:")

        if uuid and data:
            asyncio.run(self.client.write_gatt_char(uuid, bytes(data, "utf-8")))

    # ---- DISCONNECT FROM DEVICE ----
    def disconnect_device(self):
        if self.client:
            asyncio.run(self.client.disconnect())

        self.update_status("Disconnected")
        self.disconnect_button.config(state=tk.DISABLED)
        self.device_info.insert(tk.END, "Disconnected\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothLEScannerApp(root)
    root.mainloop()
