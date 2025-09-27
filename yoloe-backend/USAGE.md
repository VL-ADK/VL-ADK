# YOLO-E Backend API Usage Guide

## Overview

The YOLO-E backend provides real-time object detection with open-vocabulary capabilities. It receives camera feeds from the JetBot and streams annotated video with bounding boxes and detection data.

## Port Mapping

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Detection API** | `8001` | HTTP/REST | Object detection, prompt management, debug |
| **Annotated Stream** | `8002` | WebSocket | Live annotated video feed with bounding boxes |

## Base URLs

- **API Base URL**: `http://127.0.0.1:8001`
- **WebSocket URL**: `ws://127.0.0.1:8002`

## Data Flow

```
JetBot Camera (8890) -> YOLO-E Backend -> API (8001) + Annotated Stream (8002)
```

---

# REST API Endpoints

## Object Detection API (Port 8001)

### GET /yolo/
Get object detection results from current camera frame.

**Request:**
```bash
GET /yolo/?words=person&words=bottle&words=car
```

**Parameters:**
- `words` (string[], optional): Target object classes to detect

**Response:**
```json
{
  "annotations": [
    {
      "class": "person",
      "confidence": 0.8234,
      "bbox": [100, 50, 300, 400],
      "center": [200.0, 225.0],
      "area": 70000,
      "prompt_index": 0
    }
  ],
  "count": 1,
  "timestamp": 1758992671.631,
  "image_shape": [1232, 1640, 3],
  "current_prompts": ["person", "bottle", "car"],
  "model_type": "YOLO-E",
  "motor_data": {
    "left_motor": 0.0,
    "right_motor": 0.0
  },
  "frame_timestamp": 1758992670.990,
  "detection_timestamp": 1758992671.631
}
```

**Response Schema:**
```typescript
interface YoloDetectionResponse {
  annotations: DetectionAnnotation[];
  count: number;
  timestamp: number;
  image_shape: [number, number, number];  // [height, width, channels]
  current_prompts: string[];
  model_type: "YOLO-E";
  motor_data: {
    left_motor: number;
    right_motor: number;
  };
  frame_timestamp: number;
  detection_timestamp: number;
}

interface DetectionAnnotation {
  class: string;           // Object class name
  confidence: number;      // Detection confidence [0.0-1.0]
  bbox: [number, number, number, number];  // [x1, y1, x2, y2]
  center: [number, number];  // [x, y] center coordinates
  area: number;            // Bounding box area in pixels
  prompt_index: number;    // Index in current_prompts array
}
```

**Error Response:**
```json
{
  "error": "No image available from WebSocket stream",
  "annotations": [],
  "count": 0
}
```

---

### POST /prompts/
Set new open-vocabulary detection prompts.

**Request:**
```bash
POST /prompts/
Content-Type: application/json

["person", "bottle", "car", "dog"]
```

**Body:** Array of strings (object class names)

**Response:**
```json
{
  "success": true,
  "current_prompts": ["person", "bottle", "car", "dog"],
  "message": "Prompts set to: ['person', 'bottle', 'car', 'dog']"
}
```

**Response Schema:**
```typescript
interface SetPromptsResponse {
  success: boolean;
  current_prompts: string[];
  message: string;
}
```

**Error Response:**
```json
{
  "success": false,
  "current_prompts": [],
  "message": "YOLO-E model not loaded"
}
```

---

### GET /prompts/
Get currently active detection prompts.

**Request:**
```bash
GET /prompts/
```

**Response:**
```json
{
  "current_prompts": ["person", "bottle", "car"],
  "model_loaded": true,
  "device": "cuda"
}
```

**Response Schema:**
```typescript
interface GetPromptsResponse {
  current_prompts: string[];
  model_loaded: boolean;
  device: "cuda" | "cpu";
}
```

---

### GET /health/
Check YOLO-E backend health and status.

**Request:**
```bash
GET /health/
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_type": "YOLO-E",
  "current_prompts": ["person", "bottle"],
  "device": "cuda",
  "latest_frame_age": 0.0312,
  "websocket_connected": true
}
```

**Response Schema:**
```typescript
interface HealthResponse {
  status: "healthy" | "unhealthy";
  model_loaded: boolean;
  model_type: "YOLO-E";
  current_prompts: string[];
  device: "cuda" | "cpu";
  latest_frame_age: number | null;  // Seconds since last frame
  websocket_connected: boolean;
}
```

---

### GET /debug/save_annotated
Save current frame with annotations to debug directory (server-side).

**Request:**
```bash
GET /debug/save_annotated?words=person&words=bottle
```

**Parameters:**
- `words` (string[], optional): Target words to detect and annotate

