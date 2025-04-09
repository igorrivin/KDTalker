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

def find_wsl_nvidia_paths():
    """Find NVIDIA/CUDA paths specific to WSL2"""
    wsl_specific_paths = []
    
    # Check for WSL-specific NVIDIA paths
    possible_wsl_paths = [
        '/usr/lib/wsl/lib',
        '/usr/lib/wsl/drivers',
        '/usr/lib/wsl/nvidia',
    ]
    
    for path in possible_wsl_paths:
        if os.path.exists(path):
            wsl_specific_paths.append(path)
    
    # Try to locate WSL NVIDIA driver path by checking loaded modules
    try:
        lsmod_output = subprocess.check_output(['lsmod']).decode()
        if 'nvidia' in lsmod_output:
            # Check where NVIDIA modules are located
            modinfo_output = subprocess.check_output(['modinfo', 'nvidia']).decode()
            for line in modinfo_output.splitlines():
                if line.startswith('filename:'):
                    module_path = line.split()[1]
                    driver_path = os.path.dirname(os.path.dirname(module_path))
                    if driver_path and os.path.exists(driver_path) and driver_path not in wsl_specific_paths:
                        wsl_specific_paths.append(driver_path)
    except:
        pass
    
    return wsl_specific_paths

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
    
    # Check for nvidia-smi path first
    try:
        nvidia_smi_path = subprocess.check_output(['which', 'nvidia-smi']).decode().strip()
        if nvidia_smi_path:
            # nvidia-smi typically in /usr/bin or similar, so we need to find actual CUDA path
            try:
                # Try to use nvidia-smi to find the CUDA version
                nvidia_smi_output = subprocess.check_output(['nvidia-smi']).decode()
                # Usually displays CUDA Version: X.Y
                for line in nvidia_smi_output.splitlines():
                    if 'CUDA Version:' in line:
                        cuda_version = line.split('CUDA Version:')[1].strip()
                        # Check if there's a matching CUDA path
                        specific_cuda_path = f'/usr/local/cuda-{cuda_version}'
                        if os.path.exists(specific_cuda_path):
                            return specific_cuda_path
            except:
                pass
    except:
        pass
    
    # Check common paths
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    # Try to find using which nvcc
    try:
        nvcc_path = subprocess.check_output(['which', 'nvcc']).decode().strip()
        if nvcc_path:
            # nvcc is typically in the bin subdirectory of CUDA
            cuda_path = os.path.dirname(os.path.dirname(nvcc_path))
            if os.path.exists(cuda_path):
                return cuda_path
    except:
        pass
    
    # For WSL, try some additional methods
    if is_wsl():
        try:
            # In WSL2, sometimes CUDA is installed via CUDA toolkit in a different location
            whereis_output = subprocess.check_output(['whereis', 'cuda']).decode().strip()
            paths = whereis_output.split(':')[1:]
            for path in paths:
                path = path.strip()
                if path and os.path.exists(path) and os.path.isdir(path):
                    return path
        except:
            pass
    
    return None

