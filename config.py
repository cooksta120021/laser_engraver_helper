"""Configuration for the Engraver Camera Assistant."""

import os

# Camera settings
REAL_CAMERA_INDEX = int(os.environ.get("REAL_CAMERA_INDEX", "0"))
REAL_CAMERA_WIDTH = int(os.environ.get("REAL_CAMERA_WIDTH", "1280"))
REAL_CAMERA_HEIGHT = int(os.environ.get("REAL_CAMERA_HEIGHT", "720"))
REAL_CAMERA_FPS = int(os.environ.get("REAL_CAMERA_FPS", "30"))

# Virtual camera settings
VIRTUAL_CAMERA_FPS = int(os.environ.get("VIRTUAL_CAMERA_FPS", "30"))
VIRTUAL_CAMERA_WIDTH = int(os.environ.get("VIRTUAL_CAMERA_WIDTH", "1280"))
VIRTUAL_CAMERA_HEIGHT = int(os.environ.get("VIRTUAL_CAMERA_HEIGHT", "720"))
VIRTUAL_CAMERA_NAME = os.environ.get("VIRTUAL_CAMERA_NAME", "Engraver AI Camera")

# Network proxy fallback settings
NETWORK_PROXY_HOST = os.environ.get("NETWORK_PROXY_HOST", "0.0.0.0")
NETWORK_PROXY_PORT = int(os.environ.get("NETWORK_PROXY_PORT", "8080"))

# Overlay settings
SHOW_OVERLAY = os.environ.get("SHOW_OVERLAY", "true").lower() == "true"
OVERLAY_TEXT = os.environ.get("OVERLAY_TEXT", "AI ASSISTANT ACTIVE")
