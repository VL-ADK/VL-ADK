# yolo_model_manager.py
# YOLO-E Model Management:
# - Handles model loading and inference
# - Manages current prompts and frame processing
# - Provides detection results and annotations

import os
import time
from threading import Lock
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch

try:
    from ultralytics import YOLOE

    print("YOLO-E imported successfully")
except ImportError as e:
    print(f"YOLO-E import failed: {e}")
    raise


class YoloModelManager:
    def __init__(self, model_path: str = "yoloe-l.pt", force_cpu: bool = False):
        self.model_path = model_path
        self.force_cpu = force_cpu
        self.model = None
        self.current_prompts = []
        self.device = None
        self.latest_frame = None
        self.frame_lock = Lock()

        # Initialize model
        self.init_model()

    def init_model(self):
        """Initialize YOLO-E model with device selection and error handling."""
        try:
            # Force CPU if environment variable is set or CUDA has issues
            if self.force_cpu or os.getenv("FORCE_CPU", "false").lower() == "true":
                self.device = "cpu"
                print("Forcing CPU mode due to FORCE_CPU=true")
            else:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"

            print(f"Using device: {self.device}")
            print(f"Loading YOLO-E model: {self.model_path}")

            # Try to load model, fallback to CPU if CUDA fails
            try:
                self.model = YOLOE(self.model_path).to(self.device)
            except RuntimeError as cuda_error:
                if "CUDA" in str(cuda_error) and self.device == "cuda":
                    print(f"CUDA error encountered: {cuda_error}")
                    print("Falling back to CPU mode...")
                    self.device = "cpu"
                    self.model = YOLOE(self.model_path).to(self.device)
                else:
                    raise

            print("YOLO-E model loaded successfully!")
        except Exception as e:
            print(f"Failed to load YOLO-E model: {e}")
            self.model = None

    def set_prompts(self, prompts: List[str]) -> Dict:
        """Set open-vocabulary prompts for YOLO-E detection."""
        try:
            if self.model is None:
                return {"success": False, "current_prompts": [], "message": "YOLO-E model not loaded"}

            # Set classes with the text embeddings
            text_embeddings = self.model.get_text_pe(prompts)
            self.model.set_classes(prompts, text_embeddings)
            self.current_prompts = prompts.copy()
            print(f"Set YOLO-E prompts to: {prompts}")
            return {"success": True, "current_prompts": self.current_prompts.copy(), "message": f"Prompts set to: {prompts}"}
        except Exception as e:
            print(f"Failed to set prompts: {e}")
            return {"success": False, "current_prompts": self.current_prompts.copy(), "message": "Failed to set prompts"}

    def append_prompts(self, prompts: List[str]) -> Dict:
        """Append new open-vocabulary prompts for YOLO-E detection."""
        try:
            if self.model is None:
                return {"success": False, "current_prompts": [], "message": "YOLO-E model not loaded"}

            # Get current prompts and add new ones
            current_prompts = self.current_prompts.copy()
            current_prompts.extend(prompts)

            # Set classes with the text embeddings
            text_embeddings = self.model.get_text_pe(current_prompts)
            self.model.set_classes(current_prompts, text_embeddings)
            self.current_prompts = current_prompts.copy()
            print(f"Appended YOLO-E prompts: {prompts}")
            return {"success": True, "current_prompts": self.current_prompts.copy(), "message": f"Prompts appended: {prompts}"}
        except Exception as e:
            print(f"Failed to append prompts: {e}")
            return {"success": False, "current_prompts": self.current_prompts.copy(), "message": "Failed to append prompts"}

    def get_current_prompts(self) -> Dict:
        """Get currently active YOLO-E prompts."""
        return {"current_prompts": self.current_prompts.copy(), "model_loaded": self.model is not None, "device": self.device}

    def update_frame(self, frame, timestamp: float, motor_data: Dict = None):
        """Update the latest frame data thread-safely."""
        with self.frame_lock:
            self.latest_frame = {"frame": frame, "timestamp": timestamp, "motor_data": motor_data or {}}

    def get_latest_frame(self) -> Optional[Dict]:
        """Get the latest frame data thread-safely."""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame else None

    def run_detection(self, frame, target_words: List[str] = None) -> Dict:
        """Run YOLO-E detection on frame with open-vocabulary prompts."""
        if self.model is None:
            return {"error": "YOLO-E model not loaded"}

        # Set prompts if target_words provided and different from current
        if target_words and target_words != self.current_prompts:
            prompt_result = self.set_prompts(target_words)
            if not prompt_result["success"]:
                return {"error": "Failed to set YOLO-E prompts"}
        elif not target_words and not self.current_prompts:
            # Default prompts if none set
            default_prompts = ["person", "car", "bottle", "chair", "dog", "cat"]
            prompt_result = self.set_prompts(default_prompts)
            if not prompt_result["success"]:
                return {"error": "Failed to set default prompts"}

        try:
            # Run YOLO-E inference
            results = self.model.predict(frame, conf=0.25, iou=0.5, device=self.device, verbose=False)

            annotations = []
            if len(results) > 0:
                result = results[0]
                dets = result.boxes

                if dets is not None and len(dets) > 0:
                    n = len(dets)
                    try:
                        # Extract detection data
                        cls_indices = dets.cls.int().cpu().tolist()
                        confidences = dets.conf.float().cpu().tolist()
                        xyxy_boxes = dets.xyxy.int().cpu().tolist()
                    except Exception:
                        # Fallback for older tensor API
                        cls_indices = []
                        confidences = []
                        xyxy_boxes = []
                        for b in dets:
                            cls_indices.append(int(b.cls))
                            confidences.append(float(b.conf))
                            xyxy_boxes.append(b.xyxy.int().cpu().numpy().flatten().tolist())

                    print(f"[DEBUG] {n} detections for prompts {self.current_prompts}")

                    for i, (cls_idx, conf, box) in enumerate(zip(cls_indices, confidences, xyxy_boxes)):
                        # YOLO-E: class_id indexes current_prompts, not COCO classes
                        if 0 <= cls_idx < len(self.current_prompts):
                            class_name = self.current_prompts[cls_idx]
                        else:
                            class_name = f"id{cls_idx}"

                        print(f"   {i}: {class_name} {conf:.2f} at {box}")

                        x1, y1, x2, y2 = box

                        annotation = {"class": class_name, "confidence": conf, "bbox": [x1, y1, x2, y2], "center": [(x1 + x2) / 2, (y1 + y2) / 2], "area": (x2 - x1) * (y2 - y1), "prompt_index": cls_idx}
                        annotations.append(annotation)
                else:
                    print(f"[DEBUG] 0 detections for prompts {self.current_prompts}")

            return {"annotations": annotations, "count": len(annotations), "timestamp": time.time(), "image_shape": frame.shape if frame is not None else None, "current_prompts": self.current_prompts.copy(), "model_type": "YOLO-E"}

        except Exception as e:
            return {"error": f"YOLO-E detection failed: {str(e)}"}

    def get_detection_results(self, target_words: List[str] = None) -> Dict:
        """Get YOLO object detection results from latest frame."""
        frame_data = self.get_latest_frame()
        if not frame_data:
            return {"error": "No image available from WebSocket stream", "annotations": [], "count": 0}

        # Check if frame is too old (>5 seconds)
        if time.time() - frame_data["timestamp"] > 5:
            return {"error": "Image data is stale", "annotations": [], "count": 0, "age_seconds": time.time() - frame_data["timestamp"]}

        # Run YOLO detection
        results = self.run_detection(frame_data["frame"], target_words)

        # Add metadata
        if "error" not in results:
            results["motor_data"] = frame_data["motor_data"]
            results["frame_timestamp"] = frame_data["timestamp"]
            results["detection_timestamp"] = time.time()

        return results

    def get_health_status(self) -> Dict:
        """Get health status of YOLO backend."""
        frame_data = self.get_latest_frame()
        return {
            "status": "healthy" if self.model is not None else "unhealthy",
            "model_loaded": self.model is not None,
            "model_type": "YOLO-E",
            "current_prompts": self.current_prompts.copy(),
            "device": self.device,
            "latest_frame_age": time.time() - frame_data["timestamp"] if frame_data else None,
            "websocket_connected": frame_data is not None,
        }

    def draw_annotations_on_frame(self, frame, annotations, save_path=None):
        """Draw bounding boxes and labels on frame, optionally save to file."""
        if frame is None or not annotations:
            return frame

        # Create a copy to avoid modifying original
        annotated_frame = frame.copy()

        # Define colors for different classes (BGR format)
        colors = [
            (0, 255, 0),  # Green
            (255, 0, 0),  # Blue
            (0, 0, 255),  # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
            (128, 0, 128),  # Purple
            (255, 165, 0),  # Orange
        ]

        for i, ann in enumerate(annotations):
            # Get bounding box coordinates
            x1, y1, x2, y2 = ann["bbox"]

            # Choose color based on class
            color_idx = ann.get("prompt_index", i) % len(colors)
            color = colors[color_idx]

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # Prepare label text
            class_name = ann["class"]
            confidence = ann["confidence"]
            label = f"{class_name}: {confidence:.2f}"

            # Get text size for background
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            # Draw label background
            cv2.rectangle(annotated_frame, (x1, y1 - text_height - 10), (x1 + text_width, y1), color, -1)

            # Draw label text
            cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Draw center point
            center_x, center_y = int(ann["center"][0]), int(ann["center"][1])
            cv2.circle(annotated_frame, (center_x, center_y), 4, color, -1)

        # Save to file if path provided
        if save_path:
            cv2.imwrite(save_path, annotated_frame)
            print(f"Saved annotated image to: {save_path}")

        return annotated_frame
