# WebSocket Server for JetBot
# Sends Image Data to the Web App
# Sends Control Data to the ADK API Control Plane

import asyncio
import websockets
import json
import base64
import cv2
import numpy as np

class WebSocketServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.clients = []

    async def start(self):
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"WebSocket server started on {self.host}:{self.port}")

    async def handle_client(self, websocket, path):
        self.clients.append(websocket)
        print(f"New client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                print(f"Received message: {message}")
                
    async def send_image(self, image: np.ndarray):
        if not self.clients:
            return
        
        image_data = cv2.imencode('.jpg', image)[1].tobytes()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        for client in self.clients:
            try:
                await client.send(base64_image)
            except websockets.exceptions.ConnectionClosed:
                self.clients.remove(client)
                print(f"Client disconnected: {client.remote_address}")
                
    async def send_control_data(self, control_data: dict):
        if not self.clients:
            return
        
        for client in self.clients:
            try:
                await client.send(json.dumps(control_data))
            except websockets.exceptions.ConnectionClosed:
                self.clients.remove(client)
                print(f"Client disconnected: {client.remote_address}")
                
    async def stop(self):
        if self.server:
            await self.server.close()
            print("WebSocket server stopped")