**Response:**
```json
{
  "saved": true,
  "image_path": "./debug_images/yolo_debug_20250927_123456_person_bottle.jpg",
  "metadata_path": "./debug_images/yolo_debug_20250927_123456_person_bottle_metadata.json",
  "detection_count": 2,
  "prompts": ["person", "bottle"],
  "annotations": [...]
}
```

**Response Schema:**
```typescript
interface DebugSaveResponse {
  saved: boolean;
  image_path?: string;        // Server-side file path
  metadata_path?: string;     // Server-side metadata file path  
  detection_count?: number;
  prompts?: string[];
  annotations?: DetectionAnnotation[];
  error?: string;            // Present if saved: false
}
```

---

# WebSocket API

## Annotated Video Stream (Port 8002)

### Connection
```javascript
const ws = new WebSocket('ws://127.0.0.1:8002');
```

### Message Format

**Received Messages:**
```json
{
  "image": "base64_encoded_jpeg_with_bounding_boxes",
  "annotations": [
    {
      "class": "person",
      "confidence": 0.8234,
      "bbox": [100, 50, 300, 400],
      "center": [200.0, 225.0],
      "area": 70000,
      "prompt_index": 0
    }
  ],
  "detection_count": 1,
  "timestamp": 1758992671.631,
  "current_prompts": ["person", "bottle"],
  "model_type": "YOLO-E",
  "motor_data": {
    "left_motor": 0.0,
    "right_motor": 0.0
  },
  "frame_timestamp": 1758992670.990,
  "detection_timestamp": 1758992671.631,
  "image_shape": [1232, 1640, 3]
}
```

**Message Schema:**
```typescript
interface YoloWebSocketMessage {
  image: string;                    // Base64 JPEG with bounding boxes drawn
  annotations: DetectionAnnotation[];
  detection_count: number;
  timestamp: number;               // Detection processing timestamp
  current_prompts: string[];
  model_type: "YOLO-E";
  motor_data: {
    left_motor: number;
    right_motor: number;
  };
  frame_timestamp: number;         // Original camera frame timestamp
  detection_timestamp: number;     // When detection was completed
  image_shape: [number, number, number];  // [height, width, channels]
}
```

### Stream Features

- **Pre-annotated Images**: Bounding boxes already drawn on frames
- **Real-time Detection**: Live object detection results
- **Backpressure Handling**: Latest frame only (no buffering)
- **Multiple Clients**: Supports multiple WebSocket connections
- **Frame Rate**: ~10 FPS (detection processing)

---

# Frontend Integration

## React Component Example

```tsx
import React, { useEffect, useState, useRef } from 'react';

interface DetectionData {
  annotations: DetectionAnnotation[];
  current_prompts: string[];
  detection_count: number;
  motor_data: { left_motor: number; right_motor: number };
}

const YoloStreamViewer: React.FC = () => {
  const [detectionData, setDetectionData] = useState<DetectionData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const imgRef = useRef<HTMLImageElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to YOLO-E WebSocket
    const ws = new WebSocket('ws://127.0.0.1:8002');
    wsRef.current = ws;

    ws.onopen = () => setConnectionStatus('connected');
    ws.onclose = () => setConnectionStatus('disconnected');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Update detection data
      setDetectionData({
        annotations: data.annotations,
        current_prompts: data.current_prompts,
        detection_count: data.detection_count,
        motor_data: data.motor_data
      });
      
      // Update image (already has bounding boxes)
      if (imgRef.current) {
        imgRef.current.src = `data:image/jpeg;base64,${data.image}`;
      }
    };

    return () => ws.close();
  }, []);

  // Robot control functions
  const moveRobot = async (direction: string, speed = 0.5, duration?: number) => {
    const params = new URLSearchParams({ speed: speed.toString() });
    if (duration) params.append('duration', duration.toString());
    
    const response = await fetch(`http://127.0.0.1:8889/${direction}/?${params}`, {
      method: 'POST'
    });
    return response.json();
  };

  const setPrompts = async (prompts: string[]) => {
    const response = await fetch('http://127.0.0.1:8001/prompts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prompts)
    });
    return response.json();
  };

  return (
    <div>
      <div>Status: {connectionStatus}</div>
      
      {/* Annotated Video Feed */}
      <img ref={imgRef} alt="Annotated Camera Feed" />
      
      {/* Detection Info */}
      {detectionData && (
        <div>
          <p>Detections: {detectionData.detection_count}</p>
          <p>Prompts: {detectionData.current_prompts.join(', ')}</p>
          <p>Motors: L={detectionData.motor_data.left_motor}, R={detectionData.motor_data.right_motor}</p>
        </div>
      )}
      
      {/* Robot Controls */}
      <div>
        <button onClick={() => moveRobot('forward', 0.5, 1)}>Forward</button>
        <button onClick={() => moveRobot('left', 0.3, 0.5)}>Left</button>
        <button onClick={() => moveRobot('right', 0.3, 0.5)}>Right</button>
        <button onClick={() => moveRobot('backward', 0.5, 1)}>Backward</button>
        <button onClick={() => fetch('http://127.0.0.1:8889/stop/', {method: 'POST'})}>Stop</button>
      </div>
      
      {/* Prompt Controls */}
      <div>
        <button onClick={() => setPrompts(['person', 'bottle'])}>Detect People & Bottles</button>
        <button onClick={() => setPrompts(['car', 'bicycle'])}>Detect Vehicles</button>
      </div>
    </div>
  );
};
```

## Python Client Example

```python
import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import requests

