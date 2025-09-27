# websocket.py
# WebSocket server for JetBot:
# - Manages client connections
# - Sends JPEG frames + control data with backpressure (latest-only)

import asyncio
import json
import base64
import websockets
from dataclasses import dataclass

@dataclass
class _Client:
    ws: websockets.WebSocketClientProtocol
    queue: asyncio.Queue
    task: asyncio.Task


class WebSocketServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.clients: list[_Client] = []
        self._lock = asyncio.Lock()

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
            async for _ in ws:
                pass
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

    # ---------- Public API ----------

    async def broadcast_jpeg_payload(self, jpeg_bytes: bytes, left_motor: float = 0.0, right_motor: float = 0.0):
        """Send image+control as JSON to all clients (latest-only)."""
        base64_image = base64.b64encode(jpeg_bytes).decode("utf-8")
        msg = json.dumps({
            "image": base64_image,
            "left_motor": left_motor,
            "right_motor": right_motor
        })
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
