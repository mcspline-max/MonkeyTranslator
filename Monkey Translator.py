import sys
import os
import json
import inspect
import traceback
import importlib
import importlib.machinery
import importlib.util
from pathlib import Path

# --- Path Setup ---
try: SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except: SCRIPT_DIR = os.getcwd()
if SCRIPT_DIR not in sys.path: sys.path.append(SCRIPT_DIR)

# =============================================================================
# EMBEDDED DAVINCI RESOLVE LOADER
# =============================================================================
def load_dynamic(module_name, file_path):
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 5:
        module = None
        spec = None
        loader = importlib.machinery.ExtensionFileLoader(module_name, file_path)
        if loader:
            spec = importlib.util.spec_from_loader(module_name, loader)
        if spec:
            module = importlib.util.module_from_spec(spec)
        if module:
            loader.exec_module(module)
        return module
    else:
        import imp
        return imp.load_dynamic(module_name, file_path)

def GetResolve():
    # Attempt to load the native DLL/SO to get the 'bmd' module (needed for UI)
    script_module = None
    env_lib_path = os.getenv("RESOLVE_SCRIPT_LIB")
    
    if env_lib_path:
        try:
            script_module = load_dynamic("fusionscript", env_lib_path)
        except ImportError: pass
        
    if not script_module:
        path = ""
        ext = ".so"
        if sys.platform.startswith("darwin"):
            path = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/"
        elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
            ext = ".dll"
            path = "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\"
        elif sys.platform.startswith("linux"):
            path = "/opt/resolve/libs/Fusion/"

        try:
            # Try to load the native library
            script_module = load_dynamic("fusionscript", path + "fusionscript" + ext)
        except Exception:
            pass

    # Now verify we have the resolve object
    resolve_obj = None
    
    # 1. Check Global (Fastest)
    try:
        if 'resolve' in globals(): 
            resolve_obj = globals()['resolve']
    except: pass

    # 2. Check Module
    if not resolve_obj and script_module:
        try:
            resolve_obj = script_module.scriptapp("Resolve")
        except: pass

    # --- THE FIX: Always return a pair ---
    return script_module, resolve_obj

# =============================================================================
# MAIN LOGIC
# =============================================================================

# Initialize
bmd, resolve = GetResolve()

if not resolve:
    error_msg = (
        "Could not connect to DaVinci Resolve.\n\n"
        "Please enable External Scripting:\n"
        "1. Open Resolve > Preferences > System > General\n"
        "2. Set 'External scripting using' to 'Local'\n"
        "3. Restart DaVinci Resolve"
    )
    print("CRITICAL ERROR: " + error_msg)
    
    # Windows Popup
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Connection Failed", 0x10)
        except: pass
    sys.exit()

if not bmd:
    # If we got resolve but no bmd module, we can't draw the UI.
    # Try one last ditch standard import just in case
    try:
        import DaVinciResolveScript as bmd
    except:
        print("Error: Could not load UIDispatcher (bmd module missing). UI cannot start.")
        sys.exit()

fusion = resolve.Fusion()
ui = fusion.UIManager
dispatcher = bmd.UIDispatcher(ui)

# --- GLOBAL STATE ---
global_proc = None
stop_requested = False
work_queue = []
work_index = 0
work_mode = "" 
valid_ocr_images = []

# --- Config ---
CONFIG_FILE = Path(SCRIPT_DIR) / "config.json"
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"api_key": "", "lang": "es", "custom_prompt": ""}

def save_config(data):
    try:
        with open(CONFIG_FILE, 'w') as f: json.dump(data, f)
    except: pass

