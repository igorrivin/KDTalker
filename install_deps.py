#!/usr/bin/env python
"""
Platform-specific dependency installer for KDTalker
This script detects whether you're running on WSL2 or another platform
and installs the appropriate dependencies.
"""

import os
import sys
import platform
import subprocess

def is_wsl():
    """Check if running on WSL (Windows Subsystem for Linux)"""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

def main():
    """Main installation function"""
    print("KDTalker Dependency Installer")
    print("-----------------------------")
    
    # Detect platform
    is_windows_wsl = is_wsl()
    
    if is_windows_wsl:
        print("Detected WSL2 environment")
        req_file = "requirements-wsl2.txt"
    else:
        print(f"Detected {platform.system()} environment")
        req_file = "requirements-unix.txt"
    
    # Check if the requirements file exists
    if not os.path.exists(req_file):
        print(f"ERROR: {req_file} not found. Using default requirements.txt")
        req_file = "requirements.txt"
    
    # Install dependencies
    print(f"Installing dependencies from {req_file}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print("Installation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        sys.exit(1)
    
    # Additional instructions for all platforms
    print("\nPostinstallation steps:")
    print("1. Configure ONNX Runtime to use CUDA:")
    print("   The standard onnxruntime package can use CUDA if properly configured.")
    print("   Your Python code must specify CUDA providers when creating inference sessions, for example:")
    print("   session = onnxruntime.InferenceSession(model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])")
    print("")
    
    # Additional instructions for WSL
    if is_windows_wsl:
        print("WSL2-specific notes:")
        print("1. If dlib installation failed, try installing it separately:")
        print("   sudo apt-get install -y cmake build-essential libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev")
        print("   DLIB_USE_CUDA=0 pip install dlib==19.24.6")
        print("")
        print("2. Ensure CUDA is properly installed for PyTorch:")
        print("   nvidia-smi  # Should show your GPU")
        print("")
        print("3. For ONNX Runtime with CUDA in WSL2, you may need:")
        print("   pip install onnxruntime-gpu  # If available for your CUDA version")
        print("   # OR")
        print("   CUDA_PATH=/usr/local/cuda pip install onnxruntime  # Point to your CUDA installation")
        print("")

if __name__ == "__main__":
    main()