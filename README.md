<div align="center">

# 📱 GUIPy Scrcpy Wrapper
**An Advanced Python Controller for Scrcpy**

[![Scrcpy Repository](https://img.shields.io/badge/scrcpy-GitHub-blue?logo=github)](https://github.com/Genymobile/scrcpy)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Genymobile/scrcpy/blob/master/LICENSE)

**GUIPy Scrcpy** is a robust Python wrapper designed to manage `scrcpy` sessions programmatically. It allows Python GUI applications to orchestrate device mirroring with granular control over video, audio, inputs, and process lifecycle.

It supports **auto-detection** of binaries, handling both local environments (ENV) and system PATHs, making it ideal for portable tools.

</div>


---

## ✨ Key Features

| Category | Capabilities |
| :--- | :--- |
| **🔌 Connection** | Auto-detect `scrcpy`/`adb` binaries, listing devices (Brand/Model), USB, TCP/IP, & Serial modes. |
| **🎥 Media** | Full control over **Video** (FPS, Codec, Bitrate, Buffer) and **Audio** (Source, Codec, Bitrate). |
| **📷 Camera** | Dedicated Camera Mode handling with **auto-removal of incompatible flags** (e.g., `--turn-screen-off`). |
| **🎮 Input** | Configurable input drivers (`UHID`, `AOA`) for Keyboard, Mouse, and Gamepads. |
| **🖥️ Windowing** | Custom window titles, borderless mode, "Always on Top", fullscreen, and exact positioning (X/Y). |
| **🛡️ Safety** | Clean start/stop lifecycle management with fallback `taskkill` to prevent zombie processes. |

---

## 📦 Installation

Install the required dependencies via pip:

```bash
pip install -r requirements.txt
```

> **Note:** Ensure you have `scrcpy` and `adb` binaries available on your system or in a local folder.

---

## 🚀 Usage Guide

This module is designed to be imported into your Python project. Below are examples using the `ScrcpyClient` class.

### 1. Initialization & Device Discovery

Initialize the client by pointing to your scrcpy folder (or leave `ENV` empty to use system PATH).

```python
from scrcpy_wrapper import ScrcpyClient

# Initialize client (debug=True prints generated commands to console)
client = ScrcpyClient(ENV=r"C:\scrcpy_win64", debug=True)

# List connected devices
devices = client.list_devices()
print(devices)
```

**Output Example:**
```json
[
  {"serial": "ABC12345", "brand": "Xiaomi", "model": "Mi 11"},
  {"serial": "192.168.1.5:5555", "brand": "Samsung", "model": "Galaxy S21"}
]
```

---

### 2. Configuration Modules

You can chain configurations before starting the session.

#### 🎥 Video Settings
```python
client.set_video(
    fps=60,             # Target FPS
    bitrate="18M",      # Bitrate (e.g., 4M, 16M)
    codec="h265",       # h264, h265, or av1
    max_size=1920,      # Max width/height
    buffer=50           # Latency buffer in ms
)
```

#### 🎧 Audio Settings
```python
client.set_audio(
    source="mic",       # 'output' (device audio) or 'mic' (microphone)
    bitrate="256k",
    codec="aac"         # opus, aac, raw
)
```

#### 📷 Camera Mode (V4L2)
*Automatically sanitizes flags: Removes `--turn-screen-off` and `--stay-awake` which cause crashes in camera mode.*

```python
client.set_camera(
    video_source="camera",
    camera_id=0,            # 0 = Back, 1 = Front (usually)
    camera_size="1920x1080"
)
```

#### 🖥️ Window & UI Options
```python
client.set_application(
    title="My Mirror",
    fullscreen=False,
    always_top=True,
    borderless=False,
    width=900,
    height=1600
)
```

#### 🎮 Input Control
```python
client.set_controller(
    keyboard="uhid",    # uhid, aoa, or disabled
    mouse="uhid",       # uhid, aoa, or disabled
    gamepad="aoa"       # uhid, aoa, or disabled
)
```

#### 🌐 Connection Methods
**USB (Default):**
```python
client.set_connection(usb=True)
```
**Wireless (TCP/IP):**
```python
client.set_connection(tcp=True, tcpip="192.168.1.40:5555")
```

---

### 3. Lifecycle Management

#### ▶️ Start Session
Starts the scrcpy subprocess non-blocking.

```python
# Start the process
proc = client.start()

# Wait for process to finish (blocking)
# proc.wait() 
```

#### ⛔ Stop Session
Gracefully terminates the session. If the process is unresponsive, it forces a kill on the specific scrcpy instance.

```python
client.stop()
```

#### 💾 Recording
Record the screen while mirroring.

```python
client.set_advanced(
    record_file="gameplay_session.mp4",
    record_format="mp4"
)
```

---

## 🧪 Complete Example

Here is a full implementation combining the features above.

```python
import time
from scrcpy_wrapper import ScrcpyClient

def main():
    # 1. Setup
    client = ScrcpyClient(ENV=r"C:\scrcpy", debug=True)
    
    # 2. Check Devices
    devices = client.list_devices()
    if not devices:
        print("No devices found.")
        return

    print(f"Connecting to: {devices[0]['model']}")

    # 3. Configure
    client.set_video(fps=60, bitrate="12M", codec="h264")
    client.set_audio(bitrate="128k")
    client.set_application(title="GUIPy Mirror", always_top=True)
    
    # 4. Start
    proc = client.start()
    print("Scrcpy started. Press Ctrl+C to stop.")

    try:
        # Keep main thread alive while scrcpy runs
        proc.wait() 
    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()

if __name__ == "__main__":
    main()
```

---

## 💡 About The Project: What is GUIPy?

**GUIPy** (GUI + Python) is the architecture powering the "Scrcpy Ultimate" application. It represents a modern hybrid approach to desktop app development.

It utilizes **Eel**, a library that bridges Python with a web frontend (HTML/JS/CSS), allowing for a clean, responsive UI with a powerful Python backend.

### Architecture Overview

1.  **Frontend (`index.html` / JavaScript)**
    *   Displays the modern User Interface.
    *   Collects user inputs (Bitrate, Resolution, etc.).
    *   Visualizes logs and device status.

2.  **Backend (`App.py` / `scrcpy_wrapper.py`)**
    *   **Worker Process:** Runs scrcpy in a separate thread/process to prevent UI freezing.
    *   **IPC (Inter-Process Communication):** Streams console logs from scrcpy back to the HTML frontend in real-time.
    *   **Logic:** Handles device scanning and flag sanitization.

**GUIPy = The power of Python automation + The beauty of Web technologies.**