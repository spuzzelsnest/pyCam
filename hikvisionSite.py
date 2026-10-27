#!/usr/bin/env python3

import datetime
import io
import logging
import os
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
from http import server
from pathlib import Path

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, JpegEncoder
from picamera2.outputs import FileOutput

# ---------------------------------------------------------------------------
# Configuration (every value can be overridden with an environment variable)
# ---------------------------------------------------------------------------
PORT = int(os.environ.get("PYCAM_PORT", 8000))
STREAM_RESOLUTION = (640, 480)
RECORDING_DURATION = int(os.environ.get("PYCAM_DURATION", 10))  # seconds
BITRATE = 10_000_000
FRAMERATE = 30  # only used so ffmpeg can timestamp the raw .h264 file
CAM_NAME = os.environ.get("PYCAM_NAME", "Cam1")
WATERMARK = os.environ.get("PYCAM_WATERMARK", "THIS IS A SECRET RECORDING")

# TMP_DIR: raw camera output. OUT_DIR: final video with the text overlay.
TMP_DIR = Path(os.environ.get("PYCAM_TMP_DIR", "/tmp/FTP/recordings"))
OUT_DIR = Path(os.environ.get("PYCAM_OUT_DIR", "/FTP/recordings"))

BASE_DIR = Path(__file__).resolve().parent

PAGE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Security Portal CCTV Surveillance Camera</title>
<link rel="icon" type="image/png" href="favicon.png">
<script>
async function sendRecordRequest() {
  const status = document.getElementById("status");
  try {
    const res = await fetch("/record", { method: "POST" });
    status.textContent = await res.text();
  } catch (err) {
    status.textContent = "Request failed: " + err;
  }
}
</script>
</head>
<body>
<center>
<h1>Security Portal CCTV Surveillance Camera</h1>
<img src="stream.mjpg" width="640" height="480" id="still"/>
<p>
<button id="record" type="button" onclick="sendRecordRequest()">Record Something suspicious</button>
</p>
<p id="status"></p>
</center>
</body>
</html>
"""


def ensure_dir(path: Path) -> None:

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"Cannot create directory {path}: {e}. "
            f"Fix: sudo mkdir -p {path} && sudo chown $USER {path} "
            f"(or point PYCAM_TMP_DIR / PYCAM_OUT_DIR somewhere you can write)"
        ) from e
    if not os.access(path, os.W_OK):
        raise RuntimeError(f"Directory {path} is not writable by the current user")


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)


class Recorder:
    """Records a clip while the live stream keeps running. One clip at a time."""

    def __init__(self, camera):
        self.camera = camera
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start a recording in the background. False if one is already running."""
        if not self._lock.acquire(blocking=False):
            return False
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self):
        try:
            self._record()
        except Exception:
            logging.exception("Recording failed")
        finally:
            self._lock.release()

    def _record(self):
        ensure_dir(TMP_DIR)
        ensure_dir(OUT_DIR)

        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        raw_file = TMP_DIR / f"{CAM_NAME}_{stamp}.h264"
        out_file = OUT_DIR / f"{CAM_NAME}_{stamp}.mp4"

        encoder = H264Encoder(BITRATE)
        self.camera.start_encoder(encoder, FileOutput(str(raw_file)))
        try:
            time.sleep(RECORDING_DURATION)
        finally:
            self.camera.stop_encoder(encoder)
        logging.info("Recording stopped: %s", raw_file)

        # Burn text into the video. The raw .h264 has no timestamps, so tell
        # ffmpeg the framerate; the quote is swapped because it would end the
        # drawtext value early.
        text = f"{CAM_NAME} - {WATERMARK}".replace("'", "\u2019")
        cmd = [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
            "-framerate", str(FRAMERATE), "-i", str(raw_file),
            "-vf", f"drawtext=expansion=none:text='{text}':fontcolor=white:fontsize=24:x=10:y=10",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an",
            str(out_file),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=300)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logging.error("Failed to add text overlay, raw file kept at %s: %s", raw_file, e)
            return
        raw_file.unlink(missing_ok=True)
        logging.info("Text overlay added to video: %s", out_file)


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/index.html")
            self.end_headers()
        elif self.path == "/index.html":
            self._send_response(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/favicon.png":
            self._serve_favicon()
        elif self.path == "/stream.mjpg":
            self._serve_video_stream()
        else:
            self.send_error(404)

    def do_POST(self):
        # State-changing action: POST, so a link, prefetch or crawler can't trigger it.
        if self.path == "/record":
            self._start_recording()
        else:
            self.send_error(404)

    def _serve_favicon(self):
        try:
            content = (BASE_DIR / "favicon.png").read_bytes()
        except OSError:
            self.send_error(404)
            return
        self._send_response(content, "image/png")

    def _serve_video_stream(self):
        output = self.server.output
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()
        try:
            while True:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                self.wfile.write(b"--FRAME\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(b"Content-Length: %d\r\n\r\n" % len(frame))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            logging.info("Streaming client %s disconnected", self.client_address)
        except Exception as e:
            logging.warning("Removed streaming client %s: %s", self.client_address, e)

    def _start_recording(self):
        if self.server.recorder.start():
            self._send_response(
                f"Recording started ({RECORDING_DURATION}s).".encode("utf-8"),
                "text/plain; charset=utf-8",
            )
        else:
            self._send_response(
                b"A recording is already in progress.",
                "text/plain; charset=utf-8",
                status=409,
            )

    def _send_response(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, output, recorder):
        self.output = output
        self.recorder = recorder
        super().__init__(address, handler)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Fail fast with a clear message instead of on the first button press.
    try:
        ensure_dir(TMP_DIR)
        ensure_dir(OUT_DIR)
    except RuntimeError as e:
        sys.exit(str(e))
    if shutil.which("ffmpeg") is None:
        logging.warning("ffmpeg not found (sudo apt install ffmpeg): recordings will stay raw .h264")

    camera = Picamera2()
    camera.configure(
        camera.create_video_configuration(
            main={"size": STREAM_RESOLUTION, "format": "RGB888"},
            lores={"size": STREAM_RESOLUTION, "format": "YUV420"},
            raw={"size": STREAM_RESOLUTION},
            display=None,
        )
    )
    output = StreamingOutput()
    camera.start_recording(JpegEncoder(), FileOutput(output))

    httpd = StreamingServer(("", PORT), StreamingHandler, output, Recorder(camera))
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    try:
        logging.info("Starting server on port %d...", PORT)
        server_thread.start()
        stop.wait()
    finally:
        logging.info("Shutting down...")
        httpd.shutdown()
        httpd.server_close()
        camera.stop_recording()
        camera.close()


if __name__ == "__main__":
    main()