class YoloClient:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8001"
        self.robot_api = "http://127.0.0.1:8889"
        self.ws_url = "ws://127.0.0.1:8002"
    
    async def stream_processor(self):
        """Process annotated video stream."""
        async with websockets.connect(self.ws_url) as ws:
            async for message in ws:
                data = json.loads(message)
                
                # Process detection data
                print(f"Detected {data['detection_count']} objects:")
                for ann in data['annotations']:
                    print(f"  {ann['class']}: {ann['confidence']:.2f}")
                
                # Decode and display image (optional)
                image_bytes = base64.b64decode(data['image'])
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                cv2.imshow('YOLO-E Stream', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    
    def set_prompts(self, prompts):
        """Set detection prompts."""
        response = requests.post(f"{self.api_base}/prompts/", json=prompts)
        return response.json()
    
    def get_detection(self, words=None):
        """Get current detection results."""
        params = {"words": words} if words else {}
        response = requests.get(f"{self.api_base}/yolo/", params=params)
        return response.json()
    
    def move_robot(self, direction, speed=0.5, duration=None):
        """Control robot movement."""
        params = {"speed": speed}
        if duration:
            params["duration"] = duration
        response = requests.post(f"{self.robot_api}/{direction}/", params=params)
        return response.json()

# Usage
client = YoloClient()
client.set_prompts(["person", "bottle"])
asyncio.run(client.stream_processor())
```

---

# Error Handling

## HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `422` | Validation Error (invalid parameters) |
| `500` | Internal Server Error |

## Common Error Responses

### Detection API Errors
```json
{
  "error": "No image available from WebSocket stream",
  "annotations": [],
  "count": 0
}
```

```json
{
  "error": "Image data is stale",
  "annotations": [],
  "count": 0,
  "age_seconds": 6.23
}
```

### Prompt Setting Errors
```json
{
  "success": false,
  "current_prompts": [],
  "message": "YOLO-E model not loaded"
}
```

---

# WebSocket Message Types

## Annotated Video Stream

The WebSocket streams **pre-annotated JPEG images** with bounding boxes already drawn. This is different from raw detection data.

### Key Features:
- **Visual annotations**: Bounding boxes, labels, confidence scores already drawn
- **Color-coded boxes**: Different colors for different object classes
- **Real-time updates**: ~10 FPS detection processing
- **Multiple clients**: Supports multiple simultaneous connections
- **Backpressure handling**: Always delivers latest frame

### Image Format:
- **Type**: JPEG with annotations drawn
- **Encoding**: Base64 string
- **Resolution**: 1640x1232 (from JetBot camera)
- **Features**: Bounding boxes, class labels, confidence scores, center points

---

# Advanced Usage

## Dynamic Prompt Management

```javascript
class PromptManager {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8001';
  }
  
  async setPrompts(prompts) {
    const response = await fetch(`${this.apiBase}/prompts/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prompts)
    });
    return response.json();
  }
  
  async getCurrentPrompts() {
    const response = await fetch(`${this.apiBase}/prompts/`);
    return response.json();
  }
  
  async getDetections(words = null) {
    const params = words ? `?${words.map(w => `words=${w}`).join('&')}` : '';
    const response = await fetch(`${this.apiBase}/yolo/${params}`);
    return response.json();
  }
  
  async saveDebugImage(words = null) {
    const params = words ? `?${words.map(w => `words=${w}`).join('&')}` : '';
    const response = await fetch(`${this.apiBase}/debug/save_annotated${params}`);
    return response.json();
  }
}

// Usage example
const pm = new PromptManager();

// Set prompts for person detection
await pm.setPrompts(['person', 'bottle']);

// Get current detection results  
const detections = await pm.getDetections();

// Save debug image with annotations
const debugResult = await pm.saveDebugImage(['person']);
```

## Robot + Detection Integration

```javascript
class RobotVisionController {
  constructor() {
    this.robotApi = 'http://127.0.0.1:8889';
    this.yoloApi = 'http://127.0.0.1:8001';
  }
  
  async findAndApproach(targetObject) {
    // Set detection prompt
    await this.setPrompts([targetObject]);
    
    // Get detection results
    const detection = await this.getDetections([targetObject]);
    
    if (detection.count > 0) {
      const target = detection.annotations[0];
      const [centerX, centerY] = target.center;
      const imageWidth = detection.image_shape[1];
      
      // Simple approach logic based on center position
      if (centerX < imageWidth * 0.4) {
        return this.moveRobot('left', 0.3, 0.5);
      } else if (centerX > imageWidth * 0.6) {
        return this.moveRobot('right', 0.3, 0.5);
      } else {
        return this.moveRobot('forward', 0.4, 1.0);
      }
    } else {
      // Scan for target
      return this.moveRobot('scan', 0.4);
    }
  }
  
  async moveRobot(direction, speed = 0.5, duration = null) {
    const params = new URLSearchParams({ speed });
    if (duration) params.append('duration', duration);
    
    const response = await fetch(`${this.robotApi}/${direction}/?${params}`, {
      method: 'POST'
    });
    return response.json();
  }
  
  async setPrompts(prompts) {
    const response = await fetch(`${this.yoloApi}/prompts/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prompts)
    });
    return response.json();
  }
  
  async getDetections(words = null) {
    const params = words ? `?${words.map(w => `words=${w}`).join('&')}` : '';
    const response = await fetch(`${this.yoloApi}/yolo/${params}`);
    return response.json();
  }
}
```

---

# curl Examples

## YOLO-E Detection API

```bash
# Check health
curl "http://127.0.0.1:8001/health/"

