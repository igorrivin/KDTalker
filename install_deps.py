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
import shutil
from pathlib import Path

def is_wsl():
    """Check if running on WSL (Windows Subsystem for Linux)"""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

def find_cuda_path():
    """Find CUDA installation path"""
    # Common CUDA locations
    possible_paths = [
        '/usr/local/cuda',
        '/usr/local/cuda-12.1',
        '/usr/local/cuda-12.0',
        '/usr/local/cuda-11.8',
        '/usr/local/cuda-11.7',
        '/usr/local/cuda-11.6',
        '/opt/cuda',
    ]
    
    # Check environment variable first
    if 'CUDA_PATH' in os.environ and os.path.exists(os.environ['CUDA_PATH']):
        return os.environ['CUDA_PATH']
    
    # Check common paths
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    # Try to find using which
    try:
        nvcc_path = subprocess.check_output(['which', 'nvcc']).decode().strip()
        if nvcc_path:
            # nvcc is typically in the bin subdirectory of CUDA
            cuda_path = os.path.dirname(os.path.dirname(nvcc_path))
            if os.path.exists(cuda_path):
                return cuda_path
    except:
        pass
    
    return None

def create_onnx_helper_script():
    """Create a helper script to properly configure ONNX Runtime with CUDA"""
    cuda_path = find_cuda_path()
    script_path = Path('fix_onnxruntime_cuda.py')
    
    script_content = f"""#!/usr/bin/env python
# This script helps configure ONNX Runtime to use CUDA
import os
import sys
import subprocess
from pathlib import Path

def main():
    print("ONNX Runtime CUDA Configuration Helper")
    print("======================================")
    
    # Try to detect CUDA
    cuda_path = {repr(cuda_path) if cuda_path else 'None'}
    if not cuda_path:
        print("Could not auto-detect CUDA path.")
        cuda_path_input = input("Please enter your CUDA installation path (e.g., /usr/local/cuda): ")
        if cuda_path_input and os.path.exists(cuda_path_input):
            cuda_path = cuda_path_input
        else:
            print("No valid CUDA path provided. ONNX Runtime may not use CUDA.")
    
    # Set environment variables
    if cuda_path:
        print(f"Setting CUDA_PATH={cuda_path}")
        os.environ['CUDA_PATH'] = cuda_path
        
        # Set LD_LIBRARY_PATH
        ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
        cuda_lib_path = os.path.join(cuda_path, 'lib64')
        if cuda_lib_path not in ld_lib_path:
            new_ld_path = f"{cuda_lib_path}:{ld_lib_path}" if ld_lib_path else cuda_lib_path
            print(f"Setting LD_LIBRARY_PATH={new_ld_path}")
            os.environ['LD_LIBRARY_PATH'] = new_ld_path
    
    # Install ONNX Runtime
    print("\\nInstalling ONNX Runtime...")
    cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime", "onnxruntime-gpu"]
    subprocess.call(cmd)
    
    # Detect CUDA version for appropriate ORT version
    cuda_version = None
    if cuda_path:
        try:
            nvcc_output = subprocess.check_output([os.path.join(cuda_path, 'bin', 'nvcc'), '--version']).decode()
            for line in nvcc_output.split('\\n'):
                if "release" in line and "V" in line:
                    version_part = line.split("V")[1].split(".")[0]
                    if version_part:
                        cuda_version = int(version_part)
                    break
        except:
            print("Could not determine CUDA version from nvcc")
    
    # Install appropriate version
    if cuda_version:
        print(f"Detected CUDA version: {cuda_version}")
        if cuda_version >= 12:
            print("Installing onnxruntime 1.16.3 for CUDA 12.x...")
            cmd = [sys.executable, "-m", "pip", "install", "onnxruntime==1.16.3"]
        elif cuda_version >= 11:
            print("Installing onnxruntime 1.15.1 for CUDA 11.x...")
            cmd = [sys.executable, "-m", "pip", "install", "onnxruntime==1.15.1"]
        else:
            print("Installing onnxruntime 1.14.1 for older CUDA versions...")
            cmd = [sys.executable, "-m", "pip", "install", "onnxruntime==1.14.1"]
    else:
        print("No CUDA version detected, trying onnxruntime 1.15.1...")
        cmd = [sys.executable, "-m", "pip", "install", "onnxruntime==1.15.1"]
    
    subprocess.call(cmd)
    
    # Check if CUDA is available in ONNX Runtime
    print("\\nVerifying ONNX Runtime CUDA support...")
    
    verification_code = '''
import onnxruntime as ort
providers = ort.get_available_providers()
print(f"Available providers: {{providers}}")
if 'CUDAExecutionProvider' in providers:
    print("SUCCESS: CUDA is available for ONNX Runtime")
    cuda_info = ort.get_device()
    print(f"CUDA device info: {{cuda_info}}")
else:
    print("WARNING: CUDA is NOT available for ONNX Runtime")
    print("You may need to check CUDA installation or try a different ONNX Runtime version")
'''
    
    print("Running verification...")
    try:
        subprocess.run([sys.executable, "-c", verification_code])
    except Exception as e:
        print(f"Error during verification: {{e}}")
    
    print("\\nIf CUDA is not available, you can try:")
    print("  1. Set these in your .bashrc or before running python:")
    print(f"     export CUDA_PATH={cuda_path or '/usr/local/cuda'}")
    print(f"     export LD_LIBRARY_PATH=$CUDA_PATH/lib64:$LD_LIBRARY_PATH")
    print("  2. Try installing onnxruntime-gpu if available for your Python version")
    print("  3. Check CUDA installation with 'nvidia-smi' and 'nvcc --version'")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)  # Make executable
    return script_path

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
        print("Continuing with ONNX Runtime installation...")
    
    # Create ONNX Runtime helper script
    print("\n=== Creating ONNX Runtime CUDA helper ===")
    helper_script = create_onnx_helper_script()
    print(f"Created helper script: {helper_script}")
    print("This script will help configure ONNX Runtime to use CUDA properly.")
    
    # Ask if user wants to run it now
    try:
        run_now = input("Do you want to run the ONNX CUDA helper now? (y/n): ").strip().lower()
        if run_now == 'y' or run_now == 'yes':
            print("\n=== Running ONNX Runtime CUDA helper ===")
            subprocess.call([sys.executable, str(helper_script)])
        else:
            print(f"\nYou can run the helper later with: python {helper_script}")
            print("For now, installing a default version of ONNX Runtime...")
            subprocess.call([sys.executable, "-m", "pip", "install", "onnxruntime==1.15.1"])
    except KeyboardInterrupt:
        print("\nSkipping ONNX Runtime configuration for now.")
        print(f"You can run the helper later with: python {helper_script}")
    
    # Additional instructions for all platforms
    print("\nPostinstallation steps:")
    print(f"1. If ONNX Runtime doesn't detect CUDA, run the helper script: python {helper_script}")
    print("   This will set up the necessary environment variables and install the correct version")
    print("")
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