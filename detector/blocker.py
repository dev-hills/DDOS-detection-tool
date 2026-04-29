import subprocess
import threading
import time


class IPBlocker:
    def __init__(self, config, audit_logger=None):
        self.audit_logger = audit_logger

        # Backoff schedule in seconds
        self.ban_schedule = config.get("ban_schedule", [600, 1800, 7200])

        # ip -> metadata
        self.blocked_ips = {}

        self.lock = threading.Lock()

    def _run_iptables(self, command):
        """
        Run iptables command safely.
        """
        try:
            subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[IPTABLES ERROR] {e}")
            return False

    def is_blocked(self, ip):
        with self.lock:
            return ip in self.blocked_ips

    def get_ban_count(self, ip):
        with self.lock:
            if ip not in self.blocked_ips:
                return 0
            return self.blocked_ips[ip]["ban_count"]

    def get_ban_duration(self, ban_count):
        """
        Return next backoff duration.
        """
        if ban_count < len(self.ban_schedule):
            return self.ban_schedule[ban_count]

        return None  # permanent

    def block_ip(self, ip, condition, rate, baseline):
        """
        Block an IP with escalating duration.
        Returns duration.
        """
        with self.lock:
            previous_ban_count = 0

            if ip in self.blocked_ips:
                previous_ban_count = self.blocked_ips[ip]["ban_count"]

            duration = self.get_ban_duration(previous_ban_count)

            if ip not in self.blocked_ips:
                success = self._run_iptables([
                    "iptables",
                    "-A",
                    "INPUT",
                    "-s",
                    ip,
                    "-j",
                    "DROP"
                ])

                if not success:
                    return None

            self.blocked_ips[ip] = {
                "blocked_at": time.time(),
                "expires_at": None if duration is None else time.time() + duration,
                "ban_count": previous_ban_count + 1,
                "duration": duration,
                "condition": condition,
                "rate": rate,
                "baseline": baseline
            }

            if self.audit_logger:
                self.audit_logger(
                    action="BAN",
                    ip=ip,
                    condition=condition,
                    rate=rate,
                    baseline=baseline,
                    duration="PERMANENT" if duration is None else duration
                )

            return duration

    def unblock_ip(self, ip):
        """
        Remove iptables rule for an IP.
        """
        with self.lock:
            if ip not in self.blocked_ips:
                return False

            success = self._run_iptables([
                "iptables",
                "-D",
                "INPUT",
                "-s",
                ip,
                "-j",
                "DROP"
            ])

            if not success:
                return False

            metadata = self.blocked_ips[ip]
            del self.blocked_ips[ip]

            if self.audit_logger:
                self.audit_logger(
                    action="UNBAN",
                    ip=ip,
                    condition=metadata["condition"],
                    rate=metadata["rate"],
                    baseline=metadata["baseline"],
                    duration="-"
                )

            return True

    def get_expired_ips(self):
        """
        Return IPs whose temporary bans have expired.
        """
        now = time.time()
        expired = []

        with self.lock:
            for ip, data in self.blocked_ips.items():
                expires_at = data["expires_at"]

                if expires_at is None:
                    continue

                if now >= expires_at:
                    expired.append(ip)

        return expired

    def get_blocked_ips(self):
        """
        Return data for dashboard.
        """
        with self.lock:
            output = []

            for ip, data in self.blocked_ips.items():
                remaining = None

                if data["expires_at"] is not None:
                    remaining = max(0, int(data["expires_at"] - time.time()))

                output.append({
                    "ip": ip,
                    "blocked_at": data["blocked_at"],
                    "expires_in": remaining,
                    "ban_count": data["ban_count"],
                    "duration": data["duration"]
                })

            return output