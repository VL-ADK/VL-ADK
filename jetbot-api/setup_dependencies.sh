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
echo "Installing PyTorch for Jetson..."
echo "Note: PyTorch installation may take several minutes..."
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# Create symbolic links for system Python modules in virtual environment
echo "Creating symbolic links for system modules..."
cd .venv/lib/python3.10/site-packages
ln -sf /usr/lib/python3/dist-packages/gi* .
ln -sf /usr/lib/python3/dist-packages/cairo* .
ln -sf /usr/lib/python3/dist-packages/gobject* .
ln -sf /usr/lib/python3/dist-packages/tensorrt* .
# Link system OpenCV (has GStreamer support) instead of pip version
ln -sf /usr/lib/python3/dist-packages/cv2* .
cd ../../../..

echo "Setup complete! You can now run: python3 main.py"