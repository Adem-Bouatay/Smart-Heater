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
    OUT = 0
    
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

GPIO = FakeGPIO()

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
    except Exception as e:
        print(f"Error reading temperature: {e}")
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
            websocket_tasks = [client.send(msg) for client in authenticated_clients]
            await asyncio.gather(*websocket_tasks, return_exceptions=True)
        await asyncio.sleep(1)  # Update more frequently for better responsiveness

async def handle_client(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            try:
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
                    websocket_tasks = [client.send(update) for client in authenticated_clients]
                    await asyncio.gather(*websocket_tasks, return_exceptions=True)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
            except Exception as e:
                print(f"Error handling message: {e}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        authenticated_clients.discard(websocket)
        print("Client disconnected")

async def main():
    # Setup GPIO
    GPIO.setmode(0)  # Mode doesn't matter for fake GPIO
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    
    # Start WebSocket server and notification task together
    async with websockets.serve(handle_client, "", WEBSOCKET_PORT):
        print(f"WebSocket server started on port {WEBSOCKET_PORT}")
        # Create the notification task but don't wait for it to complete
        notification_task = asyncio.create_task(notify_clients())
        # Keep the server running until interrupted
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            notification_task.cancel()
            try:
                await notification_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        GPIO.cleanup()