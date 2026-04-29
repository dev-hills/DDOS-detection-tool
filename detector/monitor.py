import json
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional


class TrafficMonitor:
    def __init__(self, log_file: str):
        self.log_file = log_file

        # 60-second global request timestamps
        self.global_window = deque()

        # per-IP request timestamps
        self.ip_windows = defaultdict(deque)

        # per-IP error timestamps
        self.ip_error_windows = defaultdict(deque)

        # request counters for dashboard
        self.ip_totals = defaultdict(int)

        # latest parsed log entry
        self.last_entry = None

        # lock for thread safety
        self.lock = threading.Lock()

    def _cleanup_old_entries(self, now: float):
        """
        Remove timestamps older than 60 seconds from all deques.
        """
        cutoff = now - 60

        while self.global_window and self.global_window[0] < cutoff:
            self.global_window.popleft()

        for ip in list(self.ip_windows.keys()):
            while self.ip_windows[ip] and self.ip_windows[ip][0] < cutoff:
                self.ip_windows[ip].popleft()

            if not self.ip_windows[ip]:
                del self.ip_windows[ip]

        for ip in list(self.ip_error_windows.keys()):
            while self.ip_error_windows[ip] and self.ip_error_windows[ip][0] < cutoff:
                self.ip_error_windows[ip].popleft()

            if not self.ip_error_windows[ip]:
                del self.ip_error_windows[ip]

    def process_log_line(self, line: str):
        """
        Parse one JSON log line and update tracking windows.
        """
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return

        source_ip = entry.get("source_ip")
        timestamp = time.time()

        if not source_ip:
            return

        status = int(entry.get("status", 200))

        with self.lock:
            self.global_window.append(timestamp)
            self.ip_windows[source_ip].append(timestamp)
            self.ip_totals[source_ip] += 1

            if 400 <= status < 600:
                self.ip_error_windows[source_ip].append(timestamp)

            self.last_entry = {
                "source_ip": source_ip,
                "timestamp": entry.get("timestamp"),
                "method": entry.get("method"),
                "path": entry.get("path"),
                "status": status,
                "response_size": entry.get("response_size"),
            }

            self._cleanup_old_entries(timestamp)

    def tail_log(self):
        """
        Continuously tail nginx log file in real time.
        """
        with open(self.log_file, "r") as file:
            file.seek(0, 2)  # move to end of file

            while True:
                line = file.readline()

                if not line:
                    time.sleep(0.2)
                    continue

                self.process_log_line(line.strip())

    def get_global_rate(self) -> int:
        """
        Total requests in the last 60 seconds.
        """
        with self.lock:
            return len(self.global_window)

    def get_ip_rate(self, ip: str) -> int:
        """
        Requests from one IP in the last 60 seconds.
        """
        with self.lock:
            return len(self.ip_windows.get(ip, []))

    def get_ip_error_rate(self, ip: str) -> int:
        """
        Error responses from one IP in the last 60 seconds.
        """
        with self.lock:
            return len(self.ip_error_windows.get(ip, []))

    def get_all_ip_rates(self) -> Dict[str, int]:
        """
        Current request counts for every active IP.
        """
        with self.lock:
            return {ip: len(window) for ip, window in self.ip_windows.items()}

    def get_top_ips(self, limit: int = 10):
        """
        Return top IPs by request count.
        """
        with self.lock:
            sorted_ips = sorted(
                self.ip_totals.items(),
                key=lambda item: item[1],
                reverse=True
            )
            return sorted_ips[:limit]

    def get_last_entry(self) -> Optional[dict]:
        """
        Most recent parsed request.
        """
        with self.lock:
            return self.last_entry

    def start(self):
        """
        Start log monitoring in a background thread.
        """
        thread = threading.Thread(target=self.tail_log, daemon=True)
        thread.start()