def create_onnx_helper_script():
    """Create a helper script to properly configure ONNX Runtime with CUDA"""
    cuda_path = find_cuda_path()
    script_path = Path('fix_onnxruntime_cuda.py')
    
    # Create a much simpler script that's less prone to errors
    script_content = """#!/usr/bin/env python
# This script helps configure ONNX Runtime to use CUDA
import os
import sys
import subprocess
from pathlib import Path

def find_cuda_path():
    \"\"\"Find CUDA installation path\"\"\"
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
    
    # Try to get CUDA path from nvidia-smi
    try:
        nvidia_smi_output = subprocess.check_output(['nvidia-smi']).decode()
        for line in nvidia_smi_output.splitlines():
            if 'CUDA Version:' in line:
                cuda_version = line.split('CUDA Version:')[1].strip().split()[0]
                cuda_path = f'/usr/local/cuda-{cuda_version}'
                if os.path.exists(cuda_path):
                    return cuda_path
    except:
        pass
    
    # Check common paths
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
            
    # Try to find using which nvcc
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

def find_cuda_libs():
    \"\"\"Find CUDA library paths\"\"\"
    cuda_path = find_cuda_path()
    lib_paths = []
    
    # Add standard CUDA lib paths if CUDA found
    if cuda_path:
        for subdir in ['lib64', 'lib', 'lib/x64']:
            full_path = os.path.join(cuda_path, subdir)
            if os.path.exists(full_path):
                lib_paths.append(full_path)
    
    # Check for WSL specific paths
    try:
        is_wsl = False
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    is_wsl = True
        
        if is_wsl:
            # WSL-specific NVIDIA paths
            wsl_paths = [
                '/usr/lib/wsl/lib',
                '/usr/lib/wsl/drivers',
                '/usr/lib/wsl/nvidia',
                '/usr/lib/wsl/nvidia/current/lib64',
                '/usr/lib/x86_64-linux-gnu',
            ]
            
            for path in wsl_paths:
                if os.path.exists(path):
                    lib_paths.append(path)
    except:
        pass
        
    return lib_paths

def main():
    print("ONNX Runtime CUDA Configuration Helper")
    print("======================================")
    
    # Find CUDA installation
    cuda_path = find_cuda_path()
    if cuda_path:
        print(f"Found CUDA at: {cuda_path}")
        os.environ['CUDA_PATH'] = cuda_path
    else:
        print("Could not auto-detect CUDA path.")
        cuda_path_input = input("Please enter your CUDA installation path (e.g., /usr/local/cuda): ")
        if cuda_path_input and os.path.exists(cuda_path_input):
            cuda_path = cuda_path_input
            os.environ['CUDA_PATH'] = cuda_path
        else:
            print("No valid CUDA path provided. ONNX Runtime may not use CUDA.")
    
    # Find and set LD_LIBRARY_PATH
    lib_paths = find_cuda_libs()
    if lib_paths:
        print(f"Found CUDA library paths:")
        for path in lib_paths:
            print(f"  - {path}")
            
        # Set LD_LIBRARY_PATH
        ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
        new_path = ':'.join(lib_paths)
        if ld_lib_path:
            new_path = f"{new_path}:{ld_lib_path}"
        os.environ['LD_LIBRARY_PATH'] = new_path
        print(f"Set LD_LIBRARY_PATH to include CUDA libraries")
    else:
        print("Warning: No CUDA library paths found.")
        
    # Determine CUDA version for appropriate ORT version
    cuda_version = None
    if cuda_path:
        try:
            nvcc_path = os.path.join(cuda_path, 'bin', 'nvcc')
            if os.path.exists(nvcc_path):
                nvcc_output = subprocess.check_output([nvcc_path, '--version']).decode()
                for line in nvcc_output.splitlines():
                    if "release" in line and "V" in line:
                        version_part = line.split("V")[1].split(".")[0]
                        if version_part:
                            cuda_version = int(version_part)
                        break
        except:
            try:
                # Try getting version from nvidia-smi as fallback
                nvidia_smi_output = subprocess.check_output(['nvidia-smi']).decode()
                for line in nvidia_smi_output.splitlines():
                    if 'CUDA Version:' in line:
                        cuda_version = int(float(line.split('CUDA Version:')[1].strip().split()[0]))
                        break
            except:
                print("Could not determine CUDA version")
    
    # Uninstall any previous onnxruntime
    print("\\nRemoving any existing onnxruntime installations...")
    subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime", "onnxruntime-gpu"])
    
    # Install appropriate ONNX Runtime version
    if cuda_version:
        print(f"Detected CUDA version: {cuda_version}")
        
        if cuda_version >= 12:
            print("Installing onnxruntime 1.16.3 for CUDA 12.x...")
            onnx_version = "1.16.3"
        elif cuda_version >= 11:
            print("Installing onnxruntime 1.15.1 for CUDA 11.x...")
            onnx_version = "1.15.1"
        else:
            print("Installing onnxruntime 1.14.1 for older CUDA versions...")
            onnx_version = "1.14.1"
            
        # Try to install
        success = False
        
        # Try standard onnxruntime first
        try:
            print(f"Installing onnxruntime {onnx_version}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"onnxruntime=={onnx_version}"])
            success = True
        except:
            print("Standard onnxruntime installation failed, trying alternatives...")
        
        # If standard fails, try onnxruntime-gpu
        if not success:
            try:
                print("Trying onnxruntime-gpu...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "onnxruntime-gpu"])
                success = True
            except:
                print("onnxruntime-gpu installation failed.")
                
        # If both fail, try an older version
        if not success:
            try:
                older_version = "1.13.1"
                print(f"Trying older onnxruntime {older_version}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", f"onnxruntime=={older_version}"])
                success = True
            except:
                print("All onnxruntime installation attempts failed.")
    else:
        print("No CUDA version detected, installing CPU-only onnxruntime...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "onnxruntime==1.15.1"])
        except:
            print("Installation failed. You may need to install manually.")
    
    # Verify CUDA is available
    print("\\nVerifying ONNX Runtime CUDA support...")
    try:
        # Run verification in the same process
        import onnxruntime as ort
        
        print(f"CUDA_PATH: {os.environ.get('CUDA_PATH', 'Not set')}")
        print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not set')}")
        
        providers = ort.get_available_providers()
        print(f"Available providers: {providers}")
        
        if 'CUDAExecutionProvider' in providers:
            print("SUCCESS: CUDA is available for ONNX Runtime")
            try:
                device_info = ort.get_device()
                print(f"CUDA device info: {device_info}")
            except:
                print("Note: Could not query device info, but provider is available")
        else:
            print("WARNING: CUDA is NOT available for ONNX Runtime")
            
            # Try comparing with PyTorch
            try:
                import torch
                if torch.cuda.is_available():
                    print("Note: PyTorch CAN see CUDA but ONNX Runtime cannot")
                    print(f"PyTorch CUDA info: {torch.cuda.get_device_name(0)}")
                    print("This suggests an onnxruntime CUDA configuration issue")
                else:
                    print("Note: PyTorch also cannot see CUDA")
                    print("This indicates a system-wide CUDA configuration issue")
            except ImportError:
                print("Could not check PyTorch for comparison (not installed)")
    except ImportError:
        print("ERROR: Could not import onnxruntime. Installation may have failed.")
    except Exception as e:
        print(f"Error during verification: {e}")
    
    # Print final instructions
    print("\\nTo ensure CUDA is available for future sessions:")
    print("  1. Add these lines to your .bashrc or .bash_profile:")
    if cuda_path:
        print(f"     export CUDA_PATH={cuda_path}")
    else:
        print("     export CUDA_PATH=/usr/local/cuda")
    
    if lib_paths:
        print(f"     export LD_LIBRARY_PATH={':'.join(lib_paths)}:$LD_LIBRARY_PATH")
    else:
        print("     export LD_LIBRARY_PATH=$CUDA_PATH/lib64:$LD_LIBRARY_PATH")
    
    print("  2. Restart your terminal or run 'source ~/.bashrc'")
    print("  3. When running Python, make sure to specify CUDA providers:")
    print("     session = onnxruntime.InferenceSession(model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])")

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
    
    # Install critical dependencies first
    print("Installing critical dependencies first...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "onnxruntime-gpu"])
        print("Critical dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing critical dependencies: {e}")
        print("Trying to install them separately...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
            print("OpenCV installed successfully!")
        except:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python-headless"])
                print("OpenCV headless installed successfully!")
            except:
                print("ERROR: Failed to install OpenCV. Please install it manually.")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "onnxruntime-gpu"])
            print("onnxruntime-gpu installed successfully!")
        except:
            print("Failed to install onnxruntime-gpu.")
    
    # Install other dependencies
    print(f"Installing remaining dependencies from {req_file}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print("Installation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        print("Will continue with essential tools installation...")
    
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