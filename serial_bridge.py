"""
Optional ESP32 Bluetooth serial helper.
Install requirements, pair your computer with the ESP32, then set the correct COM
port (Windows) or /dev/rfcomm0 (Linux) below. This is a starter integration;
Bluetooth pairing/port names vary by operating system and ESP32 firmware.
"""
import serial
import time

PORT = "COM5"       # Change this to your Bluetooth serial port
BAUD = 115200

def send_command(command: str):
    with serial.Serial(PORT, BAUD, timeout=2) as connection:
        connection.write((command.strip() + "\\n").encode("utf-8"))
        time.sleep(0.2)
        return connection.readline().decode("utf-8", errors="replace").strip()

if __name__ == "__main__":
    print("ESP32 response:", send_command("ON"))
