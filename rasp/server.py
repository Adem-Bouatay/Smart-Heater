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

authenticated_clients = set()

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
        if authenticated_clients:
            await asyncio.gather(*(client.send(msg) for client in authenticated_clients))
        await asyncio.sleep(1)  # Update more frequently for better responsiveness

async def handle_client(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            
            # Handle authentication
            if websocket not in authenticated_clients:
                if data.get("type") == "login":
                    if data.get("username") == "admin" and data.get("password") == "1234":
                        authenticated_clients.add(websocket)
                        await websocket.send(json.dumps({"type": "auth", "success": True}))
                        # Send initial state immediately after login
                        temp = read_temperature()
                        heating = control_heating(temp)
                        await websocket.send(json.dumps({
                            "temperature": temp,
                            "target": TARGET_TEMP,
                            "heating": heating
                        }))
                    else:
                        await websocket.send(json.dumps({"type": "auth", "success": False}))
                continue

            # Handle temperature updates from authenticated clients
            if "target" in data:
                global TARGET_TEMP
                TARGET_TEMP = float(data["target"])
                # Immediate update after temperature change
                temp = read_temperature()
                heating = control_heating(temp)
                update = json.dumps({
                    "temperature": temp,
                    "target": TARGET_TEMP,
                    "heating": heating
                })
                await asyncio.gather(*(client.send(update) for client in authenticated_clients))

    finally:
        authenticated_clients.discard(websocket)
        print("Client disconnected")

async def main():
    async with websockets.serve(handle_client, "", WEBSOCKET_PORT):
        await notify_clients()  # Start periodic updates

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    GPIO.cleanup()