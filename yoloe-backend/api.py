# yolo_api.py
# FastAPI server for YOLO-E:
# - Manages HTTP API endpoints for object detection
# - Provides detection results, prompt management, health checks

import base64
import json
import os
import time
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, Query


class YoloApi:
    def __init__(self, model_manager, host: str = "127.0.0.1", port: int = 8001):
        self.host = host
        self.port = port
        self.model_manager = model_manager
        self.app = FastAPI(title="YOLO-E API", description="YOLO Object Detection for VL-ADK", version="0.1.0")
        self.server = None
        self.debug_save_dir = os.getenv("DEBUG_SAVE_DIR", "./debug_images")
        os.makedirs(self.debug_save_dir, exist_ok=True)
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes for YOLO detection."""

        @self.app.get("/yolo/")
        async def get_yolo_annotations(words: Optional[List[str]] = Query(None, description="Target words to detect")):
            """Get YOLO object detection results, optionally filtered by target words."""
            return self.model_manager.get_detection_results(words)

        @self.app.post("/prompts/")
        async def set_detection_prompts(prompts: List[str]):
            """Set new open-vocabulary prompts for YOLO-E detection."""
            return self.model_manager.set_prompts(prompts)

        @self.app.get("/prompts/")
        async def get_current_prompts():
            """Get currently active YOLO-E prompts."""
            return self.model_manager.get_current_prompts()

        @self.app.get("/health/")
        async def health_check():
            """Check YOLO-E backend health and status."""
            return self.model_manager.get_health_status()

        @self.app.get("/debug/save_annotated")
        async def save_annotated_image(words: Optional[List[str]] = Query(None, description="Target words to detect")):
            """Save current frame with YOLO annotations to debug directory."""
            # Get current frame and detection results
            frame_data = self.model_manager.get_latest_frame()
            if not frame_data:
                return {"error": "No image available from WebSocket stream", "saved": False}

            # Check if frame is too old
            if time.time() - frame_data["timestamp"] > 5:
                return {
                    "error": "Image data is stale",
                    "saved": False,
                    "age_seconds": time.time() - frame_data["timestamp"],
                }

            # Run YOLO detection
            results = self.model_manager.run_detection(frame_data["frame"], words)
            if "error" in results:
                return {"error": results["error"], "saved": False}

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_prompts = results.get("current_prompts", [])
            prompts_str = "_".join(words) if words else "_".join(current_prompts) if current_prompts else "default"
            filename = f"yolo_debug_{timestamp}_{prompts_str}.jpg"
            save_path = os.path.join(self.debug_save_dir, filename)

            # Draw annotations and save (this call draws labels; fine for debug)
            _ = self.model_manager.draw_annotations_on_frame(frame_data["frame"], results["annotations"], save_path)

            # Also save metadata
            metadata_path = save_path.replace(".jpg", "_metadata.json")
            metadata = {
                "timestamp": timestamp,
                "prompts": results.get("current_prompts", []),
                "detection_count": results.get("count", 0),
                "annotations": results["annotations"],
                "motor_data": frame_data.get("motor_data", {}),
                "frame_timestamp": frame_data["timestamp"],
                "detection_timestamp": time.time(),
                "image_shape": results.get("image_shape", None),
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return {
                "saved": True,
                "image_path": save_path,
                "metadata_path": metadata_path,
                "detection_count": results.get("count", 0),
                "prompts": results.get("current_prompts", []),
                "annotations": results["annotations"],
            }

        @self.app.get("/retrieve-annotated-image")
        async def retrieve_annotated_image(words: Optional[List[str]] = Query(None, description="Target words to detect")):
            """
            Return a base64-encoded JPEG with only visual annotations (boxes/segments) overlaid.
            No text overlays (no labels/FPS/prompts) to keep tokens low for downstream AI consumption.
            """
            # Get current frame
            frame_data = self.model_manager.get_latest_frame()
            if not frame_data:
                return {"error": "No image available from WebSocket stream"}
            if time.time() - frame_data["timestamp"] > 5:
                return {
                    "error": "Image data is stale",
                    "age_seconds": time.time() - frame_data["timestamp"],
                }

            # Run detection (boxes only if model is detector; will draw segments if provided)
            results = self.model_manager.run_detection(frame_data["frame"], words)
            if "error" in results:
                return {"error": results["error"]}

            frame = frame_data["frame"]
            anns = results.get("annotations", [])
            if frame is None:
                return {"error": "No frame data"}

            # ---- Minimal overlay (no text) ----
            annotated = frame.copy()
            # simple color palette (BGR)
            colors = [
                (0, 255, 0),  # green
                (255, 0, 0),  # blue
                (0, 0, 255),  # red
                (255, 255, 0),  # cyan
                (255, 0, 255),  # magenta
                (0, 255, 255),  # yellow
                (128, 0, 128),  # purple
                (255, 165, 0),  # orange
            ]
            for i, ann in enumerate(anns):
                color = colors[(ann.get("prompt_index", i)) % len(colors)]

                # Draw polygon segmentation (if provided)
                # Expect either:
                #  - ann["segments"]: list of Nx2 points (float/int)
                #  - ann["mask"]: binary mask (H x W) or contour list
                seg_drawn = False
                seg = ann.get("segments")
                if isinstance(seg, (list, tuple)) and len(seg) > 0:
                    try:
                        pts = np.array(seg, dtype=np.int32).reshape(-1, 1, 2)
                        cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=2)
                        seg_drawn = True
                    except Exception:
                        pass
                else:
                    mask = ann.get("mask")
                    if isinstance(mask, np.ndarray) and mask.dtype == np.uint8:
                        try:
                            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            cv2.drawContours(annotated, contours, -1, color, 2)
                            seg_drawn = True
                        except Exception:
                            pass

                # Draw bbox
                if "bbox" in ann and isinstance(ann["bbox"], (list, tuple)) and len(ann["bbox"]) == 4:
                    x1, y1, x2, y2 = map(int, ann["bbox"])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                # NOTE: no labels / text / centers drawn by design

            # Encode to JPEG -> base64
            ok, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                return {"error": "Failed to encode image"}
            img_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

            return {
                "image": img_b64,  # base64 JPEG
                "count": len(anns),
                "image_shape": results.get("image_shape"),
                "prompts": results.get("current_prompts", []),
                "timestamp": results.get("timestamp"),
                "annotations": anns,  # raw boxes/segments (no text added to pixels)
            }

    async def start(self):
        """Start the FastAPI server."""
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info")
        self.server = uvicorn.Server(config)
        print(f"YOLO-E API server started on {self.host}:{self.port}")
        await self.server.serve()

    async def stop(self):
        """Stop the FastAPI server."""
        if self.server:
            self.server.should_exit = True
            print("YOLO-E API server stopped")
