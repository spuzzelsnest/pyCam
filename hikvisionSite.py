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
# Configuration (every value can be overridden with an environment variable,
# e.g. from the .env file that pycam.service loads)
# ---------------------------------------------------------------------------
PORT = int(os.environ.get("PYCAM_PORT", 8000))
STREAM_RESOLUTION = (640, 480)
RECORDING_DURATION = int(os.environ.get("PYCAM_DURATION", 10))  # seconds
BITRATE = 10_000_000
FRAMERATE = 30  # only used so ffmpeg can timestamp the raw .h264 file
CAM_NAME = os.environ.get("PYCAM_NAME", "Cam1")
WATERMARK = os.environ.get("PYCAM_WATERMARK", "THIS IS A SECRET RECORDING")
LOG_LEVEL = os.environ.get("PYCAM_LOG_LEVEL", "INFO").upper()

# TMP_DIR: raw camera output. OUT_DIR: final video with the text overlay.
TMP_DIR = Path(os.environ.get("PYCAM_TMP_DIR", "/tmp/FTP/recordings"))
OUT_DIR = Path(os.environ.get("PYCAM_OUT_DIR", "/FTP/recordings"))

BASE_DIR = Path(__file__).resolve().parent

log = logging.getLogger("pycam")

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


class JournalFormatter(logging.Formatter):
    """Prefix each line with a syslog priority ("<4>") so journald stores the
    right severity and `journalctl -p warning -u pycam` works. journald adds
    the timestamp itself, so we leave it out."""

    PRIORITY = {
        logging.CRITICAL: 2,
        logging.ERROR: 3,
        logging.WARNING: 4,
        logging.INFO: 6,
        logging.DEBUG: 7,
    }

    def format(self, record):
        return f"<{self.PRIORITY.get(record.levelno, 6)}>{super().format(record)}"


def setup_logging() -> None:
    handler = logging.StreamHandler()  # stderr
    if os.environ.get("JOURNAL_STREAM"):
        # Set by systemd when stdout/stderr are connected to the journal.
        handler.setFormatter(JournalFormatter("%(name)s: %(message)s"))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=LOG_LEVEL, handlers=[handler])


def ensure_dir(path: Path) -> None:
    """Create `path` if needed and make sure we can write to it.

    Called at startup (fail fast) and again before every recording, because
    /tmp can be cleaned at any time (reboot, systemd-tmpfiles).
    """
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
            log.exception("Recording failed")
        finally:
            self._lock.release()

    def _record(self):
        ensure_dir(TMP_DIR)
        ensure_dir(OUT_DIR)

        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        raw_file = TMP_DIR / f"{CAM_NAME}_{stamp}.h264"
        out_file = OUT_DIR / f"{CAM_NAME}_{stamp}.mp4"

        log.info("Recording started: %s (%ds)", raw_file, RECORDING_DURATION)
        encoder = H264Encoder(BITRATE)
        self.camera.start_encoder(encoder, FileOutput(str(raw_file)))
        try:
            time.sleep(RECORDING_DURATION)
        finally:
            self.camera.stop_encoder(encoder)
        log.info("Recording stopped: %s", raw_file)

        # Burn text into the video. The raw .h264 has no timestamps, so tell
        # ffmpeg the framerate; the quote is swapped because it would end the
        # drawtext value early.
        text = f"{CAM_NAME} - {WATERMARK}".replace("'", "’")
        cmd = [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
            "-framerate", str(FRAMERATE), "-i", str(raw_file),
            "-vf", f"drawtext=expansion=none:text='{text}':fontcolor=white:fontsize=24:x=10:y=10",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an",
            str(out_file),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            log.error("ffmpeg timed out, raw file kept at %s", raw_file)
            return
        if result.returncode != 0:
            log.error(
                "ffmpeg failed (exit %d), raw file kept at %s: %s",
                result.returncode, raw_file, result.stderr.strip()[-500:],
            )
            return
        raw_file.unlink(missing_ok=True)
        log.info("Saved %s (%.1f MB)", out_file, out_file.stat().st_size / 1e6)


class StreamingHandler(server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Send the built-in access log through logging instead of raw stderr.
        log.info("%s %s", self.address_string(), format % args)

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
            log.info("Streaming client %s disconnected", self.client_address[0])
        except Exception as e:
            log.warning("Removed streaming client %s: %s", self.client_address[0], e)

    def _start_recording(self):
        if self.server.recorder.start():
            log.info("Recording requested by %s", self.client_address[0])
            self._send_response(
                f"Recording started ({RECORDING_DURATION}s).".encode("utf-8"),
                "text/plain; charset=utf-8",
            )
        else:
            log.warning("Recording requested by %s but one is already running", self.client_address[0])
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
    setup_logging()
    log.info(
        "pyCam starting (port=%d, duration=%ds, tmp=%s, out=%s)",
        PORT, RECORDING_DURATION, TMP_DIR, OUT_DIR,
    )

    # Fail fast with a clear message instead of on the first button press.
    try:
        ensure_dir(TMP_DIR)
        ensure_dir(OUT_DIR)
    except RuntimeError as e:
        log.error("%s", e)
        sys.exit(1)
    if shutil.which("ffmpeg") is None:
        log.warning("ffmpeg not found (sudo apt install ffmpeg): recordings will stay raw .h264")

    camera = None
    try:
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
    except Exception:
        log.exception("Could not start camera or web server (camera busy? port %d in use?)", PORT)
        if camera is not None:
            try:
                camera.close()
            except Exception:
                pass
        sys.exit(1)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    try:
        log.info("Listening on port %d", PORT)
        server_thread.start()
        stop.wait()
    finally:
        log.info("Shutting down...")
        httpd.shutdown()
        httpd.server_close()
        camera.stop_recording()
        camera.close()
        log.info("Stopped")


if __name__ == "__main__":
    main()
