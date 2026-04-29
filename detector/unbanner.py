import time
import threading


class AutoUnbanner:
    def __init__(self, blocker, notifier, audit_logger=None, interval=10):
        self.blocker = blocker
        self.notifier = notifier
        self.interval = interval  # check every X seconds
        self.audit_logger = audit_logger

    def check_expired_bans(self):
        """
        Find expired bans and remove them.
        """
        expired_ips = self.blocker.get_expired_ips()

        for ip in expired_ips:
            self.blocker.unblock_ip(ip)

            self.notifier.send_unban_alert(
                    ip=ip,
                    timestamp=time.time()
                )
                   

    def run_cycle(self):
        """
        Run one unban cycle.
        """
        try:
            self.check_expired_bans()
        except Exception as e:
            print(f"[UNBANNER ERROR] {e}")

    def start(self):
        """
        Start continuous unban monitoring.
        """
        def worker():
            while True:
                self.run_cycle()
                time.sleep(self.interval)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()