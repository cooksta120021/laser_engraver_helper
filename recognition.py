"""Recognition and overlay module for the camera feed.

Provides wood identification and laser engraving settings overlay.
"""

import cv2
import numpy as np
import time

import wood_database

# Simple motion detector state
_motion_detector_state = {
    "last_frame": None,
    "last_time": 0,
}

# Cache wood identification to avoid flickering every frame
_wood_cache = {
    "name": "Scanning...",
    "confidence": 0.0,
    "settings": None,
    "grain_angle": None,
    "last_update": 0,
}

_SAMPLE_INTERVAL = 1.0  # seconds between wood re-identification


def _draw_rounded_rect(img, x1, y1, x2, y2, color, thickness, radius=8):
    """Draw a rectangle with rounded corners."""
    cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
    cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
    cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)


def _draw_panel(img, x1, y1, x2, y2, alpha=0.7):
    """Draw a semi-transparent dark panel."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
    return cv2.addWeighted(img, 1 - alpha, overlay, alpha, 0)


def process_frame(
    frame: np.ndarray,
    overlay_text: str = "Engraver Assistant",
    wattage: int = 10,
    enable_wood_id: bool = True,
) -> np.ndarray:
    """Process a single frame and apply recognition overlays.

    Args:
        frame: Input BGR image from the camera.
        overlay_text: Header text to display.
        wattage: Diode laser wattage for settings lookup.
        enable_wood_id: Whether to run wood identification.

    Returns:
        Annotated BGR image.
    """
    output = frame.copy()
    h, w = output.shape[:2]

    # --- Wood identification (runs periodically) ---
    roi = None
    if enable_wood_id:
        h, w = frame.shape[:2]
        y1 = int(h * 0.35)
        y2 = int(h * 0.65)
        x1 = int(w * 0.35)
        x2 = int(w * 0.65)
        roi = frame[y1:y2, x1:x2]

        now = time.time()
        if now - _wood_cache["last_update"] > _SAMPLE_INTERVAL:
            _wood_cache["last_update"] = now
            patches = wood_database._sample_patches_lab(frame)
            name, conf = wood_database.identify_wood(patches)
            _wood_cache["name"] = name
            _wood_cache["confidence"] = conf
            settings = wood_database.get_settings(name, wattage)
            _wood_cache["settings"] = settings
            # Grain direction
            grain = wood_database.detect_grain_direction(roi)
            _wood_cache["grain_angle"] = grain
            print(f"[WOOD] Identified: {name} (conf={conf:.2f}), patches={len(patches)}, grain={grain}")

    # --- Header bar ---
    cv2.rectangle(output, (0, 0), (w, 42), (0, 0, 0), -1)
    cv2.putText(
        output,
        overlay_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    # --- Grain direction arrow (center of frame) ---
    if enable_wood_id:
        grain = _wood_cache["grain_angle"]
        if grain is not None and roi is not None:
            cx = w // 2
            cy = h // 2
            angle_rad = np.radians(grain)
            arrow_len = 40
            x_end = int(cx + arrow_len * np.cos(angle_rad))
            y_end = int(cy + arrow_len * np.sin(angle_rad))

            # Good if aligned with bed axes (0, 90, 180) ±15°
            # Bad if diagonal — laser scan may create artifacts
            aligned = any(
                abs((grain - ref) % 180) <= 15 or abs((grain - ref) % 180) >= 165
                for ref in (0, 90)
            )
            arrow_color = (0, 255, 0) if aligned else (0, 0, 255)  # green or red
            cv2.arrowedLine(output, (cx, cy), (x_end, y_end),
                            arrow_color, 2, tipLength=0.3)

    # --- Grid overlay for alignment ---
    grid_color = (0, 255, 255)
    grid_alpha = 0.25
    grid_step = 100
    overlay_grid = output.copy()
    for x in range(0, w, grid_step):
        cv2.line(overlay_grid, (x, 0), (x, h), grid_color, 1)
    for y in range(0, h, grid_step):
        cv2.line(overlay_grid, (0, y), (w, y), grid_color, 1)
    output = cv2.addWeighted(output, 1 - grid_alpha, overlay_grid, grid_alpha, 0)

    # --- Center crosshair ---
    cx, cy = w // 2, h // 2
    cv2.drawMarker(output, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 50, 2)
    # Sample region indicator (center 30%)
    cv2.rectangle(output, (int(w * 0.35), int(h * 0.35)),
                  (int(w * 0.65), int(h * 0.65)), (0, 255, 0), 1)

    # FPS counter
    _motion_detector_state["last_time"] = time.time()

    return output


def _detect_motion(frame: np.ndarray) -> np.ndarray | None:
    """Simple background-subtraction motion detector."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    last = _motion_detector_state["last_frame"]
    _motion_detector_state["last_frame"] = gray.copy()

    if last is None or last.shape != gray.shape:
        return None

    delta = cv2.absdiff(last, gray)
    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    overlay = np.zeros_like(frame)
    for cnt in contours:
        if cv2.contourArea(cnt) < 500:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
        cv2.putText(overlay, "MOTION", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

    return overlay if np.any(overlay) else None
