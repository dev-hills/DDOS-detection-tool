import time
import threading


class AnomalyDetector:
    def __init__(self, monitor, baseline, blocker, notifier, config):
        self.monitor = monitor
        self.baseline = baseline
        self.blocker = blocker
        self.notifier = notifier

        self.zscore_threshold = config.get("zscore_threshold", 3.0)
        self.multiplier_threshold = config.get("multiplier_threshold", 5)

        # prevent repeated alerts
        self.last_global_alert = 0
        self.last_ip_alerts = {}

        # cooldowns
        self.global_alert_cooldown = 60
        self.ip_alert_cooldown = 60

    def calculate_zscore(self, current, mean, stddev):
        if stddev <= 0:
            return 0.0
        return (current - mean) / stddev

    def should_alert_ip(self, ip, now):
        last_alert = self.last_ip_alerts.get(ip, 0)
        return (now - last_alert) > self.ip_alert_cooldown

    def should_alert_global(self, now):
        return (now - self.last_global_alert) > self.global_alert_cooldown

    def check_global_anomaly(self):
        """
        Detect traffic spike across all traffic.
        """
        now = time.time()

        current_rate = self.monitor.get_global_rate()
        baseline_data = self.baseline.get_baseline()

        mean = baseline_data["mean"]
        stddev = baseline_data["stddev"]

        zscore = self.calculate_zscore(current_rate, mean, stddev)

        triggered = (
            zscore > self.zscore_threshold or
            current_rate > mean * self.multiplier_threshold
        )

        if triggered and self.should_alert_global(now):
            self.last_global_alert = now

            condition = (
                f"GLOBAL anomaly | z={round(zscore,2)} "
                f"| current={current_rate} "
                f"| baseline={round(mean,2)}"
            )

            self.notifier.send_global_alert(
                condition=condition,
                current_rate=current_rate,
                baseline=round(mean, 2),
                timestamp=now
            )

    def check_ip_anomalies(self):
        """
        Detect aggressive individual IPs.
        """
        now = time.time()

        ip_rates = self.monitor.get_all_ip_rates()
        baseline_data = self.baseline.get_baseline()

        mean = baseline_data["mean"]
        stddev = baseline_data["stddev"]
        error_mean = baseline_data["error_mean"]

        for ip, current_rate in ip_rates.items():
          

            ip_error_rate = self.monitor.get_ip_error_rate(ip)

            zscore_threshold = self.zscore_threshold
            multiplier_threshold = self.multiplier_threshold

            # tighten thresholds if error surge
            if error_mean > 0 and ip_error_rate > error_mean * 3:
                zscore_threshold = max(2.0, self.zscore_threshold - 0.5)
                multiplier_threshold = max(3, self.multiplier_threshold - 1)

            zscore = self.calculate_zscore(current_rate, mean, stddev)

            triggered = (
                zscore > zscore_threshold or
                current_rate > mean * multiplier_threshold
            )

            if triggered and self.should_alert_ip(ip, now):
                self.last_ip_alerts[ip] = now

                duration = self.blocker.block_ip(
                    ip=ip,
                    condition=f"z={round(zscore,2)}",
                    rate=current_rate,
                    baseline=round(mean, 2)
                )

                self.notifier.send_ban_alert(
                    ip=ip,
                    condition=f"IP anomaly | z={round(zscore,2)}",
                    current_rate=current_rate,
                    baseline=round(mean, 2),
                    duration=duration,
                    timestamp=now
                )

    def run_cycle(self):
        """
        Run one detection cycle.
        """
        self.check_global_anomaly()
        self.check_ip_anomalies()

    def start(self):
        """
        Run detector every 5 seconds.
        """
        def worker():
            while True:
                try:
                    self.run_cycle()
                except Exception as e:
                    print(f"[DETECTOR ERROR] {e}")

                time.sleep(5)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()