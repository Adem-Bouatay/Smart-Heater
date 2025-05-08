import asyncio
import json
import random
import websockets

# --- CONFIG ---
RELAY_PIN = 17
WEBSOCKET_PORT = 8765
TARGET_TEMP = 22.0

# --- FAKE HARDWARE ---
class FakeGPIO:
    HIGH = 1
    LOW = 0

    @staticmethod
    def setmode(mode):
        pass

    @staticmethod
    def setup(pin, mode):
        pass

    @staticmethod
    def output(pin, state):
        print(f"Relay {'ON' if state else 'OFF'}")

    @staticmethod
    def cleanup():
        print("GPIO cleanup called")

GPIO = FakeGPIO

class FakeDHTDevice:
    def __init__(self):
        pass

    @property
    def temperature(self):
        return round(random.uniform(20.0, 28.0), 1)

dht_device = FakeDHTDevice()

clients = set()

def read_temperature():
    try:
        return round(dht_device.temperature, 1)
    except:
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

authenticated_clients = {}

async def handle_client(websocket):
    clients.add(websocket)
    authenticated = False
    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            if not authenticated:
                if data.get("type") == "login":
                    if data["username"] == "admin" and data["password"] == "1234":
                        authenticated_clients[websocket] = True
                        await websocket.send(json.dumps({"type": "auth", "success": True}))
                        authenticated = True
                    else:
                        await websocket.send(json.dumps({"type": "auth", "success": False}))
                continue

            # Only handle messages if authenticated
            if authenticated and "target" in data:
                global TARGET_TEMP
                TARGET_TEMP = float(data["target"])
    finally:
        clients.remove(websocket)
        authenticated_clients.pop(websocket, None)
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
