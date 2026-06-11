"""Engraver Camera Assistant — Standalone GUI Application.

Captures frames from your real USB webcam, runs recognition overlays,
and displays the annotated feed in a tkinter window with physical buttons.

Usage:
    python main.py
"""

import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk

import config
import recognition
import wood_database

APP_TITLE = "Engraver Camera Assistant"
SNAPSHOT_PREFIX = "engraver_snapshot"
MAX_CAMERA_CHECK = 10
SWITCH_SPLASH_FRAMES = 45  # ~1.5s at 30fps


def draw_camera_indicator(frame: np.ndarray, camera_index: int, switch_timer: int):
    """Draw the active camera index and a brief switch splash on the frame."""
    h, w = frame.shape[:2]

    # Persistent small label in bottom-right corner
    label = f"CAM [{camera_index}]"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    pad = 8
    x1, y1 = w - tw - pad * 2, h - th - pad * 2
    x2, y2 = w - pad, h - pad
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.putText(frame, label, (x1 + pad, y2 - pad), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

    # Brief "SWITCHING" splash in center
    if switch_timer > 0:
        splash = f"SWITCHING TO CAMERA [{camera_index}]"
        (sw, sh), _ = cv2.getTextSize(splash, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        cx, cy = (w - sw) // 2, (h + sh) // 2
        cv2.rectangle(frame, (cx - 20, cy - sh - 20), (cx + sw + 20, cy + 20), (0, 0, 0), -1)
        cv2.putText(frame, splash, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA)

    return frame


def enumerate_cameras() -> dict[int, tuple[int, int]]:
    """Probe indices 0..MAX_CAMERA_CHECK-1 and return a dict of
    index -> (width, height) for working cameras."""
    found = {}
    for i in range(MAX_CAMERA_CHECK):
        cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            found[i] = (w, h)
        cap.release()
    return found


def test_resolutions(index: int) -> list[tuple[int, int]]:
    """Probe a camera with common resolutions and return which ones it accepts."""
    common = [
        (320, 240), (640, 480), (800, 600),
        (1280, 720), (1920, 1080), (1600, 1200),
    ]
    supported = []
    for w, h in common:
        cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
        if not cap.isOpened():
            cap.release()
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        # Give the driver a moment to apply the setting
        time.sleep(0.15)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if actual_w == w and actual_h == h:
            supported.append((w, h))
    return supported


def open_camera(index: int, width: int | None = None, height: int | None = None):
    """Open a camera by index with optional resolution.

    Forces MJPEG pixel format, which most USB webcams use internally.
    Without this, some cameras produce unreadable or black frames.
    """
    cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
    if not cap.isOpened():
        return cap

    # Try YUY2 format first (uncompressed, common on USB webcams)
    yuy2_fourcc = cv2.VideoWriter_fourcc('Y', 'U', 'Y', '2')
    cap.set(cv2.CAP_PROP_FOURCC, yuy2_fourcc)

    if width and height:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Log what the driver actually settled on
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join([chr((actual_fourcc >> (8 * i)) & 0xFF) for i in range(4)])
    print(f"[DEBUG] Camera [{index}] opened: {actual_w}x{actual_h}, FOURCC={fourcc_str}")

    return cap


class DualStream:
    """Redirects stdout/stderr to both the original console and a tkinter text widget."""

    def __init__(self, text_widget: tk.Text, original_stream):
        self.text_widget = text_widget
        self.original_stream = original_stream

    def write(self, message: str):
        self.original_stream.write(message)
        # Schedule GUI update on main thread
        def _append():
            self.text_widget.insert(tk.END, message)
            self.text_widget.see(tk.END)
        try:
            self.text_widget.after_idle(_append)
        except Exception:
            pass

    def flush(self):
        self.original_stream.flush()


class CameraApp:
    def __init__(self, root: tk.Tk, cameras: dict):
        self.root = root
        self.root.title(APP_TITLE)
        self.cameras = cameras
        self.current_index = config.REAL_CAMERA_INDEX if config.REAL_CAMERA_INDEX in cameras else next(iter(cameras))

        # Skip startup resolution probing — rapid open/close cycles can lock USB webcams.
        # We'll use the camera's native resolution and resize in the main loop.
        self.camera_resolutions: dict[int, list[tuple[int, int]]] = {}
        self.selected_resolution = tk.StringVar(value="Auto")

        self.cap = open_camera(self.current_index)
        self.show_overlay = tk.BooleanVar(value=config.SHOW_OVERLAY)
        self.snapshot_counter = 0
        self.switch_timer = 0
        self._running = True

        self._build_ui()
        self._read_camera_settings()
        self._redirect_streams()
        self._update_frame()

    def _get_current_resolution(self) -> tuple[int | None, int | None]:
        val = self.selected_resolution.get()
        if not val or val == "Auto":
            return (None, None)
        w, h = val.split("x")
        return (int(w), int(h))

    def _build_ui(self):
        # Video label
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(padx=5, pady=5)

        # Wood info panel (outside video — never blocks the feed)
        info = ttk.LabelFrame(self.root, text="Wood Identification")
        info.pack(padx=5, pady=(0, 5), fill=tk.X)

        self.info_wood = ttk.Label(info, text="Scanning...", font=("Consolas", 11, "bold"))
        self.info_wood.pack(anchor=tk.W, padx=5, pady=2)

        self.info_settings = ttk.Label(info, text="Settings: --", font=("Consolas", 10))
        self.info_settings.pack(anchor=tk.W, padx=5, pady=1)

        self.info_grain = ttk.Label(info, text="Grain: --", font=("Consolas", 10))
        self.info_grain.pack(anchor=tk.W, padx=5, pady=1)

        # Control frame
        ctrl = ttk.Frame(self.root)
        ctrl.pack(padx=5, pady=5, fill=tk.X)

        # Camera switch buttons
        ttk.Label(ctrl, text="Camera:").pack(side=tk.LEFT, padx=(0, 5))
        self.cam_buttons = {}
        for idx in sorted(self.cameras):
            btn = ttk.Button(ctrl, text=f"Camera {idx}", command=lambda i=idx: self._switch_camera(i))
            btn.pack(side=tk.LEFT, padx=2)
            self.cam_buttons[idx] = btn
        self._highlight_active_camera()

        # Resolution dropdown
        ttk.Label(ctrl, text="Resolution:").pack(side=tk.LEFT, padx=(10, 2))
        self.res_combo = ttk.Combobox(
            ctrl,
            textvariable=self.selected_resolution,
            values=[],
            width=12,
            state="readonly",
        )
        self.res_combo.pack(side=tk.LEFT, padx=2)
        self.res_combo.bind("<<ComboboxSelected>>", self._on_resolution_change)
        self._update_resolution_dropdown(self.current_index)

        # Wattage dropdown
        ttk.Label(ctrl, text="Laser W:").pack(side=tk.LEFT, padx=(10, 2))
        self.wattage_var = tk.StringVar(value="10")
        wattage_combo = ttk.Combobox(
            ctrl,
            textvariable=self.wattage_var,
            values=["5", "10", "20", "40", "60", "80"],
            width=6,
            state="readonly",
        )
        wattage_combo.pack(side=tk.LEFT, padx=2)
        wattage_combo.bind("<<ComboboxSelected>>", self._on_wattage_change)

        # Thickness input
        ttk.Label(ctrl, text="Thickness (mm):").pack(side=tk.LEFT, padx=(10, 2))
        self.thickness_var = tk.StringVar(value="3")
        thickness_entry = ttk.Entry(ctrl, textvariable=self.thickness_var, width=5)
        thickness_entry.pack(side=tk.LEFT, padx=2)
        thickness_entry.bind("<Return>", self._on_thickness_change)
        thickness_entry.bind("<FocusOut>", self._on_thickness_change)

        # Engraving mode dropdown
        ttk.Label(ctrl, text="Mode:").pack(side=tk.LEFT, padx=(10, 2))
        self.mode_var = tk.StringVar(value="Surface")
        mode_combo = ttk.Combobox(
            ctrl,
            textvariable=self.mode_var,
            values=["Surface", "Deep", "Cut"],
            width=8,
            state="readonly",
        )
        mode_combo.pack(side=tk.LEFT, padx=2)
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Spacer
        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Overlay toggle
        ttk.Checkbutton(ctrl, text="Overlay", variable=self.show_overlay,
                        command=self._on_overlay_toggle).pack(side=tk.LEFT, padx=2)

        # Snapshot button
        ttk.Button(ctrl, text="Snapshot", command=self._take_snapshot).pack(side=tk.LEFT, padx=2)

        # Quit button
        ttk.Button(ctrl, text="Quit", command=self._quit).pack(side=tk.RIGHT, padx=2)

        # Camera settings frame
        settings = ttk.LabelFrame(self.root, text="Camera Settings")
        settings.pack(padx=5, pady=5, fill=tk.X)

        # Brightness slider
        ttk.Label(settings, text="Brightness:").pack(side=tk.LEFT, padx=(5, 2))
        self.brightness_var = tk.IntVar(value=0)
        self.brightness_scale = tk.Scale(
            settings, from_=-64, to=64, orient=tk.HORIZONTAL,
            variable=self.brightness_var, length=150,
            command=self._on_brightness_change,
        )
        self.brightness_scale.pack(side=tk.LEFT, padx=2)

        # Contrast slider
        ttk.Label(settings, text="Contrast:").pack(side=tk.LEFT, padx=(10, 2))
        self.contrast_var = tk.IntVar(value=32)
        self.contrast_scale = tk.Scale(
            settings, from_=0, to=64, orient=tk.HORIZONTAL,
            variable=self.contrast_var, length=150,
            command=self._on_contrast_change,
        )
        self.contrast_scale.pack(side=tk.LEFT, padx=2)

        # Exposure slider
        ttk.Label(settings, text="Exposure:").pack(side=tk.LEFT, padx=(10, 2))
        self.exposure_var = tk.IntVar(value=-6)
        self.exposure_scale = tk.Scale(
            settings, from_=-11, to=-1, orient=tk.HORIZONTAL,
            variable=self.exposure_var, length=150,
            command=self._on_exposure_change,
        )
        self.exposure_scale.pack(side=tk.LEFT, padx=2)

        # Auto button
        ttk.Button(settings, text="Auto", command=self._auto_settings).pack(side=tk.LEFT, padx=(15, 2))

        # Status bar
        self.status = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Debug / Log panel
        self.log_frame = ttk.LabelFrame(self.root, text="Debug Log")
        self.log_frame.pack(padx=5, pady=(0, 5), fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.NORMAL,
            font=("Consolas", 9),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # Set initial size
        self.root.geometry(f"{config.VIRTUAL_CAMERA_WIDTH + 20}x{config.VIRTUAL_CAMERA_HEIGHT + 420}")

    def _redirect_streams(self):
        """Redirect stdout and stderr to the debug log panel."""
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = DualStream(self.log_text, self._orig_stdout)
        sys.stderr = DualStream(self.log_text, self._orig_stderr)

    def _highlight_active_camera(self):
        for idx, btn in self.cam_buttons.items():
            if idx == self.current_index:
                btn.configure(text=f"Camera {idx} ●")
            else:
                btn.configure(text=f"Camera {idx}")

    def _update_resolution_dropdown(self, index: int):
        # Static common resolutions — user can try any of them
        common = ["Auto", "320x240", "640x480", "800x600", "1280x720", "1920x1080"]
        self.res_combo.configure(values=common)
        self.selected_resolution.set("Auto")

    def _on_resolution_change(self, event=None):
        # Reopen current camera with new resolution
        self.status.configure(text="Applying resolution...")
        self.cap.release()
        self._diag_counter = 0
        w, h = self._get_current_resolution()
        self.cap = open_camera(self.current_index, w, h)
        self._read_camera_settings()
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.status.configure(text=f"Resolution: {actual_w}x{actual_h}")

    def _switch_camera(self, new_idx: int):
        if new_idx == self.current_index:
            return
        self.status.configure(text=f"Switching to Camera {new_idx}...")
        self.root.update_idletasks()

        def _do_switch():
            self.cap.release()
            self._diag_counter = 0
            new_cap = open_camera(new_idx)
            if new_cap.isOpened():
                self.current_index = new_idx
                self.cap = new_cap
                self.switch_timer = SWITCH_SPLASH_FRAMES
                self._read_camera_settings()
                actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                # Schedule UI updates on main thread
                self.root.after_idle(lambda: self.status.configure(
                    text=f"Switched to Camera {new_idx} @ {actual_w}x{actual_h}"
                ))
                self.root.after_idle(self._highlight_active_camera)
                print(f"[INFO] Switched to camera [{new_idx}] @ {actual_w}x{actual_h}")
            else:
                self.root.after_idle(lambda: self.status.configure(
                    text=f"Failed to open Camera {new_idx}, reverting..."
                ))
                print(f"[ERROR] Failed to open Camera [{new_idx}], reverting to [{self.current_index}]")
                self._diag_counter = 0
                self.cap = open_camera(self.current_index)

        threading.Thread(target=_do_switch, daemon=True).start()

    def _on_overlay_toggle(self):
        state = "ON" if self.show_overlay.get() else "OFF"
        self.status.configure(text=f"Overlay {state}")

    def _on_wattage_change(self, event=None):
        wattage = int(self.wattage_var.get())
        self.status.configure(text=f"Laser: {wattage}W")
        # Force wood re-identification on next frame with new wattage
        recognition._wood_cache["last_update"] = 0

    def _on_thickness_change(self, event=None):
        try:
            t = float(self.thickness_var.get())
            self.status.configure(text=f"Thickness: {t}mm")
            # Force wood info refresh to update pass estimate
            recognition._wood_cache["last_update"] = 0
        except ValueError:
            self.status.configure(text="Invalid thickness")

    def _on_mode_change(self, event=None):
        mode = self.mode_var.get()
        self.status.configure(text=f"Mode: {mode}")
        # Force wood info refresh to show/hide passes
        recognition._wood_cache["last_update"] = 0

    def _update_wood_info(self):
        """Sync the tkinter wood info panel with the recognition cache."""
        cache = recognition._wood_cache
        name = cache["name"]
        conf = cache["confidence"]
        settings = cache["settings"]
        grain = cache["grain_angle"]

        self.info_wood.configure(text=f"{name}  ({int(conf * 100)}% confidence)")

        mode = self.mode_var.get()
        thickness = self._get_thickness()
        
        if mode == "Cut":
            cut_settings = wood_database.get_cut_settings(name, int(self.wattage_var.get()))
            if cut_settings:
                speed, power = cut_settings
                passes = self._estimate_cut_passes(name, thickness)
                self.info_settings.configure(
                    text=f"Speed: {speed} mm/min  |  Power: {power}%  |  Passes: {passes}"
                )
            else:
                self.info_settings.configure(text="Cut settings: --")
        elif settings:
            speed, power = settings
            if mode == "Deep":
                passes = self._estimate_passes(name, thickness)
                self.info_settings.configure(
                    text=f"Speed: {speed} mm/min  |  Power: {power}%  |  Passes: {passes}"
                )
            else:  # Surface mode
                self.info_settings.configure(
                    text=f"Speed: {speed} mm/min  |  Power: {power}%  |  Passes: 1"
                )
        else:
            self.info_settings.configure(text="Settings: --")

        if grain is not None:
            self.info_grain.configure(text=f"Grain direction: {grain:.0f}")
        else:
            self.info_grain.configure(text="Grain direction: --")

    def _get_thickness(self) -> float:
        try:
            return max(0.5, float(self.thickness_var.get()))
        except ValueError:
            return 3.0

    def _estimate_passes(self, wood_name: str, thickness_mm: float) -> int:
        """Estimate passes for deep engraving based on wood density and laser power.
        
        Values based on real-world depth per pass data:
        - Softwoods (basswood, pine): 0.3-0.5mm per pass at standard settings
        - Medium hardwoods (oak, maple): 0.2-0.35mm per pass
        - Dense hardwoods (walnut, ebony): 0.15-0.25mm per pass
        - Engineered materials (plywood, MDF): 0.2-0.3mm per pass
        - Non-wood (leather, cork): 0.4-0.6mm per pass
        """
        # Depth per pass in mm (for deep engraving - removes more than cutting)
        depth_per_pass = {
            # Softwoods
            "Basswood": 1.0, "Pine": 0.9, "Poplar": 0.9, "Cedar": 0.9,
            "Bamboo": 0.8, "Cork": 1.2,
            # Medium hardwoods
            "Oak": 0.6, "Maple": 0.6, "Birch": 0.7, "Cherry": 0.6,
            "Alder": 0.7, "Mahogany": 0.6,
            # Dense hardwoods
            "Walnut": 0.5, "Padauk": 0.5, "Purpleheart": 0.45,
            "Wenge": 0.45, "Ebony": 0.45,
            # Engineered materials
            "Plywood": 0.6, "MDF / HDF": 0.55,
            # Non-wood
            "Leather": 1.1,
        }
        mm_per_pass = depth_per_pass.get(wood_name, 0.25)
        passes = max(1, int(thickness_mm / mm_per_pass + 0.5))
        # Cap at reasonable maximum to avoid endless passes
        return min(passes, 10)

    def _estimate_cut_passes(self, wood_name: str, thickness_mm: float) -> int:
        """Estimate passes needed to cut through material.
        
        Based on typical kerf depth per pass for cutting:
        - Softwoods: 0.6-0.8mm per pass
        - Medium hardwoods: 0.4-0.6mm per pass
        - Dense hardwoods: 0.3-0.4mm per pass
        - Engineered materials: 0.4-0.5mm per pass
        """
        # Kerf depth per pass in mm
        kerf_per_pass = {
            # Softwoods
            "Basswood": 0.7, "Pine": 0.6, "Poplar": 0.6, "Cedar": 0.6,
            "Bamboo": 0.5, "Cork": 0.8,
            # Medium hardwoods
            "Oak": 0.45, "Maple": 0.45, "Birch": 0.5, "Cherry": 0.45,
            "Alder": 0.5, "Mahogany": 0.45,
            # Dense hardwoods
            "Walnut": 0.35, "Padauk": 0.35, "Purpleheart": 0.3,
            "Wenge": 0.3, "Ebony": 0.3,
            # Engineered materials
            "Plywood": 0.4, "MDF / HDF": 0.45,
            # Non-wood
            "Leather": 0.8,
        }
        mm_per_pass = kerf_per_pass.get(wood_name, 0.4)
        passes = max(1, int(thickness_mm / mm_per_pass + 0.5))
        # Cap at reasonable maximum for cutting
        return min(passes, 8)

    def _on_brightness_change(self, val):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, int(float(val)))

    def _on_contrast_change(self, val):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_CONTRAST, int(float(val)))

    def _on_exposure_change(self, val):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_EXPOSURE, int(float(val)))

    def _auto_settings(self):
        """Auto-adjust camera settings for optimal picture."""
        if not self.cap.isOpened():
            return
        self.status.configure(text="Auto-tuning...")

        def _tune():
            target = 128.0
            # Sample current brightness
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.root.after_idle(lambda: self.status.configure(text="Auto-tune failed: no frame"))
                return
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            current = gray.mean()
            print(f"[INFO] Auto-tune start brightness={current:.1f}")

            # Quick binary search on exposure to get close to target
            best_exp = int(self.exposure_var.get())
            best_delta = abs(current - target)
            for exp in range(-11, 0):
                self.cap.set(cv2.CAP_PROP_EXPOSURE, exp)
                time.sleep(0.2)
                ret, frame = self.cap.read()
                if not ret:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = gray.mean()
                delta = abs(brightness - target)
                print(f"[DEBUG] Auto-tune exp={exp} brightness={brightness:.1f} delta={delta:.1f}")
                if delta < best_delta:
                    best_delta = delta
                    best_exp = exp

            # Apply best exposure
            self.cap.set(cv2.CAP_PROP_EXPOSURE, best_exp)
            time.sleep(0.1)

            # Update slider UI
            self.root.after_idle(lambda: self.exposure_var.set(best_exp))
            self.root.after_idle(lambda: self.status.configure(
                text=f"Auto-tuned: exposure={best_exp}"
            ))
            print(f"[INFO] Auto-tuned: exposure={best_exp}")

        threading.Thread(target=_tune, daemon=True).start()

    def _read_camera_settings(self):
        """Sync slider values with the current camera's actual settings."""
        if not self.cap.isOpened():
            return
        try:
            b = int(self.cap.get(cv2.CAP_PROP_BRIGHTNESS))
            c = int(self.cap.get(cv2.CAP_PROP_CONTRAST))
            e = int(self.cap.get(cv2.CAP_PROP_EXPOSURE))
            self.brightness_var.set(b)
            self.contrast_var.set(c)
            self.exposure_var.set(e)
        except Exception:
            pass

    def _take_snapshot(self):
        filename = f"{SNAPSHOT_PREFIX}_{self.snapshot_counter:03d}.png"
        # Snapshot will be saved from the next rendered frame via _update_frame
        self._pending_snapshot = filename
        self.status.configure(text=f"Snapshot: {filename}")
        self.snapshot_counter += 1

    def _quit(self):
        self._running = False
        self.cap.release()
        # Restore original streams
        if hasattr(self, "_orig_stdout"):
            sys.stdout = self._orig_stdout
        if hasattr(self, "_orig_stderr"):
            sys.stderr = self._orig_stderr
        self.root.destroy()

    def _update_frame(self):
        if not self._running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(10, self._update_frame)
            return

        # First-frame diagnostics after a camera switch
        diag_count = getattr(self, "_diag_counter", 0)
        if diag_count < 10:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = gray.mean()
            print(f"[DEBUG] Frame {diag_count}: shape={frame.shape}, brightness={brightness:.1f}")
            self._diag_counter = diag_count + 1

        if frame.shape[1] != config.VIRTUAL_CAMERA_WIDTH or frame.shape[0] != config.VIRTUAL_CAMERA_HEIGHT:
            frame = cv2.resize(frame, (config.VIRTUAL_CAMERA_WIDTH, config.VIRTUAL_CAMERA_HEIGHT))

        if self.show_overlay.get():
            wattage = int(self.wattage_var.get())
            frame = recognition.process_frame(frame, config.OVERLAY_TEXT, wattage=wattage)

        # Update tkinter wood info panel from recognition cache
        self._update_wood_info()

        frame = draw_camera_indicator(frame, self.current_index, self.switch_timer)
        if self.switch_timer > 0:
            self.switch_timer -= 1

        # Handle pending snapshot
        if hasattr(self, "_pending_snapshot"):
            cv2.imwrite(self._pending_snapshot, frame)
            del self._pending_snapshot

        # Convert to tkinter image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk  # keep reference
        self.video_label.configure(image=imgtk)

        self.root.after(15, self._update_frame)  # ~60fps target


def main():
    cameras = enumerate_cameras()
    if not cameras:
        print("[ERROR] No USB cameras detected.")
        sys.exit(1)

    print("[INFO] Detected cameras:")
    for idx, (w, h) in cameras.items():
        marker = "  <-- default" if idx == config.REAL_CAMERA_INDEX else ""
        print(f"    [{idx}] {w}x{h}{marker}")

    root = tk.Tk()
    app = CameraApp(root, cameras)
    root.mainloop()
    print("[INFO] Shutdown complete.")


if __name__ == "__main__":
    main()