# Get current prompts
curl "http://127.0.0.1:8001/prompts/"

# Set detection prompts
curl -X POST "http://127.0.0.1:8001/prompts/" \
  -H "Content-Type: application/json" \
  -d '["person", "bottle", "car"]'

# Get detection results
curl "http://127.0.0.1:8001/yolo/?words=person&words=bottle"

# Save debug image
curl "http://127.0.0.1:8001/debug/save_annotated?words=person"
```

## Robot Control API

```bash
# Move forward for 2 seconds
curl -X POST "http://127.0.0.1:8889/forward/?speed=0.5&duration=2"

# Turn left continuously
curl -X POST "http://127.0.0.1:8889/left/?speed=0.3"

# Stop robot
curl -X POST "http://127.0.0.1:8889/stop/"

# Scan (360 degree rotation)
curl -X POST "http://127.0.0.1:8889/scan/?speed=0.4"
```

---

# Environment Configuration

## YOLO-E Backend Environment Variables

```bash
# WebSocket URL to JetBot camera
WEBSOCKET_URL="ws://10.108.169.202:8890"  # Use Jetson IP

# Force CPU mode (for RTX 5080 compatibility)
FORCE_CPU="true"

# Debug image save directory
DEBUG_SAVE_DIR="./debug_images"
```

## Starting Services

### JetBot Backend (on Jetson)
```bash
cd /path/to/VL-ADK/jetbot-backend
source ../.venv/bin/activate
python3 main.py
# Starts: API (8889) + WebSocket (8890)
```

### YOLO-E Backend (on Laptop)
```bash
cd /path/to/VL-ADK/yoloe-backend
source ../.venv/bin/activate
FORCE_CPU=true WEBSOCKET_URL="ws://10.108.169.202:8890" python3 main.py
# Starts: API (8001) + WebSocket (8002)
```

---

# Network Architecture

```
+-----------------+    +------------------+    +-----------------+
|   Jetson        |    |    Laptop        |    |   Frontend      |
|                 |    |                  |    |                 |
| JetBot Backend  |<-->| YOLO-E Backend   |<-->|  Web App        |
| API: 8889       |    | API: 8001        |    |                 |
| WebSocket: 8890 |    | WebSocket: 8002  |    |                 |
|                 |    |                  |    |                 |
| [Camera Feed]   |    | [AI Processing]  |    | [User Interface]|
+-----------------+    +------------------+    +-----------------+
```

## Data Flow:
1. **JetBot** captures camera frames and streams via WebSocket (8890)
2. **YOLO-E Backend** receives frames, runs AI detection, streams annotated results (8002)
3. **Frontend** receives annotated video stream and sends robot commands (8889)

## Recommended Frontend Architecture:
- **Video Display**: Connect to YOLO-E WebSocket (8002) for annotated stream
- **Robot Control**: Send commands to JetBot API (8889)
- **Detection Management**: Use YOLO-E API (8001) for prompt management
- **Debug/Development**: Use debug endpoints for troubleshooting