# JetBot Backend API Usage Guide

## Overview

The JetBot backend provides robot control and camera streaming capabilities through REST API and WebSocket connections.

## Port Mapping

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Robot Control API** | `8889` | HTTP/REST | Robot movement commands |
| **Camera Stream** | `8890` | WebSocket | Live camera feed + motor status |

## Base URLs

- **API Base URL**: `http://127.0.0.1:8889`
- **WebSocket URL**: `ws://127.0.0.1:8890`

---

# REST API Endpoints

## Robot Control API (Port 8889)

### POST /scan/
Starts robot scanning motion (360 degree rotation).

**Request:**
```bash
POST /scan/?speed=0.5
```

**Parameters:**
- `speed` (float, optional): Rotation speed [0.0-1.0], default: 0.5

**Response:**
```json
{
  "status": "scanning",
  "speed": 0.5
}
```

**Response Schema:**
```typescript
interface ScanResponse {
  status: "scanning";
  speed: number;
}
```

---

### POST /forward/
Move robot forward.

**Request:**
```bash
POST /forward/?speed=0.5&duration=2.0
```

**Parameters:**
- `speed` (float, optional): Movement speed [0.0-1.0], default: 0.5
- `duration` (float, optional): Movement duration in seconds, default: continuous

**Response:**
```json
{
  "status": "moving forward",
  "speed": 0.5,
  "duration": 2.0
}
```

**Response Schema:**
```typescript
interface MovementResponse {
  status: "moving forward" | "moving backward" | "turning left" | "turning right";
  speed: number;
  duration: number | null;
}
```

---

### POST /backward/
Move robot backward.

**Request:**
```bash
POST /backward/?speed=0.3&duration=1.5
```

**Parameters:** Same as `/forward/`

**Response:** Same schema as forward, with `status: "moving backward"`

---

### POST /left/
Turn robot left.

**Request:**
```bash
POST /left/?speed=0.4&duration=1.0
```

**Parameters:** Same as `/forward/`

**Response:** Same schema as forward, with `status: "turning left"`

---

### POST /right/
Turn robot right.

**Request:**
```bash
POST /right/?speed=0.4&duration=1.0
```

**Parameters:** Same as `/forward/`

**Response:** Same schema as forward, with `status: "turning right"`

---

### POST /stop/
Stop all robot movement immediately.

**Request:**
```bash
POST /stop/
```

**Parameters:** None

**Response:**
```json
{
  "status": "stopped"
}
```

**Response Schema:**
```typescript
interface StopResponse {
  status: "stopped";
}
```

---

# WebSocket API

## Camera Stream (Port 8890)

### Connection
```javascript
const ws = new WebSocket('ws://127.0.0.1:8890');
```

### Message Format

**Received Messages:**
```json
{
  "image": "base64_encoded_jpeg_data",
  "left_motor": 0.0,
  "right_motor": 0.0,
  "control": {
    "status": "moving forward",
    "speed": 0.5,
    "duration": 2.0
  }
}
```

**Message Schema:**
```typescript
interface JetBotWebSocketMessage {
  image: string;           // Base64-encoded JPEG image data
  left_motor: number;      // Left motor value [-1.0 to 1.0]
  right_motor: number;     // Right motor value [-1.0 to 1.0]
  control?: {              // Optional current robot command
    status: string;        // Current action status
    speed?: number;        // Movement speed
    duration?: number;     // Duration (null for continuous)
  };
}
```

### Image Processing

**Decoding Base64 Image (JavaScript):**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Create image element
  const img = new Image();
  img.src = `data:image/jpeg;base64,${data.image}`;
  
  // Display in canvas or img element
  document.getElementById('camera-feed').src = img.src;
};
```

**Decoding Base64 Image (Python):**
```python
import base64
import cv2
import numpy as np

# Decode base64 to image
image_bytes = base64.b64decode(data["image"])
nparr = np.frombuffer(image_bytes, np.uint8)
frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
```

---

# Error Handling

## HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `307` | Temporary Redirect (trailing slash missing) |
| `422` | Validation Error (invalid parameters) |
| `500` | Internal Server Error |

## Common Issues

### 307 Temporary Redirect
**Problem:** Calling `/forward` instead of `/forward/`

**Solution:** Always include trailing slash in API calls:
```bash
# Wrong
POST /forward

# Correct  
POST /forward/
```

---

# Example Usage

## Frontend Integration

```typescript
class JetBotController {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8889';
    this.ws = new WebSocket('ws://127.0.0.1:8890');
    this.setupWebSocket();
  }
  
  // Robot control methods
  async moveForward(speed = 0.5, duration = null) {
    const params = new URLSearchParams({ speed });
    if (duration) params.append('duration', duration);
    
    const response = await fetch(`${this.apiBase}/forward/?${params}`, {
      method: 'POST'
    });
    return response.json();
  }
  
  async stop() {
    const response = await fetch(`${this.apiBase}/stop/`, {
      method: 'POST'
    });
    return response.json();
  }
  
  // WebSocket camera feed
  setupWebSocket() {
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Update camera feed
      const cameraImg = document.getElementById('camera-feed');
      cameraImg.src = `data:image/jpeg;base64,${data.image}`;
      
      // Update motor status
      document.getElementById('left-motor').textContent = data.left_motor;
      document.getElementById('right-motor').textContent = data.right_motor;
      
      // Update current command
      if (data.control) {
        document.getElementById('status').textContent = data.control.status;
      }
    };
  }
}
```

## curl Examples

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

# Technical Details

## Camera Configuration
- **Resolution**: 1640x1232 pixels
- **Frame Rate**: 20 FPS target
- **Format**: JPEG (quality 75%)
- **Color Space**: BGR
- **Encoding**: Base64 in WebSocket messages

## Motor Values
- **Range**: -1.0 (full reverse) to 1.0 (full forward)
- **Type**: Float
- **Update Rate**: Real-time with camera frames

## WebSocket Features
- **Backpressure Handling**: Latest frame only (drops old frames)
- **Connection Management**: Multiple clients supported
- **Auto-reconnection**: Client should implement reconnection logic
- **Message Queue**: Max size 1 (latest frame priority)

---

# Deployment Notes

## Starting the JetBot Backend
```bash
cd /path/to/VL-ADK/jetbot-backend
source ../.venv/bin/activate
python3 main.py
```

## Environment Requirements
- **Platform**: NVIDIA Jetson with CSI camera
- **Dependencies**: System OpenCV with GStreamer support
- **Hardware**: JetBot robot with I2C motor controller

## Network Configuration
- **Default**: Localhost only (`127.0.0.1`)
- **For Remote Access**: Update `API_HOST` and `WEBSOCKET_HOST` in `main.py`
- **Firewall**: Ensure ports 8889 and 8890 are accessible