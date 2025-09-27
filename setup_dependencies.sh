#!/bin/bash

# JetBot API Setup Script
# This script installs system dependencies and Python packages needed for JetBot API

echo "Setting up JetBot API dependencies..."

# Source the .venv/bin/activate file
source .venv/bin/activate

# Update package list
echo "Updating package list..."
sudo apt update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    python3-gst-1.0 \
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    libcairo-gobject2 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-tools \
    libopencv-dev \
    python3-opencv \
    python3-dev \
    build-essential

# Install TensorRT packages (NVIDIA specific)
echo "Installing TensorRT packages..."
sudo apt install -y \
    python3-libnvinfer \
    python3-libnvinfer-dev \
    python3-libnvinfer-dispatch \
    python3-libnvinfer-lean

# Install Python packages
echo "Installing Python packages..."
pip install -r requirements.txt

# Install PyTorch (NVIDIA Jetson optimized version)
echo "Checking PyTorch installation..."
if python3 -c "import torch; print(f'PyTorch {torch.__version__} already installed')" 2>/dev/null; then
    echo "PyTorch already installed, skipping..."
else
    echo "Installing PyTorch for Jetson..."
    echo "Note: PyTorch installation may take 10-20 minutes on Jetson..."
    pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
fi

# Install YOLO-E specific dependencies (without opencv dependency)
echo "Checking ultralytics installation..."
if python3 -c "import ultralytics; print(f'Ultralytics already installed')" 2>/dev/null; then
    echo "Ultralytics already installed, skipping..."
else
    echo "Installing YOLO-E dependencies..."
    pip install ultralytics>=8.0.196 --no-deps
fi

# Create symbolic links for system Python modules in virtual environment
echo "Creating symbolic links for system modules..."
cd .venv/lib/python3.10/site-packages

# Link GStreamer and GTK modules
ln -sf /usr/lib/python3/dist-packages/gi* .
ln -sf /usr/lib/python3/dist-packages/cairo* .
ln -sf /usr/lib/python3/dist-packages/gobject* .

# Link TensorRT modules (specific known locations)
echo "Linking TensorRT modules..."
if [ -d "/usr/lib/python3.10/dist-packages/tensorrt" ]; then
    ln -sf /usr/lib/python3.10/dist-packages/tensorrt .
    echo "  - tensorrt"
fi
if [ -d "/usr/lib/python3.10/dist-packages/tensorrt_lean" ]; then
    ln -sf /usr/lib/python3.10/dist-packages/tensorrt_lean .
    echo "  - tensorrt_lean"
fi
if [ -d "/usr/lib/python3.10/dist-packages/tensorrt_dispatch" ]; then
    ln -sf /usr/lib/python3.10/dist-packages/tensorrt_dispatch .
    echo "  - tensorrt_dispatch"
fi

# Link system OpenCV (has GStreamer support) instead of pip version  
ln -sf /usr/lib/python3/dist-packages/cv2* .

cd ../../../..

# Verify installations
echo ""
echo "Verifying installations..."
echo "================================"

# Check TensorRT
if python3 -c "import tensorrt as trt; print(f'TensorRT {trt.__version__}')" 2>/dev/null; then
    :
else
    echo "TensorRT not found - symlinks may need fixing"
fi

# Check PyTorch
if python3 -c "import torch; print(f'PyTorch {torch.__version__} (CUDA: {torch.cuda.is_available()})')" 2>/dev/null; then
    :
else
    echo "PyTorch not found"
fi

# Check OpenCV
if python3 -c "import cv2; print(f'OpenCV {cv2.__version__}')" 2>/dev/null; then
    :
else
    echo "OpenCV not found"
fi

# Check Ultralytics/YOLO-E
if python3 -c "import ultralytics; print('Ultralytics/YOLO-E available')" 2>/dev/null; then
    :
else
    echo "Ultralytics not found"
fi

# Check JetBot imports
if python3 -c "import sys; sys.path.append('jetbot-api'); from jetbot import Camera, Robot; print('JetBot imports successful')" 2>/dev/null; then
    :
else
    echo "JetBot imports failed - some dependencies may be missing"
fi

echo ""
echo "Setup complete! You can now run:"
echo "   cd jetbot-api && python3 main.py"
echo "   cd yoloe-backend && python3 main.py"