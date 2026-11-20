/*
  Smart LED Bluetooth demo firmware - ESP32 Classic Bluetooth
  Board: ESP32 DevKit V1 (Bluetooth Classic supported)
  LED output: GPIO 2 (change LED_PIN if your wiring differs)
  Pair Windows with device name: ESP32_LED
  Windows: Settings > Bluetooth & devices > Devices > More Bluetooth settings > COM Ports
  Select the OUTGOING COM port in the dashboard's Real COM mode.
  Protocol:
    ON
    OFF
    DIM,70
    STATUS
  STATUS response: STATUS,<0-or-1>,<brightness 0-100>
*/
#include "BluetoothSerial.h"
BluetoothSerial SerialBT;
const int LED_PIN = 2;
const int PWM_CHANNEL = 0;
const int PWM_FREQ = 5000;
const int PWM_RESOLUTION = 8;
int brightness = 0;
bool ledOn = false;

void applyLed() {
  int duty = ledOn ? map(brightness, 0, 100, 0, 255) : 0;
  ledcWrite(PWM_CHANNEL, duty);
}
void setup() {
  Serial.begin(115200);
  ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(LED_PIN, PWM_CHANNEL);
  applyLed();
  SerialBT.begin("ESP32_LED");
}
void loop() {
  if (!SerialBT.available()) return;
  String cmd = SerialBT.readStringUntil('\n');
  cmd.trim(); cmd.toUpperCase();
  if (cmd == "ON") { ledOn = true; if (brightness == 0) brightness = 70; applyLed(); }
  else if (cmd == "OFF") { ledOn = false; brightness = 0; applyLed(); }
  else if (cmd.startsWith("DIM,")) {
    int value = cmd.substring(4).toInt();
    brightness = constrain(value, 0, 100);
    ledOn = brightness > 0; applyLed();
  } else if (cmd == "STATUS") {
    SerialBT.printf("STATUS,%d,%d\n", ledOn ? 1 : 0, brightness);
  }
}
