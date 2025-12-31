# 🐒 Monkey Translator for DaVinci Resolve

**Monkey Translator** is a powerful Workflow Integration plugin for DaVinci Resolve Studio & Free. It uses **Google Gemini 3.0 AI** to automatically detect text in your video frames, translate it (or modify it based on your instructions), and seamlessly import the translated images back into your timeline.

---

## ✨ Features

*   **⚡ Instant Single Clip Process:** Translate the clip under your playhead in seconds with one click.
*   **ax Batch Processing:** Analyze an entire timeline, perform OCR to detect text, and batch-translate everything.
*   **🤖 Gemini 3.0 Pro Vision:** Uses the latest Google AI models for high-quality text replacement while preserving the background.
*   **🎨 4K & HD Support:** Generates high-resolution images suitable for professional workflows.
*   **🚀 GPU Acceleration:** Uses CUDA (Windows) and Metal/MPS (Mac) for fast OCR scanning.
*   **📝 Custom Prompts:** Tell the AI exactly what to do (e.g., "Translate to French", "Remove text only", "Change text to 'Hello'").
*   **🔄 Auto-Import:** Automatically creates specific bins and appends clips to the correct timeline track.

---

## 🛠 Prerequisites

1.  **DaVinci Resolve** (Free or Studio version 18/19+).
2.  **Python 3.6+** installed on your system.
3.  A **Google Gemini API Key** (Get it for free [here](https://aistudio.google.com/app/apikey)).

---

## 📥 Installation

### 🍎 MacOS
1.  Download the **`MonkeyTranslator_Mac_Installer.command`** from the Releases Page: https://github.com/mcspline-max/MonkeyTranslator/releases
2.  Open a terminal and type `chmod +x` and drag and drop the file you downloaded in terminal window, then press Enter
3.  Type: `sudo` and **drag and drop the file you downloaded** in terminal window, then press **Enter**.
4.  Wait for the installation process to finish
5.  Restart Resolve.

### 🪟 Windows
1.  Download the **`Windows - Monkey Translator Installer V1.0.bat`** from the Releases Page: https://github.com/mcspline-max/MonkeyTranslator/releases
2.  Double-click `Windows - Monkey Translator Installer V1.0.bat`.
3.  If prompted by UAC, click **Yes** to run as Administrator.
4.  Wait for the installation to finish.
5.  Restarts Resolve.
---

## ⚙️ Initial Setup (Crucial Step)

Before running the script, you **must** enable external scripting in DaVinci Resolve, or the plugin will fail to connect.

1.  Open **DaVinci Resolve**.
2.  Go to the menu: **DaVinci Resolve** > **Preferences**.
3.  Select the **System** tab and go to **General**.
4.  Find the setting **"External scripting using"**.
5.  Change it from **None** to **Local**.
6.  **Restart DaVinci Resolve**.

---

## 🚀 How to Use

1.  Open your project in DaVinci Resolve.
2.  Go to the top menu: **Workspace** > **Scripts** > **Edit** > **MonkeyTranslator** > **MonkeyTranslator**.
3.  The plugin window will appear.

### 🔑 Configuration
*   **API Key:** Paste your Google Gemini API Key.
*   **Source Lang:** Select the language for OCR detection (e.g., 'es' for Spanish text).
*   **Custom Instruction:** (Optional) Type what you want the AI to do.
    *   *Default:* "Detect text, translate to French contextually..."
    *   *Example:* "Replace text with 'CENSORED'"

### ⚡ Mode A: Instant Single Clip
1.  Place your playhead over a clip in the timeline.
2.  Click **"⚡ Process Current Clip (Instant)"**.
3.  The script will grab the frame, send it to AI, and place the result on **Video Track 2**.

### 📦 Mode B: Batch Workflow
1.  Click **"1. Analyze & OCR"**: Scans the whole timeline for text.
2.  Click **"2. Generate Translation"**: Sends all detected images to Gemini AI.
3.  Click **"3. Import to Timeline"**: Imports all generated images and places them in sync on Video Track 2.

---

## ❓ Troubleshooting

**"Could not connect to DaVinci Resolve"**
*   Did you restart Resolve after installing?
*   Did you set "External scripting using" to **Local** in Preferences? (See Initial Setup above).

**Script opens and closes immediately**
*   Ensure Python is installed on your computer. Open a terminal/command prompt and type `python --version` to check.
  
---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Disclaimer:** This tool uses Google Gemini API. Usage costs may apply depending on your API plan (Free tier is available). This tool is not affiliated with Blackmagic Design.
