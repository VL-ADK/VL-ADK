# websocket.py
# WebSocket server for JetBot:
# - Manages client connections
# - Sends JPEG frames + control data with backpressure (latest-only)

import asyncio
import base64
import json
from dataclasses import dataclass

import websockets


@dataclass
class _Client:
    ws: websockets.WebSocketClientProtocol
    queue: asyncio.Queue
    task: asyncio.Task


class WebSocketServer:
    def __init__(self, host: str, port: int, robot=None):
        self.host = host
        self.port = port
        self.server = None
        self.clients: list[_Client] = []
        self._lock = asyncio.Lock()
        self.robot = robot  # JetBot robot instance for direct control
        self._smooth_stop_task = None  # Track smooth stop task

    async def start(self):
        self.server = await websockets.serve(self._handle_client, self.host, self.port)
        print(f"WebSocket server started on {self.host}:{self.port}")

    async def _handle_client(self, ws):
        client = _Client(ws=ws, queue=asyncio.Queue(maxsize=1), task=None)
        async with self._lock:
            self.clients.append(client)
        print(f"New client connected: {ws.remote_address}")

        client.task = asyncio.create_task(self._client_sender(client))
        try:
            async for message in ws:
                # Handle incoming control messages
                await self._handle_control_message(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self._remove_client(client)

    async def _client_sender(self, client: _Client):
        try:
            while True:
                msg = await client.queue.get()
                await client.ws.send(msg)
        except Exception:
            await self._remove_client(client)

    async def _remove_client(self, client: _Client):
        async with self._lock:
            if client in self.clients:
                self.clients.remove(client)
        if client.task:
            client.task.cancel()
        try:
            await client.ws.close()
        except Exception:
            pass
        print(f"Client disconnected: {getattr(client.ws, 'remote_address', '?')}")

    async def _handle_control_message(self, message):
        """Handle incoming control messages from clients."""
        if not self.robot:
            return  # No robot available

        try:
            data = json.loads(message)
            action = data.get("action")

            # Extract speed parameters - allow both 'speed' and 'linear_velocity'
            linear_velocity = data.get("speed", data.get("linear_velocity", 0.3))
            angular_velocity = data.get("angular_velocity", linear_velocity)  # Use linear as fallback

            if action == "forward":
                print(f"WebSocket control: forward linear_velocity={linear_velocity} (direct motor control)")
                self.robot.left_motor.value = linear_velocity
                self.robot.right_motor.value = linear_velocity

            elif action == "backward":
                print(f"WebSocket control: backward linear_velocity={linear_velocity} (direct motor control)")
                self.robot.left_motor.value = -linear_velocity
                self.robot.right_motor.value = -linear_velocity

            elif action == "left":
                print(f"WebSocket control: left angular_velocity={angular_velocity} (direct motor control)")
                self.robot.left_motor.value = -angular_velocity
                self.robot.right_motor.value = angular_velocity

            elif action == "right":
                print(f"WebSocket control: right angular_velocity={angular_velocity} (direct motor control)")
                self.robot.left_motor.value = angular_velocity
                self.robot.right_motor.value = -angular_velocity

            elif action == "stop":
                print("WebSocket control: smooth stop (direct motor control)")
                await self._smooth_stop()

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Invalid control message: {e}")

    async def _smooth_stop(self):
        """Smoothly decelerate the robot to a stop over 1 second."""
        # Cancel any existing smooth stop task
        if self._smooth_stop_task and not self._smooth_stop_task.done():
            self._smooth_stop_task.cancel()

        # Start new smooth stop task
        self._smooth_stop_task = asyncio.create_task(self._decelerate_motors())

    async def _decelerate_motors(self):
        """Gradually reduce motor speeds to 0 over 1 second."""
        if not self.robot:
            return

        try:
            # Get current motor values
            initial_left = self.robot.left_motor.value
            initial_right = self.robot.right_motor.value

            # If motors are already stopped, nothing to do
            if abs(initial_left) < 0.01 and abs(initial_right) < 0.01:
                return

            # Decelerate over 1 second with 50ms steps (20 steps)
            steps = 20
            step_duration = 0.05  # 50ms per step

            for i in range(steps):
                if self.robot:  # Check robot still exists
                    # Linear interpolation from initial values to 0
                    progress = (i + 1) / steps  # 0.05, 0.10, ..., 1.0

                    # Apply easing for smoother deceleration (ease-out)
                    eased_progress = 1 - (1 - progress) ** 2

                    new_left = initial_left * (1 - eased_progress)
                    new_right = initial_right * (1 - eased_progress)

                    self.robot.left_motor.value = new_left
                    self.robot.right_motor.value = new_right

                await asyncio.sleep(step_duration)

            # Ensure completely stopped
            if self.robot:
                self.robot.left_motor.value = 0.0
                self.robot.right_motor.value = 0.0

        except asyncio.CancelledError:
            # Task was cancelled - immediately stop
            if self.robot:
                self.robot.left_motor.value = 0.0
                self.robot.right_motor.value = 0.0

    # ---------- Public API ----------

    async def broadcast_payload(self, jpeg_bytes: bytes, left_motor: float = 0.0, right_motor: float = 0.0, control=None):
        """Send image+control as JSON to all clients (latest-only)."""
        base64_image = base64.b64encode(jpeg_bytes).decode("utf-8")
        payload = {"image": base64_image, "left_motor": left_motor, "right_motor": right_motor}

        # Add control message if provided
        if control is not None:
            payload["control"] = control.dict() if hasattr(control, "dict") else control

        msg = json.dumps(payload)
        async with self._lock:
            for client in list(self.clients):
                await self._offer_latest(client.queue, msg)

    @staticmethod
    async def _offer_latest(q: asyncio.Queue, item: str):
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            try:
                _ = q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            finally:
                await q.put(item)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped")
        async with self._lock:
            for c in self.clients:
                try:
                    await c.ws.close()
                except Exception:
                    pass
            self.clients.clear()
