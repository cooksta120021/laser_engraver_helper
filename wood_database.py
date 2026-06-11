"""Wood identification database and laser engraving settings.

Color signatures are stored as mean LAB values (L 0-255, A -128-127, B -128-127).
LAB separates lightness from color, making matching robust to poor lighting.
Laser settings are tuples of (speed_mm_min, power_percent).
"""

from __future__ import annotations

import math

import cv2
import numpy as np

# -----------------------------------------------------------------------------
# Wood color signatures (mean LAB — lighting-independent color info)
# L = lightness (0-255), A = green-red, B = blue-yellow
# Only A and B are used for matching; L provides context.
# -----------------------------------------------------------------------------

WOOD_SIGNATURES: dict[str, tuple[float, float, float]] = {
    "Pine":        (185.0,   8.0,  55.0),   # pale yellow
    "Oak":         (150.0,  12.0,  42.0),   # light tan/brown
    "Maple":       (200.0,   5.0,  25.0),   # very pale, almost white
    "Walnut":      ( 65.0,  10.0,  30.0),   # dark chocolate brown
    "Cherry":      (110.0,  25.0,  35.0),   # reddish brown
    "Birch":       (180.0,   6.0,  40.0),   # pale yellowish
    "Mahogany":    ( 85.0,  28.0,  25.0),   # deep reddish
    "Bamboo":      (175.0,   9.0,  48.0),   # light yellow/tan
    "Poplar":      (170.0,  -5.0,  30.0),   # pale greenish tint
    "MDF / HDF":   (135.0,   8.0,  30.0),   # uniform medium brown
    "Plywood":     (145.0,  10.0,  35.0),   # layered tan
    "Basswood":    (205.0,   4.0,  22.0),   # very pale, soft
    "Alder":       (130.0,  15.0,  32.0),   # light reddish brown
    "Cedar":       (115.0,  18.0,  28.0),   # pinkish brown
    "Padauk":      ( 95.0,  45.0,  48.0),   # vivid orange-red
    "Purpleheart": ( 55.0,  35.0, -10.0),   # deep purple-brown
    "Wenge":       ( 40.0,   8.0,  18.0),   # very dark brown
    "Ebony":       ( 25.0,   3.0,   8.0),   # near-black
    "Cork":        (160.0,   7.0,  38.0),   # mottled tan
    "Leather":     (105.0,  12.0,  28.0),   # medium brown
}

# -----------------------------------------------------------------------------
# Laser engraving settings per wattage
# Based on real-world data from Tyvok, Craftgineer, and community sources
# Speeds in mm/min, power as percentage
# -----------------------------------------------------------------------------

