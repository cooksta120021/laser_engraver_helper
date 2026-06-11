"""Network Camera Proxy — Fallback for LightBurn Network Camera mode.

If the virtual camera driver does not work, run this instead. It serves an
MJPEG HTTP stream that LightBurn 2.1+ can consume as a Network camera.
LightBurn 1.7 users should prefer main.py (virtual camera).

Usage:
    python network_proxy.py

In LightBurn, add a Network camera with URL: http://YOUR_PC_IP:8080/video.mjpg
"""

import io
import threading
import cv2
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
import recognition

# Shared frame buffer (thread-safe via lock)
_frame_lock = threading.Lock()
_latest_frame: bytes | None = None


class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/video.mjpg":
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=--jpgboundary")
            self.end_headers()
            try:
                while True:
                    with _frame_lock:
                        frame_bytes = _latest_frame
                    if frame_bytes is None:
                        continue
                    self.wfile.write(b"--jpgboundary\r\n")
                    self.send_header("Content-type", "image/jpeg")
                    self.send_header("Content-length", str(len(frame_bytes)))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b"\r\n")
            except BrokenPipeError:
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging


def capture_loop():
    """Thread: captures from real camera and processes frames."""
    global _latest_frame

    cap = cv2.VideoCapture(config.REAL_CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.REAL_CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.REAL_CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.REAL_CAMERA_FPS)

    if not cap.isOpened():
        print("[ERROR] Cannot open real camera.")
        return

    print("[INFO] Capture loop started.")
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 85]

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        if frame.shape[1] != config.VIRTUAL_CAMERA_WIDTH or frame.shape[0] != config.VIRTUAL_CAMERA_HEIGHT:
            frame = cv2.resize(frame, (config.VIRTUAL_CAMERA_WIDTH, config.VIRTUAL_CAMERA_HEIGHT))

        if config.SHOW_OVERLAY:
            frame = recognition.process_frame(frame, config.OVERLAY_TEXT)

        ok, buf = cv2.imencode(".jpg", frame, encode_params)
        if ok:
            with _frame_lock:
                _latest_frame = buf.tobytes()

    cap.release()


def main():
    # Start capture thread
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    # Start HTTP server
    server = HTTPServer((config.NETWORK_PROXY_HOST, config.NETWORK_PROXY_PORT), MJPEGHandler)
    print(f"[INFO] MJPEG server listening on http://{config.NETWORK_PROXY_HOST}:{config.NETWORK_PROXY_PORT}/video.mjpg")
    print("[INFO] In LightBurn, add a Network camera with the URL above.")
    print("[INFO] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
