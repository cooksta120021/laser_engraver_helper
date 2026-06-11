# Engraver Camera Assistant

A standalone camera assistant that captures your real USB webcam, applies recognition overlays, and displays the annotated feed in its own resizable window alongside LightBurn.

## What It Does

This app opens its own window showing your camera feed with real-time overlays:

- **Motion detection** — highlights moving regions
- **Alignment grid** — positioning reference
- **Center crosshair** — precise targeting
- **Status bar** — shows active mode

You can run it alongside LightBurn on a second monitor or snapped to the side of your screen.

## Prerequisites

- **Python 3.9+**
- **Windows 10/11**
- **LightBurn 1.7.00** (optional — run alongside for engraving)

## Quick Start

1. **Install Python dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Run the app**
   ```powershell
   python main.py
   ```
   Or double-click `run.bat`.

3. **Use alongside LightBurn**
   - Position the app window next to LightBurn
   - The overlay helps with alignment, motion detection, and positioning
   - Press `s` to save a snapshot anytime

## What the Overlay Shows

The default `recognition.py` includes:

- **Status header bar** — shows "AI ASSISTANT ACTIVE"
- **Motion detection** — highlights moving regions in green
- **Alignment grid** — 100px grid for positioning
- **Center crosshair** — red cross at the center of the frame

## Customizing the Recognition

Open `recognition.py` and edit the `process_frame()` function. You can plug in:

- Your own OpenCV / ML models
- ArUco marker detection
- Object detection (YOLO, MediaPipe, etc.)
- Custom measurements or alignment guides
- Color masks for material detection

The function receives a BGR numpy array and must return an annotated BGR array.

## Configuration

Set environment variables before running, or edit `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `REAL_CAMERA_INDEX` | `0` | Which USB camera to capture from |
| `REAL_CAMERA_WIDTH` | `1280` | Capture width |
| `REAL_CAMERA_HEIGHT` | `720` | Capture height |
| `VIRTUAL_CAMERA_WIDTH` | `1280` | Output width (must match LightBurn settings) |
| `VIRTUAL_CAMERA_HEIGHT` | `720` | Output height |
| `OVERLAY_TEXT` | `AI ASSISTANT ACTIVE` | Header text on the overlay |
| `SHOW_OVERLAY` | `true` | Toggle overlays on/off |

Example:
```powershell
$env:REAL_CAMERA_INDEX="1"
python main.py
```

## Network Camera Fallback

If the virtual camera driver does not work on your system, use the MJPEG network proxy:

```powershell
python network_proxy.py
```

In LightBurn 2.1+, add a **Network** camera with the URL:  
`http://YOUR_PC_IP:8080/video.mjpg`

## Project Structure

```
engraver-wood-helper/
├── main.py           # Standalone window entry point
├── network_proxy.py  # HTTP MJPEG fallback server
├── recognition.py    # Your AI / overlay pipeline
├── config.py         # Settings
├── requirements.txt  # Python dependencies
├── run.bat           # One-click Windows launcher
└── README.md         # This file
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Window does not appear | Make sure OpenCV is installed (`pip install opencv-python`). |
| Preview window is black | Change `REAL_CAMERA_INDEX` to `1` (or try other indices) if you have multiple cameras. |
| Framerate is low | Lower `REAL_CAMERA_WIDTH` / `REAL_CAMERA_HEIGHT` in `config.py`. |

## License

MIT — modify and extend as needed for your engraving workflow.
