"""Background UDP traffic pacer to prevent Windows Wi-Fi driver throttling.

By emitting minimal 1-byte UDP datagrams at ~20 Hz (every 50 ms), the Wi-Fi
network interface card is kept in Continuous Aware Mode (CAM) rather than
falling into Power Save (PSP) mode, ensuring consistent 10 Hz telemetry
sampling without driver sleep jitter.
"""

import socket
import threading
import time


class TrafficPacer:
    """Threaded UDP keep-alive pacer."""

    def __init__(self, target_ip: str = "127.0.0.1", port: int = 9999, rate_hz: float = 20.0):
        self.target_ip = target_ip
        self.port = int(port)
        self.interval = 1.0 / max(1.0, float(rate_hz))
        self._stop_event = threading.Event()
        self._thread = None
        self._sock = None
        self.packets_sent = 0

    def start(self):
        """Start the background pacer thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="WiFiTrafficPacer")
        self._thread.start()

    def stop(self):
        """Stop the background pacer thread gracefully."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _run(self):
        payload = b"\x00"
        while not self._stop_event.is_set():
            try:
                if self._sock:
                    self._sock.sendto(payload, (self.target_ip, self.port))
                    self.packets_sent += 1
            except Exception:
                # Silently ignore network unreachable or local loopback warnings
                pass
            time.sleep(self.interval)
