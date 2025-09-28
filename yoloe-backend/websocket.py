# yolo_websocket.py
# WebSocket server for YOLO-E:
# - Manages client connections
# - Sends annotated JPEG frames with detection data (latest-only)

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


class YoloWebSocketServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.clients: list[_Client] = []
        self._lock = asyncio.Lock()

    async def start(self):
        self.server = await websockets.serve(self._handle_client, self.host, self.port)
        print(f"YOLO WebSocket server started on {self.host}:{self.port}")

    async def _handle_client(self, ws):
        client = _Client(ws=ws, queue=asyncio.Queue(maxsize=1), task=None)
        async with self._lock:
            self.clients.append(client)
        print(f"New YOLO WebSocket client connected: {ws.remote_address}")

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
        print(f"YOLO WebSocket client disconnected: {getattr(client.ws, 'remote_address', '?')}")

    # ---------- Public API ----------
    async def broadcast_annotated_frame(self, annotated_jpeg_bytes: bytes, annotations: list, detection_data=None):
        """Send annotated image + detection data as JSON to all clients (latest-only)."""
        base64_image = base64.b64encode(annotated_jpeg_bytes).decode("utf-8")
        payload = {"image": base64_image, "annotations": annotations, "detection_count": len(annotations), "timestamp": detection_data.get("timestamp") if detection_data else None, "current_prompts": detection_data.get("current_prompts", []) if detection_data else [], "model_type": "YOLO-E"}

        # Add detection metadata if provided
        if detection_data:
            payload.update({"motor_data": detection_data.get("motor_data", {}), "frame_timestamp": detection_data.get("frame_timestamp"), "detection_timestamp": detection_data.get("detection_timestamp"), "image_shape": detection_data.get("image_shape")})

        msg = json.dumps(payload)
        async with self._lock:
            for client in list(self.clients):
                await self._offer_latest(client.queue, msg)

    async def broadcast_annotations(self, annotations: list, detection_data=None):
        """
        Send only annotation data as JSON to all clients (much faster than images).

        Format matches frontend YOLOObject type:
        {
            "type": "annotations",
            "objects": [
                {
                    "x": <bbox x position>,
                    "y": <bbox y position>,
                    "width": <bbox width>,
                    "height": <bbox height>,
                    "label": "class_name (confidence%) ↻45°"
                }
            ],
            "timestamp": <number>,
            "current_prompts": [...]
        }
        """
        timestamp = 0
        current_prompts = []

        if detection_data:
            timestamp = detection_data.get("timestamp", 0)
            current_prompts = detection_data.get("current_prompts", [])

        # Convert YOLO annotations to YOLOObject format
        yolo_objects = []
        for annotation in annotations:
            # Extract bbox coordinates [x, y, width, height]
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            x, y, width, height = bbox

            # Create label with class and confidence
            class_name = annotation.get("class", "unknown")
            confidence = annotation.get("confidence", 0.0)
            label = f"{class_name} ({int(confidence * 100)}%)"

            # Add rotation info if available
            if "rotation_degree" in annotation:
                rotation = annotation["rotation_degree"]
                arrow = "↻" if rotation > 0 else "↺"
                label += f" {arrow}{abs(int(rotation))}°"

            yolo_objects.append({"x": int(x), "y": int(y), "width": int(width), "height": int(height), "label": label})

        payload = {"type": "annotations", "objects": yolo_objects, "timestamp": timestamp, "current_prompts": current_prompts}

        msg = json.dumps(payload)
        print(f"[YOLO WebSocket] Broadcasting {len(yolo_objects)} objects to {len(self.clients)} clients")
        if yolo_objects:
            print(f"[YOLO WebSocket] First object: {yolo_objects[0]}")
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
            print("YOLO WebSocket server stopped")
        async with self._lock:
            for c in self.clients:
                try:
                    await c.ws.close()
                except Exception:
                    pass
            self.clients.clear()