# --- UI ---
def show_window():
    cfg = load_config()
    
    layout = ui.VGroup([
        ui.Label({ 'Text': "Monkey Translator V1.0", 'Font': ui.Font({'PixelSize': 20, 'Bold': True}), 'Alignment': { 'AlignHCenter': True } }),
        
        ui.VGroup({'Weight': 0, 'FrameStyle': 1}, [
            ui.HGroup([
                ui.Label({'Text': "API Key:", 'Weight': 0}),
                ui.LineEdit({'ID': "ApiKey", 'Text': cfg.get("api_key", ""), 'EchoMode': "Password"}),
            ]),
            ui.HGroup([
                ui.Label({'Text': "Source Lang:", 'Weight': 0}),
                ui.ComboBox({'ID': "LangCombo"}), 
            ]),
            ui.VGap(10),
        ]),

        ui.VGroup({'Weight': 0}, [
            ui.Button({'ID': "BtnAnalyze", 'Text': "1. Analyze & OCR"}),
            ui.Button({'ID': "BtnGenerate", 'Text': "2. Generate Translation"}),
            ui.Button({'ID': "BtnImport", 'Text': "3. Import to Timeline"}),
            ui.VGap(10),
        ]),

        ui.VGroup({'Weight': 0}, [
            ui.Button({'ID': "BtnSingle", 'Text': "⚡ Process Current Clip (Instant)"}),
            ui.Label({'Text': "Custom Instruction (Optional):"}),
            ui.TextEdit({'ID': "PromptInput", 'Height': 50, 'PlaceholderText': "Default: Translate to French..."}),
        ]),
        
        ui.VGap(10),
        ui.VGroup({'Weight': 0}, [
        ui.Button({'ID': "BtnStop", 'Text': "STOP ALL PROCESSES", 'Enabled': False, 'BackgroundColor': {'Color': '#883333'}, 'TextColor': {'Color': '#FFFFFF'}}),
        ui.VGap(5),
        ui.Label({'ID': "StatusLabel", 'Text': "Ready", 'Alignment': { 'AlignHCenter': True }, 'Color': {'Color': '#888888'}}),
        
        # HIDDEN TICKER
        ui.Button({'ID': "BtnTicker", 'Visible': False}),
        ]),
    ])

    win = dispatcher.AddWindow({ 'ID': 'MonkeyTranslatorWin', 'WindowTitle': 'Monkey Translator V1.0', 'Geometry': [ 500, 300, 400, 500 ] }, layout)
    itm = win.GetItems()
    itm['LangCombo'].AddItems(['es', 'fr', 'de', 'it', 'en'])
    itm['LangCombo'].CurrentText = cfg.get('lang', 'es')
    itm['PromptInput'].PlainText = cfg.get("custom_prompt", "")

    def update_status(msg):
        itm['StatusLabel'].Text = msg
        print(msg)

    def set_running(running):
        itm['BtnAnalyze'].Enabled = not running
        itm['BtnGenerate'].Enabled = not running
        itm['BtnImport'].Enabled = not running
        itm['BtnSingle'].Enabled = not running
        itm['BtnStop'].Enabled = running

    def get_current_prompt():
        user_text = itm['PromptInput'].PlainText
        if user_text and user_text.strip():
            return user_text.strip()
        prompt = (
            "Perform a realistic text replacement. Detect all text in this image and "
            "translate it into French. \n"
            "REQUIREMENTS:\n"
            "1. Replace the text in-place. strictly matching the original font style, "
            "size, color, weight, and perspective/orientation.\n"
            "2. Seamlessly reconstruct the background behind the new text (inpainting) "
            "so it looks like the original design.\n"
            "3. Do not alter any non-text visual elements, characters, or the aspect ratio.\n"
            "4. Output ONLY the resulting image."
        )
        return prompt

    # --- MAIN LOOP ---
    def process_next_step(ev):
        global work_index, stop_requested, valid_ocr_images
        
        try:
            if stop_requested:
                update_status("🛑 Stopped.")
                set_running(False)
                return

            if work_index >= len(work_queue):
                if work_mode == "OCR":
                    update_status(f"Mapping {len(valid_ocr_images)} images...")
                    global_proc.create_json_map(valid_ocr_images)
                    update_status("Analysis Complete.")
                elif work_mode == "GEMINI":
                    update_status("Generation Complete.")
                
                set_running(False)
                return

            item = work_queue[work_index]
            
            if work_mode == "OCR":
                update_status(f"OCR ({work_index+1}/{len(work_queue)}): {item.name}")
                if work_index == 0: global_proc.init_ocr(itm['LangCombo'].CurrentText)
                has_text, _ = global_proc.step_ocr(item)
                if has_text: valid_ocr_images.append(item.name)

            elif work_mode == "GEMINI":
                update_status(f"Gemini ({work_index+1}/{len(work_queue)}): {item['name']}")
                global_proc.step_gemini(item, get_current_prompt())

            work_index += 1
            ui.QueueEvent(itm['BtnTicker'], "Clicked", {})

        except Exception as e:
            update_status("Error in Loop (See Console)")
            traceback.print_exc()
            set_running(False)

    # --- HANDLERS ---
    def on_stop(ev):
        global stop_requested
        stop_requested = True
        update_status("Stopping...")

    def on_single(ev):
        global global_proc
        try:
            update_status("⚡ Processing Single Clip...")

            key = itm['ApiKey'].Text
            p_text = itm['PromptInput'].PlainText
            
            save_config({"api_key": key, "lang": itm['LangCombo'].CurrentText, "custom_prompt": p_text})

            if not global_proc:
                try:
                    import processor
                    importlib.reload(processor)
                    from processor import GeminiProcessor
                    global_proc = GeminiProcessor(resolve, resolve.GetProjectManager().GetCurrentProject(), key)
                except:
                    update_status("Error loading processor.")
                    return

            global_proc.api_key = key
            from google import genai
            global_proc.client = genai.Client(api_key=key)

            success, msg = global_proc.run_single_clip_workflow(get_current_prompt())
            update_status(msg)

        except Exception as e:
            update_status("Error (See Console)")
            traceback.print_exc()

    def on_analyze(ev):
        global global_proc, work_queue, work_index, work_mode, stop_requested, valid_ocr_images
        try:
            key = itm['ApiKey'].Text
            p_text = itm['PromptInput'].PlainText
            save_config({"api_key": key, "lang": itm['LangCombo'].CurrentText, "custom_prompt": p_text})
            
            import processor
            importlib.reload(processor)
            from processor import GeminiProcessor
            
            global_proc = GeminiProcessor(resolve, resolve.GetProjectManager().GetCurrentProject(), key)
            global_proc.ensure_structure()
            
            update_status("Exporting Stills...")
            global_proc.grab_stills()
            global_proc.process_drx()
            
            work_queue = global_proc.get_images_for_ocr()
            work_index = 0
            valid_ocr_images = []
            work_mode = "OCR"
            stop_requested = False
            
            set_running(True)
            ui.QueueEvent(itm['BtnTicker'], "Clicked", {})

        except Exception as e:
            update_status("Error (See Console)")
            traceback.print_exc()

    def on_generate(ev):
        global global_proc, work_queue, work_index, work_mode, stop_requested
        try:
            if not global_proc: return update_status("Run Analyze first.")
            from google import genai
            global_proc.client = genai.Client(api_key=itm['ApiKey'].Text)
            
            save_config({"api_key": itm['ApiKey'].Text, "lang": itm['LangCombo'].CurrentText, "custom_prompt": itm['PromptInput'].PlainText})

            work_queue = global_proc.get_gemini_list()
            work_index = 0
            work_mode = "GEMINI"
            stop_requested = False
            
            set_running(True)
            ui.QueueEvent(itm['BtnTicker'], "Clicked", {})
        except Exception as e:
            update_status("Error")
            traceback.print_exc()

    def on_import(ev):
        global global_proc
        try:
            if not global_proc:
                 import processor
                 importlib.reload(processor)
                 from processor import GeminiProcessor
                 global_proc = GeminiProcessor(resolve, resolve.GetProjectManager().GetCurrentProject(), itm['ApiKey'].Text)
            success, msg = global_proc.import_to_timeline()
            update_status(msg)
        except Exception as e:
            update_status("Error")
            traceback.print_exc()

    def on_close(ev):
        global stop_requested
        stop_requested = True
        win.Hide()
        dispatcher.ExitLoop()

    win.On.BtnSingle.Clicked = on_single
    win.On.BtnAnalyze.Clicked = on_analyze
    win.On.BtnGenerate.Clicked = on_generate
    win.On.BtnImport.Clicked = on_import
    win.On.BtnStop.Clicked = on_stop
    win.On.BtnTicker.Clicked = process_next_step
    win.On.MonkeyTranslatorWin.Close = on_close

    win.Show()
    dispatcher.RunLoop()

if __name__ == "__main__":
    show_window()