WOOD_SETTINGS: dict[str, dict[int, tuple[int, int]]] = {
    # Softwoods (engrave faster, less power)
    "Pine": {
        5:  ( 1500, 80),  10: ( 3000, 60),  20: ( 4500, 50),
        40: ( 6000, 45),  60: ( 7500, 40),  80: ( 9000, 35),
    },
    "Basswood": {
        5:  ( 1800, 80),  10: ( 3600, 60),  20: ( 5400, 50),
        40: ( 7200, 45),  60: ( 9000, 40),  80: (10800, 35),
    },
    "Poplar": {
        5:  ( 1650, 80),  10: ( 3300, 60),  20: ( 4950, 50),
        40: ( 6600, 45),  60: ( 8250, 40),  80: ( 9900, 35),
    },
    "Bamboo": {
        5:  ( 1200, 75),  10: ( 2400, 55),  20: ( 3600, 45),
        40: ( 4800, 40),  60: ( 6000, 35),  80: ( 7200, 30),
    },
    "Cedar": {
        5:  ( 1500, 80),  10: ( 3000, 60),  20: ( 4500, 50),
        40: ( 6000, 45),  60: ( 7500, 40),  80: ( 9000, 35),
    },
    "Cork": {
        5:  ( 3000, 50),  10: ( 6000, 35),  20: ( 9000, 25),
        40: (12000, 20),  60: (15000, 18),  80: (18000, 15),
    },

    # Medium hardwoods (slower, more power)
    "Oak": {
        5:  ( 1000, 90),  10: ( 2000, 75),  20: ( 3000, 65),
        40: ( 4000, 60),  60: ( 5000, 55),  80: ( 6000, 50),
    },
    "Maple": {
        5:  ( 1000, 90),  10: ( 2000, 75),  20: ( 3000, 65),
        40: ( 4000, 60),  60: ( 5000, 55),  80: ( 6000, 50),
    },
    "Birch": {
        5:  ( 1200, 85),  10: ( 2400, 70),  20: ( 3600, 60),
        40: ( 4800, 55),  60: ( 6000, 50),  80: ( 7200, 45),
    },
    "Cherry": {
        5:  ( 1200, 85),  10: ( 2400, 70),  20: ( 3600, 60),
        40: ( 4800, 55),  60: ( 6000, 50),  80: ( 7200, 45),
    },
    "Alder": {
        5:  ( 1350, 85),  10: ( 2700, 70),  20: ( 4050, 60),
        40: ( 5400, 55),  60: ( 6750, 50),  80: ( 8100, 45),
    },
    "Mahogany": {
        5:  ( 1200, 85),  10: ( 2400, 70),  20: ( 3600, 60),
        40: ( 4800, 55),  60: ( 6000, 50),  80: ( 7200, 45),
    },

    # Dense hardwoods (slowest, highest power)
    "Walnut": {
        5:  (  800, 95),  10: ( 1600, 85),  20: ( 2400, 75),
        40: ( 3200, 70),  60: ( 4000, 65),  80: ( 4800, 60),
    },
    "Padauk": {
        5:  (  900, 95),  10: ( 1800, 85),  20: ( 2700, 75),
        40: ( 3600, 70),  60: ( 4500, 65),  80: ( 5400, 60),
    },
    "Purpleheart": {
        5:  (  900, 95),  10: ( 1800, 85),  20: ( 2700, 75),
        40: ( 3600, 70),  60: ( 4500, 65),  80: ( 5400, 60),
    },
    "Wenge": {
        5:  (  750, 95),  10: ( 1500, 90),  20: ( 2250, 80),
        40: ( 3000, 75),  60: ( 3750, 70),  80: ( 4500, 65),
    },
    "Ebony": {
        5:  (  750, 95),  10: ( 1500, 90),  20: ( 2250, 80),
        40: ( 3000, 75),  60: ( 3750, 70),  80: ( 4500, 65),
    },

    # Engineered materials
    "Plywood": {
        5:  ( 1200, 85),  10: ( 2400, 70),  20: ( 3600, 60),
        40: ( 4800, 55),  60: ( 6000, 50),  80: ( 7200, 45),
    },
    "MDF / HDF": {
        5:  (  900, 90),  10: ( 1800, 80),  20: ( 2700, 70),
        40: ( 3600, 65),  60: ( 4500, 60),  80: ( 5400, 55),
    },

    # Non-wood
    "Leather": {
        5:  ( 3000, 60),  10: ( 6000, 45),  20: ( 9000, 35),
        40: (12000, 30),  60: (15000, 25),  80: (18000, 20),
    },
}

# -----------------------------------------------------------------------------
# Cutting settings per wattage (for through-cutting)
# Speeds in mm/min, power as percentage
# These are for cutting through, not engraving
# -----------------------------------------------------------------------------

