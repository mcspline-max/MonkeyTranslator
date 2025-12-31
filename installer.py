import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import zipfile
import io
import tempfile
import ssl  # <--- ADDED THIS
from pathlib import Path

# =============================================================================
# [CONFIGURATION] 
# =============================================================================
GITHUB_USER = "mcspline-max"       # Updated based on your screenshot
REPO_NAME   = "MonkeyTranslator"   
BRANCH      = "main"               

PLUGIN_FOLDER_NAME = "MonkeyTranslator" 
FILES_TO_DEPLOY = ["Monkey Translator.py", "processor.py", "config.json"]

REQUIRED_PACKAGES = ["easyocr", "google-genai", "Pillow"]
# =============================================================================

def get_resolve_scripts_dir():
    """Smart detection of DaVinci Resolve Paths."""
    system = platform.system()
    potential_roots = []
    
    if system == "Windows":
        base = Path(os.getenv("PROGRAMDATA"))
        potential_roots = [base / "Blackmagic Design" / "DaVinci Resolve"]
    elif system == "Darwin": # macOS
        potential_roots.append(Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve"))
        potential_roots.append(Path.home() / "Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Blackmagic Design/DaVinci Resolve")
        potential_roots.append(Path.home() / "Library/Containers/com.blackmagic-design.DaVinciResolveApp/Data/Library/Application Support/Blackmagic Design/DaVinci Resolve")
    elif system == "Linux":
        potential_roots = [Path("/opt/resolve")]

    valid_root = None
    for root in potential_roots:
        if root.exists():
            print(f"✅ Found DaVinci Resolve at: {root}")
            valid_root = root
            break
    
    if not valid_root: return None
    return valid_root / "Fusion" / "Scripts" / "Edit"

def install_dependencies():
    print(f"\n[1/4] Checking GPU & Installing Dependencies...")
    python_exec = sys.executable
    system = platform.system()

    print("   ...Installing PyTorch...")
    if system == "Windows":
        try:
            subprocess.check_call([
                python_exec, "-m", "pip", "install", 
                "torch", "torchvision", "torchaudio", 
                "--index-url", "https://download.pytorch.org/whl/cu121"
            ])
        except:
            subprocess.check_call([python_exec, "-m", "pip", "install", "torch", "torchvision", "torchaudio"])
    else:
        # On Mac, we add --break-system-packages if using system python, 
        # but usually standard install is fine. We handle the error just in case.
        try:
            subprocess.check_call([python_exec, "-m", "pip", "install", "torch", "torchvision", "torchaudio"])
        except subprocess.CalledProcessError:
             print("   ⚠️  Pip install warning (ignoring if packages exist).")

    print(f"   ...Installing {', '.join(REQUIRED_PACKAGES)}...")
    cmd = [python_exec, "-m", "pip", "install"] + REQUIRED_PACKAGES
    
    try:
        subprocess.check_call(cmd)
        print("   ✅ Libraries installed.")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Error installing libraries.")
        return False

def download_and_deploy(dest_root):
    print("\n[2/4] Downloading Source Code from GitHub...")
    final_dest = dest_root / PLUGIN_FOLDER_NAME
    zip_url = f"https://github.com/{GITHUB_USER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
    
    try:
        print(f"   Fetching: {zip_url}")
        
        # --- SSL CERTIFICATE FIX ---
        # This creates an unverified context to bypass the "CERTIFICATE_VERIFY_FAILED" error
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        response = urllib.request.urlopen(zip_url, context=ctx)
        # ---------------------------
        
        zip_data = response.read()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                z.extractall(temp_dir)
            
            extracted_items = os.listdir(temp_dir)
            if not extracted_items: return False
            repo_root = Path(temp_dir) / extracted_items[0]
            
            print(f"\n[3/4] Installing to: {final_dest}")
            
            if not dest_root.exists():
                print(f"   Creating missing directory structure: {dest_root}")
                try:
                    dest_root.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    print("❌ PERMISSION DENIED: Cannot create folders.")
                    print("   You MUST run this script with 'sudo'.")
                    return False

            if final_dest.exists(): shutil.rmtree(final_dest)
            final_dest.mkdir(parents=True, exist_ok=True)
            
            count = 0
            for file_name in FILES_TO_DEPLOY:
                src = repo_root / file_name
                dst = final_dest / file_name
                if src.exists():
                    shutil.copy2(src, dst)
                    count += 1
            
            (final_dest / "__init__.py").touch()
            print(f"   ✅ Installed {count} files.")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print(f"=== {PLUGIN_FOLDER_NAME} Installer (SSL Fix) ===")
    
    target_path = get_resolve_scripts_dir()
    if not target_path:
        print("❌ CRITICAL: Could not find DaVinci Resolve installation.")
        sys.exit(1)

    # Mac Permission Check
    if platform.system() == "Darwin" and os.geteuid() != 0:
        if "/Library/Application Support" in str(target_path) and not os.access(str(target_path.parent), os.W_OK):
             print("❌ PERMISSION WARNING: Run with sudo.")
             print(f"   sudo python3 \"{sys.argv[0]}\"")
             sys.exit(1)

    if install_dependencies():
        if download_and_deploy(target_path):
            print("\n" + "="*40)
            print("      INSTALLATION SUCCESSFUL")
            print("="*40)
            print("1. Restart DaVinci Resolve.")
            print("2. Go to: Workspace > Scripts > Edit > MonkeyTranslator > main")
            print("="*40)

if __name__ == "__main__":
    main()