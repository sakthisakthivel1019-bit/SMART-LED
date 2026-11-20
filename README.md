# Smart LED Control System — Live Demo + Bluetooth

## What is included
- Login protected Flask dashboard.
- **Demo Bluetooth mode:** click Connect to simulate a Bluetooth link and start a live stream of generated telemetry every 2 seconds. The page clearly labels this as simulated.
- LED ON/OFF/brightness controls in demo mode.
- Live analysis page: auto-refreshing command distribution, brightness trend, estimated power trend, and latest readings.
- SQLite stores readings and command events. No random historical records are inserted at startup.
- **Real Bluetooth Classic option:** pair a compatible ESP32 with Windows, select its outgoing Bluetooth COM port, and connect using Real COM mode.
- Arduino firmware in `firmware/esp32_bluetooth_led.ino`.

## Run on Windows
Open PowerShell in this folder:
```powershell
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000
Login: `admin` / `admin123`

## Demo presentation (no hardware required)
1. Open Dashboard.
2. Leave Connection mode as **Demo Bluetooth (simulated)**.
3. Click **Connect**.
4. Click Turn ON, Turn OFF, and Apply brightness.
5. Wait a few seconds. Live voltage/current/power/temperature estimates and readings update.
6. Open Analysis. Charts refresh every 3 seconds based on readings stored while connected.
7. Disconnect to stop collecting demo readings.

**Important:** Demo mode is a software simulation. It does not discover or connect to a physical Bluetooth device. Demo sensor values are illustrative estimates, not physical measurements.

## Connect a real ESP32 (Bluetooth Classic)
1. This included sketch targets a classic Bluetooth-capable ESP32 such as ESP32 DevKit V1. ESP32-C3 does not support Bluetooth Classic; BLE needs a different implementation.
2. Open `firmware/esp32_bluetooth_led.ino` in Arduino IDE, select your ESP32 board and port, then upload.
3. Wire an LED with a suitable current-limiting resistor to GPIO 2 (or change `LED_PIN`). Do not connect an LED directly without a resistor.
4. Pair `ESP32_LED` in Windows Bluetooth settings.
5. Find the **outgoing** Bluetooth serial COM port in Windows Bluetooth settings / Device Manager.
6. On Dashboard choose **Real ESP32 Bluetooth COM**, enter the port (example `COM5`), then Connect.
7. The app sends `ON`, `OFF`, `DIM,70`, and `STATUS` commands at 115200 baud.
8. The firmware responds to `STATUS` as `STATUS,<led 0|1>,<brightness 0..100>`.

Real COM mode reports only LED state and brightness returned by the firmware. Voltage, current, power and temperature show as unavailable because this sketch has no physical sensors attached. To measure those values, add suitable sensors and extend the firmware protocol.

## Data accuracy
- Demo telemetry is synthetic and visibly labelled as demo.
- Real mode reads LED state and brightness from the ESP32. It does not invent electrical sensor readings.
- Analysis uses actual readings captured by this running application; it starts empty rather than adding fabricated history.
- The life calculator is still an illustrative estimate based on the nominal value described on its page, not a measured hardware lifetime.

## Troubleshooting
- If `python` is not recognized, install Python from https://www.python.org/downloads/windows/ and tick **Add python.exe to PATH**.
- If the COM port cannot open, close Arduino Serial Monitor and other apps using that port; verify you selected the outgoing Bluetooth COM port.
- If your ESP32 board does not support `BluetoothSerial.h`, use Demo mode for presentation or ask for a BLE firmware/browser variant.
