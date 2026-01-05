import os
import shutil
import json
import time
import ssl
import warnings
from pathlib import Path
from PIL import Image

# --- SILENCE WARNINGS ---
warnings.filterwarnings("ignore", message=".*pin_memory.*") 

try:
    import easyocr
    from google import genai
    from google.genai import types
except ImportError:
    pass 

class GeminiProcessor:
    def __init__(self, resolve, project, api_key):
        self.resolve = resolve
        self.project = project
        self.api_key = api_key
        self.client = None
        self.reader = None 
        
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except: pass
        
        # Setup paths
        self.tl = self.project.GetCurrentTimeline()
        raw_name = self.tl.GetName() if self.tl else "Untitled"
        self.tl_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        self.base_dir = Path.home() / "Documents" / "Monkey Translator"
        self.work_dir = self.base_dir / self.tl_name
        
        self.paths = {
            "ROOT": self.work_dir,
            "TEMP": self.work_dir / "TEMP",
            "DRX": self.work_dir / "TEMP" / "DRX",
            "EXP_STILLS": self.work_dir / "TEMP" / "EXP_STILLS",
            "EXP_STILLS_SINGLES": self.work_dir / "TEMP" / "EXP_STILLS_SINGLES",
            "RECEIVED": self.work_dir / "TEMP" / "RECEIVED",
            "JSON": self.work_dir / "TEMP" / f"{self.tl_name}.json",
            "JSON_SINGLE": self.work_dir / "TEMP" / "single_map.json",
            "OCR_CACHE": self.work_dir / "TEMP" / "ocr_cache.json"
        }
        
        self.ocr_cache = {}
        self.load_cache()

    def ensure_structure(self):
        for p in self.paths.values():
            if p.suffix in ['.json']: p.parent.mkdir(parents=True, exist_ok=True)
            else: p.mkdir(parents=True, exist_ok=True)
        return True

    def load_cache(self):
        if self.paths["OCR_CACHE"].exists():
            try:
                with open(self.paths["OCR_CACHE"], 'r') as f:
                    self.ocr_cache = json.load(f)
            except: pass

    def save_cache(self):
        with open(self.paths["OCR_CACHE"], 'w') as f:
            json.dump(self.ocr_cache, f)

    def _get_or_create_album(self, gallery, album_name):
        albums = gallery.GetGalleryStillAlbums()
        if albums:
            for album in albums:
                if gallery.GetAlbumName(album) == album_name:
                    return album
        new_album = gallery.CreateGalleryStillAlbum()
        gallery.SetAlbumName(new_album, album_name)
        return new_album

    # --- TRACK HELPER (NEW) ---
    def _ensure_track_2_exists(self):
        """Checks if V2 exists, creates it if not."""
        track_count = self.tl.GetTrackCount("video")
        if track_count < 2:
            print("Creating Video Track 2...")
            self.tl.AddTrack("video")

    # --- BATCH WORKFLOW ---
    def grab_stills(self):
        existing_jpgs = list(self.paths["EXP_STILLS"].glob("*.jpg"))
        if len(existing_jpgs) > 0:
            return True, f"Skipped export. Using {len(existing_jpgs)} existing stills."

        gallery = self.project.GetGallery()
        album = self._get_or_create_album(gallery, "To_Gemini_AI")
        gallery.SetCurrentStillAlbum(album)
        
        self.tl.GrabAllStills(1)
        stills = album.GetStills()
        
        if not stills: return False, "No stills found."
            
        album.ExportStills(stills, str(self.paths["EXP_STILLS"]), self.tl_name, "jpg")
        return True, f"Exported {len(stills)} stills."

    def process_drx(self):
        source_drx = list(self.paths["EXP_STILLS"].glob("*.drx"))
        if not source_drx: return True, "Using existing metadata."

        count = 0
        for f in source_drx:
            dest = self.paths["DRX"] / f.name
            try:
                text = f.read_text(encoding='utf-8')
                cleaned = text.replace('::', '')
                dest.write_text(cleaned, encoding='utf-8')
                f.unlink() 
                count += 1
            except: pass
        return True, f"Processed {count} metadata files."

    # --- SINGLE CLIP WORKFLOW ---
    def run_single_clip_workflow(self, prompt):
        # 1. SETUP & GRAB
        single_dir = self.paths["EXP_STILLS_SINGLES"]
        single_dir.mkdir(parents=True, exist_ok=True)

        gallery = self.project.GetGallery()
        album = self._get_or_create_album(gallery, "Gemini_Singles")
        gallery.SetCurrentStillAlbum(album)

        print("Grabbing Single Still...")
        current_still = self.tl.GrabStill()
        if not current_still: return False, "Could not grab still."

        base_name = f"Single_{int(time.time())}"
        
        if not album.ExportStills([current_still], str(single_dir), base_name, "jpg"):
            return False, "Export failed."
        
        # Wait for file
        timeout = 10 
        start_time = time.time()
        jpg_path = None
        
        print(f"Waiting for export: {base_name}...")
        while time.time() - start_time < timeout:
            candidates = list(single_dir.glob(f"{base_name}*.jpg"))
            if candidates:
                jpg_path = candidates[0] 
                time.sleep(0.5) 
                break
            time.sleep(0.5)
            
        if not jpg_path: return False, "Timeout: File not created."

        print(f"Detected file: {jpg_path.name}")
        drx_path = jpg_path.with_suffix(".drx")

        # 2. PROCESS DRX
        rec_tc = "00:00:00:00"
        duration = "1"
        
        if drx_path.exists():
            try:
                raw_text = drx_path.read_text(encoding='utf-8')
                clean_text = raw_text.replace('::', '')
                drx_path.write_text(clean_text, encoding='utf-8')
                
                import re
                match = re.search(r'RecTC="([^"]+)"', clean_text)
                if not match: match = re.search(r'<RecTC>(.*?)</RecTC>', clean_text)
                if match:
                    rec_tc = match.group(1)
                    self.tl.SetCurrentTimecode(rec_tc)
                    video_item = self.tl.GetCurrentVideoItem()
                    if video_item: duration = str(video_item.GetDuration())
            except: pass

        # 3. SEND TO GEMINI (4K)
        print(f"Sending {jpg_path.name} to Gemini (4K)...")
        if not self.client: return False, "API Key missing."
        
        try:
            img = Image.open(jpg_path)
            response = self.client.models.generate_content(
                model="gemini-3-pro-image-preview", 
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(image_size="4K")
                )
            )
            
            generated = False
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        gen_img = part.as_image()
                        save_name = f"GEMINI_{base_name}.jpg" 
                        save_path = self.paths["RECEIVED"] / save_name
                        
                        gen_img.save(save_path)
                        
                        clean_img = Image.open(save_path)
                        data = list(clean_img.getdata())
                        final_img = Image.new(clean_img.mode, clean_img.size)
                        final_img.putdata(data)
                        final_img.save(save_path)
                        generated = True
                        break 
            
            if not generated: return False, "Gemini did not return an image."
            
        except Exception as e:
            return False, f"Gemini API Error: {e}"

        # 4. IMPORT & APPEND
        media_pool = self.project.GetMediaPool()
        root_folder = media_pool.GetRootFolder()
        
        target_bin = None
        for f in root_folder.GetSubFolderList():
            if f.GetName() == "FROM_GEMINI": target_bin = f; break
        if not target_bin: target_bin = media_pool.AddSubFolder(root_folder, "FROM_GEMINI")
        media_pool.SetCurrentFolder(target_bin)
        
        gen_file_path = str(self.paths["RECEIVED"] / f"GEMINI_{base_name}.jpg")
        media_pool.ImportMedia([gen_file_path])
        
        clips = target_bin.GetClipList()
        target_clip = next((c for c in clips if c.GetName() == f"GEMINI_{base_name}.jpg"), None)
        
        if target_clip:
            # --- FIX: ENSURE TRACK 2 EXISTS ---
            self._ensure_track_2_exists()
            # ----------------------------------

            fps = float(self.tl.GetSetting("timelineFrameRate"))
            try:
                h, m, s, f = map(int, rec_tc.split(':'))
                rec_frame = int((h*3600+m*60+s)*fps + f)
            except: rec_frame = 0
            
            dur_int = int(float(duration))
            target_clip.SetMarkInOut(1, dur_int)
            
            media_pool.AppendToTimeline([{
                'mediaPoolItem': target_clip,
                'timeline': self.tl, 
                'startFrame': 0,
                'endFrame': dur_int,
                'recordFrame': rec_frame,
                'trackIndex': 2, # Now guaranteed to exist
                'mediaType': 1 
            }])
            
            return True, "Single clip processed (4K) and appended to Track 2."
        
        return False, "Import failed."

    # --- OCR HELPERS ---
    def init_ocr(self, lang):
        if not self.reader:
            print(f"Loading OCR Model ({lang})...")
            # SSL Fix for Mac
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError: pass
            else: ssl._create_default_https_context = _create_unverified_https_context

            gpu_enable = False
            try:
                import torch
                if torch.cuda.is_available(): gpu_enable = True
                elif torch.backends.mps.is_available(): gpu_enable = True
            except: pass

            self.reader = easyocr.Reader([lang], gpu=gpu_enable)

    def get_images_for_ocr(self):
        return list(self.paths["EXP_STILLS"].glob("*.jpg"))

    def step_ocr(self, img_path):
        if img_path.name in self.ocr_cache:
            return self.ocr_cache[img_path.name], False
        try:
            result = self.reader.readtext(str(img_path), detail=0, text_threshold=0.85)
            has_text = bool(result)
            self.ocr_cache[img_path.name] = has_text
            self.save_cache()
            return has_text, True
        except: return False, True

    def create_json_map(self, image_list):
        data_map = []
        for img_name in image_list:
            drx_path = self.paths["DRX"] / f"{Path(img_name).stem}.drx"
            rec_tc = "00:00:00:00"
            duration = "1"

            if drx_path.exists():
                try:
                    content = drx_path.read_text(encoding='utf-8')
                    if 'RecTC' in content:
                        import re
                        match = re.search(r'RecTC="([^"]+)"', content)
                        if not match: match = re.search(r'<RecTC>(.*?)</RecTC>', content)
                        if match:
                            rec_tc = match.group(1)
                            self.tl.SetCurrentTimecode(rec_tc)
                            video_item = self.tl.GetCurrentVideoItem()
                            if video_item: duration = str(video_item.GetDuration())
                except: pass
            
            data_map.append({"name": img_name, "RecTC": rec_tc, "Duration": duration})

        json_path = self.paths["JSON"]
        if json_path.exists():
            try: json_path.unlink()
            except: 
                try: json_path.rename(json_path.with_name(f"trash_{int(time.time())}.json"))
                except: json_path = json_path.parent / f"{self.tl_name}_{int(time.time())}.json"
                self.paths["JSON"] = json_path

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data_map, f, indent=4)
        return True

    # --- GEMINI HELPERS ---
    def get_gemini_list(self):
        if not self.paths["JSON"].exists(): return []
        with open(self.paths["JSON"], 'r', encoding='utf-8') as f:
            return json.load(f)

    def step_gemini(self, item, prompt):
        img_name = item['name']
        src_path = self.paths["EXP_STILLS"] / img_name
        if not src_path.exists(): return False

        try:
            img = Image.open(src_path)
            response = self.client.models.generate_content(
                model="gemini-3-pro-image-preview", 
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(image_size="1K")
                )
            )
            
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        gen_img = part.as_image()
                        save_name = f"GEMINI_{Path(img_name).stem}.jpg"
                        save_path = self.paths["RECEIVED"] / save_name
                        gen_img.save(save_path)
                        
                        clean_img = Image.open(save_path)
                        data = list(clean_img.getdata())
                        final_img = Image.new(clean_img.mode, clean_img.size)
                        final_img.putdata(data)
                        final_img.save(save_path)
                        return True
            time.sleep(1)
            return False
        except Exception as e:
            print(f"Gemini Error {img_name}: {e}")
            return False

    def import_to_timeline(self):
        media_pool = self.project.GetMediaPool()
        root_folder = media_pool.GetRootFolder()
        target_bin = None
        for f in root_folder.GetSubFolderList():
            if f.GetName() == "FROM_GEMINI": target_bin = f; break
        if not target_bin: target_bin = media_pool.AddSubFolder(root_folder, "FROM_GEMINI")
        media_pool.SetCurrentFolder(target_bin)
        
        files = [str(p) for p in self.paths["RECEIVED"].glob("*.jpg")]
        if files: media_pool.ImportMedia(files)
        
        if not self.paths["JSON"].exists(): return False, "JSON Map missing."
        with open(self.paths["JSON"], 'r', encoding='utf-8') as f: data_map = json.load(f)
        
        clips = target_bin.GetClipList()
        fps = float(self.tl.GetSetting("timelineFrameRate"))
        append_data = []
        
        # --- FIX: ENSURE TRACK 2 EXISTS (BATCH) ---
        self._ensure_track_2_exists()
        # ------------------------------------------

        for item in data_map:
            gemini_name = f"GEMINI_{Path(item['name']).stem}.jpg"
            target_clip = next((c for c in clips if c.GetName() == gemini_name), None)
            if target_clip:
                rec_tc = item['RecTC']
                try:
                    h, m, s, f = map(int, rec_tc.split(':'))
                    rec_frame = int((h*3600+m*60+s)*fps + f)
                except: rec_frame = 0
                
                dur_int = int(float(item['Duration']))
                target_clip.SetMarkInOut(1, dur_int)
                
                append_data.append({
                    'mediaPoolItem': target_clip,
                    'timeline': self.tl, 
                    'startFrame': 0,
                    'endFrame': dur_int,
                    'recordFrame': rec_frame,
                    'trackIndex': 2,
                    'mediaType': 1 
                })

        if append_data: media_pool.AppendToTimeline(append_data)
        return True, "Clips appended."