CUT_SETTINGS: dict[str, dict[int, tuple[int, int]]] = {
    # Softwoods (easiest to cut)
    "Pine": {
        5:  ( 600, 100),  10: ( 1200, 100),  20: ( 1800, 100),
        40: ( 3000, 100),  60: ( 4500, 100),  80: ( 6000, 100),
    },
    "Basswood": {
        5:  ( 600, 100),  10: ( 1200, 100),  20: ( 1800, 100),
        40: ( 3000, 100),  60: ( 4500, 100),  80: ( 6000, 100),
    },
    "Poplar": {
        5:  ( 600, 100),  10: ( 1200, 100),  20: ( 1800, 100),
        40: ( 3000, 100),  60: ( 4500, 100),  80: ( 6000, 100),
    },
    "Bamboo": {
        5:  ( 450, 100),  10: (  900, 100),  20: ( 1500, 100),
        40: ( 2400, 100),  60: ( 3600, 100),  80: ( 4800, 100),
    },
    "Cedar": {
        5:  ( 450, 100),  10: (  900, 100),  20: ( 1500, 100),
        40: ( 2400, 100),  60: ( 3600, 100),  80: ( 4800, 100),
    },
    "Cork": {
        5:  ( 900,  80),  10: ( 1800,  60),  20: ( 2700,  50),
        40: ( 4500,  40),  60: ( 6000,  35),  80: ( 7500,  30),
    },

    # Medium hardwoods (moderate difficulty)
    "Oak": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "Maple": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "Birch": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "Cherry": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "Alder": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "Mahogany": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },

    # Dense hardwoods (hardest to cut)
    "Walnut": {
        5:  ( 150, 100),  10: (  300, 100),  20: (  450, 100),
        40: (  750, 100),  60: ( 1200, 100),  80: ( 1650, 100),
    },
    "Padauk": {
        5:  ( 150, 100),  10: (  300, 100),  20: (  450, 100),
        40: (  750, 100),  60: ( 1200, 100),  80: ( 1650, 100),
    },
    "Purpleheart": {
        5:  ( 150, 100),  10: (  300, 100),  20: (  450, 100),
        40: (  750, 100),  60: ( 1200, 100),  80: ( 1650, 100),
    },
    "Wenge": {
        5:  ( 150, 100),  10: (  300, 100),  20: (  450, 100),
        40: (  750, 100),  60: ( 1200, 100),  80: ( 1650, 100),
    },
    "Ebony": {
        5:  ( 150, 100),  10: (  300, 100),  20: (  450, 100),
        40: (  750, 100),  60: ( 1200, 100),  80: ( 1650, 100),
    },

    # Engineered materials
    "Plywood": {
        5:  ( 300, 100),  10: (  600, 100),  20: (  900, 100),
        40: ( 1500, 100),  60: ( 2400, 100),  80: ( 3300, 100),
    },
    "MDF / HDF": {
        5:  ( 450, 100),  10: (  900, 100),  20: ( 1350, 100),
        40: ( 2250, 100),  60: ( 3600, 100),  80: ( 4800, 100),
    },

    # Non-wood
    "Leather": {
        5:  ( 900,  80),  10: ( 1800,  60),  20: ( 2700,  50),
        40: ( 4500,  40),  60: ( 6000,  35),  80: ( 7500,  30),
    },
}

AVAILABLE_WATTAGES = [5, 10, 20, 40, 60, 80]


