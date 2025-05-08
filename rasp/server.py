import asyncio
import json
import adafruit_dht
import board
import RPi.GPIO as GPIO
import websockets

# --- CONFIG ---
RELAY_PIN = 17
WEBSOCKET_PORT = 8765
TARGET_TEMP = 22.0

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)

dht_device = adafruit_dht.DHT22(board.D4)

clients = set()

def read_temperature():
    try:
        return round(dht_device.temperature, 1)
    except RuntimeError:
        return None

def control_heating(current_temp):
    if current_temp is None:
        return False
    if current_temp < TARGET_TEMP:
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        return True
    else:
        GPIO.output(RELAY_PIN, GPIO.LOW)
        return False

async def notify_clients():
    while True:
        temp = read_temperature()
        heating = control_heating(temp)
        data = {
            "temperature": temp,
            "target": TARGET_TEMP,
            "heating": heating
        }
        msg = json.dumps(data)
        if clients:
            await asyncio.gather(*(client.send(msg) for client in clients))
        await asyncio.sleep(5)

async def handle_client(websocket):
    global TARGET_TEMP
    clients.add(websocket)
    print("Client connected")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            try:
                data = json.loads(message)
                if "target" in data:
                    TARGET_TEMP = float(data["target"])
                    print(f"New target temperature: {TARGET_TEMP}")
            except Exception as e:
                print("Error parsing message:", e)
    finally:
        clients.remove(websocket)
        print("Client disconnected")

async def main():
    async with websockets.serve(handle_client, "", WEBSOCKET_PORT):
        await notify_clients()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    GPIO.cleanup()
