#!/bin/bash

# VL-ADK Setup Script
# This script installs system dependencies and Python packages for both Jetson and Desktop

echo "VL-ADK Setup Script"
echo "====================="

# Detect environment
if [ -f "/etc/nv_tegra_release" ] || grep -q "tegra" /proc/cpuinfo 2>/dev/null; then
    ENVIRONMENT="jetson"
    echo "Detected: NVIDIA Jetson"
elif command -v system76-power >/dev/null 2>&1; then
    ENVIRONMENT="system76"
    echo "Detected: System76 Laptop"
else
    ENVIRONMENT="desktop"
    echo "Detected: Desktop/Laptop"
fi

# Allow manual override
if [ "$1" = "--jetson" ]; then
    ENVIRONMENT="jetson"
    echo "Forced: Jetson mode"
elif [ "$1" = "--desktop" ]; then
    ENVIRONMENT="desktop"
    echo "Forced: Desktop mode"
elif [ "$1" = "--system76" ]; then
    ENVIRONMENT="system76"
    echo "Forced: System76 mode"
fi

echo "Environment: $ENVIRONMENT"
echo ""

# Source the .venv/bin/activate file
source .venv/bin/activate

# Update package list
echo "Updating package list..."
sudo apt update

# Install system dependencies (environment-specific)
if [ "$ENVIRONMENT" = "jetson" ]; then
    echo "Installing Jetson system dependencies..."
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

    # Install TensorRT packages (Jetson specific)
    echo "Installing TensorRT packages..."
    sudo apt install -y \
        python3-libnvinfer \
        python3-libnvinfer-dev \
        python3-libnvinfer-dispatch \
        python3-libnvinfer-lean

elif [ "$ENVIRONMENT" = "system76" ]; then
    echo "Installing System76 desktop dependencies..."
    sudo apt install -y \
        python3-dev \
        build-essential \
        libopencv-dev \
        nvidia-driver-530 \
        nvidia-cuda-toolkit
    
    # Enable NVIDIA graphics
    echo "Enabling NVIDIA graphics..."
    sudo system76-power graphics nvidia || echo "Warning: Could not switch to NVIDIA graphics"

else
    echo "Installing desktop dependencies..."
    sudo apt install -y \
        python3-dev \
        build-essential \
        libopencv-dev
    
    # Try to install NVIDIA drivers if available
    if lspci | grep -i nvidia >/dev/null; then
        echo "NVIDIA GPU detected, installing drivers..."
        sudo apt install -y nvidia-driver-530 nvidia-cuda-toolkit || echo "Warning: NVIDIA driver installation failed"
    fi
fi

# Install Python packages
echo "Installing Python packages..."
pip install -r requirements.txt

# Install PyTorch (environment-specific)
echo "Checking PyTorch installation..."
if python3 -c "import torch; print(f'PyTorch {torch.__version__} already installed')" 2>/dev/null; then
    echo "PyTorch already installed, skipping..."
else
    if [ "$ENVIRONMENT" = "jetson" ]; then
        echo "Installing PyTorch for Jetson..."
        echo "Note: PyTorch installation may take 10-20 minutes on Jetson..."
        pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
    else
        echo "Installing PyTorch for Desktop/Laptop..."
        echo "Note: This will install CUDA-enabled PyTorch..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    fi
fi

# Install YOLO-E specific dependencies
echo "Checking ultralytics installation..."
if python3 -c "import ultralytics; print(f'Ultralytics already installed')" 2>/dev/null; then
    echo "Ultralytics already installed, skipping..."
else
    echo "Installing YOLO-E dependencies..."
    if [ "$ENVIRONMENT" = "jetson" ]; then
        # On Jetson, avoid opencv conflict with system opencv
        pip install ultralytics>=8.0.196 --no-deps
    else
        # On desktop, install normally (opencv-python is fine)
        pip install ultralytics>=8.0.196
    fi
fi

# Create symbolic links for system Python modules (Jetson only)
if [ "$ENVIRONMENT" = "jetson" ]; then
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
fi

# Enable NVIDIA graphics on System76
if [ "$ENVIRONMENT" = "system76" ]; then
    echo "Checking System76 graphics mode..."
    CURRENT_MODE=$(system76-power graphics 2>/dev/null || echo "unknown")
    echo "Current graphics mode: $CURRENT_MODE"
    
    if [ "$CURRENT_MODE" != "nvidia" ]; then
        echo "Graphics not set to NVIDIA. You may need to:"
        echo "   sudo system76-power graphics nvidia"
        echo "   Then logout/login or reboot"
    fi
fi

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

# Check JetBot imports (Jetson only)
if [ "$ENVIRONMENT" = "jetson" ]; then
    if python3 -c "import sys; sys.path.append('jetbot-api'); from jetbot import Camera, Robot; print('JetBot imports successful')" 2>/dev/null; then
        :
    else
        echo "JetBot imports failed - some dependencies may be missing"
    fi
fi

echo ""
echo "Setup complete! You can now run:"
if [ "$ENVIRONMENT" = "jetson" ]; then
    echo "   cd jetbot-api && python3 main.py    # JetBot hardware API"
fi
echo "   cd yoloe-backend && python3 main.py  # YOLO-E detection API"

if [ "$ENVIRONMENT" = "system76" ]; then
    echo ""
    echo "System76 Next Steps:"
    echo "1. Check graphics mode: system76-power graphics"
    echo "2. If not 'nvidia', run: sudo system76-power graphics nvidia"
    echo "3. Logout/login or reboot for GPU changes to take effect"
    echo "4. Test CUDA: python3 -c 'import torch; print(torch.cuda.is_available())'"
fi