def _lab_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Distance in LAB space, weighted to favor A/B (color) over L (lightness)."""
    dl = abs(a[0] - b[0]) / 255.0 * 0.15
    da = abs(a[1] - b[1]) / 255.0
    db = abs(a[2] - b[2]) / 255.0
    return math.sqrt(dl ** 2 + da ** 2 + db ** 2)


def _best_match_for_patch(lab: tuple[float, float, float]) -> tuple[str, float]:
    """Find the single best wood match for one patch and its distance."""
    best_name = "Unknown"
    best_dist = float("inf")
    for name, sig in WOOD_SIGNATURES.items():
        dist = _lab_distance(lab, sig)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name, best_dist


def _sample_patches_lab(frame: np.ndarray, grid: int = 3) -> list[tuple[float, float, float]]:
    """Split the center 30% ROI into a grid x grid set of patches and return mean LAB per patch.

    Each patch is locally contrast-normalized so lighting changes affect all patches
    similarly rather than biasing the global mean.
    """
    h, w = frame.shape[:2]
    y1 = int(h * 0.35)
    y2 = int(h * 0.65)
    x1 = int(w * 0.35)
    x2 = int(w * 0.65)
    roi = frame[y1:y2, x1:x2]
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)

    ph, pw = lab.shape[:2]
    cell_h = ph // grid
    cell_w = pw // grid
    patches = []
    for row in range(grid):
        for col in range(grid):
            cy1 = row * cell_h
            cy2 = (row + 1) * cell_h if row < grid - 1 else ph
            cx1 = col * cell_w
            cx2 = (col + 1) * cell_w if col < grid - 1 else pw
            patch = lab[cy1:cy2, cx1:cx2]

            # Local contrast normalization: stretch L to full range per patch
            l_chan = patch[:, :, 0].astype(np.float32)
            l_min = l_chan.min()
            l_max = l_chan.max()
            if l_max > l_min:
                l_norm = (l_chan - l_min) / (l_max - l_min) * 255.0
            else:
                l_norm = l_chan
            mean_l = float(np.mean(l_norm))
            mean_a = float(np.mean(patch[:, :, 1])) - 128.0
            mean_b = float(np.mean(patch[:, :, 2])) - 128.0
            patches.append((mean_l, mean_a, mean_b))
    return patches


def identify_wood(patches: list[tuple[float, float, float]]) -> tuple[str, float]:
    """Identify wood type from multiple LAB patch samples.

    Uses vote counting across patches. If patches disagree, confidence drops.
    If they all agree but the color distance is still large, confidence also drops.

    Returns:
        (wood_name, confidence_score) where confidence is 0-1.
    """
    if not patches:
        return "Unknown", 0.0

    votes: dict[str, list[float]] = {}  # name -> list of distances
    for patch in patches:
        name, dist = _best_match_for_patch(patch)
        votes.setdefault(name, []).append(dist)

    # Winner by majority vote
    best_name = max(votes, key=lambda k: len(votes[k]))
    winner_votes = len(votes[best_name])
    total_votes = len(patches)
    agreement = winner_votes / total_votes

    # Average distance of winner's patches
    avg_dist = sum(votes[best_name]) / winner_votes

    # Combined confidence:
    #   agreement factor: all patches agree = 1.0, split evenly = 0.5
    #   distance factor: perfect match = 1.0, far match = 0.0
    # Thresholds tuned so that genuine matches with good agreement score ~0.8+
    # and questionable matches score <0.5
    distance_conf = max(0.0, 1.0 - avg_dist / 0.5)
    confidence = agreement * distance_conf

    # If confidence is very low, return Unknown
    if confidence < 0.15:
        return "Unknown", confidence
    return best_name, confidence


def detect_grain_direction(roi: np.ndarray) -> float | None:
    """Detect dominant grain direction in a grayscale ROI.

    Uses CLAHE for poor-lighting enhancement, Canny edges, and
    Hough line detection to find the dominant angle.

    Returns:
        Dominant angle in degrees (0-180), or None if no clear grain.
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # Adaptive histogram equalization for poor lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, 30, 90)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30,
                            minLineLength=30, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return None

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) < 1 and abs(dy) < 1:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        # Normalize to 0-180 (grain has 180° symmetry)
        angle = abs(angle) % 180
        angles.append(angle)

    if len(angles) < 3:
        return None

    # Histogram of angles to find dominant peak
    hist, bin_edges = np.histogram(angles, bins=18, range=(0, 180))
    dominant_bin = np.argmax(hist)
    return (bin_edges[dominant_bin] + bin_edges[dominant_bin + 1]) / 2.0


def get_settings(wood_name: str, wattage: int) -> tuple[int, int] | None:
    """Look up (speed_mm_min, power_percent) for a given wood and wattage.

    Returns None if no exact match exists.
    """
    if wood_name not in WOOD_SETTINGS:
        return None
    settings = WOOD_SETTINGS[wood_name]
    if wattage in settings:
        return settings[wattage]
    # Interpolate between nearest wattages
    watts = sorted(settings.keys())
    if wattage < watts[0] or wattage > watts[-1]:
        return None
    for i in range(len(watts) - 1):
        if watts[i] <= wattage <= watts[i + 1]:
            w1, w2 = watts[i], watts[i + 1]
            s1, p1 = settings[w1]
            s2, p2 = settings[w2]
            ratio = (wattage - w1) / (w2 - w1)
            speed = int(s1 + (s2 - s1) * ratio)
            power = int(p1 + (p2 - p1) * ratio)
            return speed, power
    return None
def get_cut_settings(wood_name: str, wattage: int) -> tuple[int, int] | None:
    """Look up cutting (speed_mm_min, power_percent) for through-cutting.

    Returns None if no exact match exists.
    """
    if wood_name not in CUT_SETTINGS:
        return None
    settings = CUT_SETTINGS[wood_name]
    if wattage in settings:
        return settings[wattage]
    # Interpolate between nearest wattages
    watts = sorted(settings.keys())
    if wattage < watts[0] or wattage > watts[-1]:
        return None
    for i in range(len(watts) - 1):
        if watts[i] <= wattage <= watts[i + 1]:
            w1, w2 = watts[i], watts[i + 1]
            s1, p1 = settings[w1]
            s2, p2 = settings[w2]
            ratio = (wattage - w1) / (w2 - w1)
            speed = int(s1 + (s2 - s1) * ratio)
            power = int(p1 + (p2 - p1) * ratio)
            return speed, power
    return None
