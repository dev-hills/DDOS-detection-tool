import time
import threading
import statistics
from collections import defaultdict, deque


class TrafficBaseline:
    def __init__(self, monitor, audit_logger=None):
        self.monitor = monitor
        self.audit_logger = audit_logger

        # rolling 30-minute per-second samples
        self.global_history = deque(maxlen=1800)

        # rolling 30-minute per-second error rates
        self.error_history = deque(maxlen=1800)

        # hourly traffic buckets
        self.hourly_history = defaultdict(list)

        # calculated values
        self.effective_mean = 1.0
        self.effective_stddev = 1.0
        self.error_mean = 0.0

        self.last_recalculation = None

        self.lock = threading.Lock()

    def _current_hour_key(self):
        """
        Returns current hour slot like:
        2026-04-28-18
        """
        return time.strftime("%Y-%m-%d-%H")

    def collect_sample(self):
        """
        Collect current traffic metrics every second.
        """
        global_rate = self.monitor.get_global_rate()

        ip_rates = self.monitor.get_all_ip_rates()
        total_errors = 0

        for ip in ip_rates:
            total_errors += self.monitor.get_ip_error_rate(ip)

        current_hour = self._current_hour_key()

        with self.lock:
            self.global_history.append(global_rate)
            self.error_history.append(total_errors)
            self.hourly_history[current_hour].append(global_rate)

            # keep only latest 24 hourly slots
            if len(self.hourly_history) > 24:
                oldest = sorted(self.hourly_history.keys())[0]
                del self.hourly_history[oldest]

    def recalculate(self):
        """
        Recalculate rolling baseline.
        Runs every 60 seconds.
        """
        with self.lock:
            current_hour = self._current_hour_key()
            current_hour_samples = self.hourly_history.get(current_hour, [])

            # prefer current hour if enough data
            if len(current_hour_samples) >= 60:
                data = current_hour_samples
            else:
                data = list(self.global_history)

            if len(data) >= 2:
                mean = statistics.mean(data)
                stddev = statistics.stdev(data)
            elif len(data) == 1:
                mean = data[0]
                stddev = 1.0
            else:
                mean = 1.0
                stddev = 1.0

            print(f"[BASELINE] mean={mean:.2f} std={stddev:.2f}")    

            # prevent impossible zero values
            self.effective_mean = max(mean, 1.0)
            self.effective_stddev = max(stddev, 1.0)

            if self.error_history:
                self.error_mean = statistics.mean(self.error_history)
            else:
                self.error_mean = 0.0

            self.last_recalculation = time.time()

            if self.audit_logger:
                self.audit_logger.log(
                    action="BASELINE",
                    ip="-",
                    condition="recalculated",
                    rate=round(self.effective_mean, 2),
                    baseline=round(self.effective_stddev, 2),
                    duration="-"
                )

    def get_baseline(self):
        """
        Return current baseline metrics.
        """
        with self.lock:
            return {
                "mean": self.effective_mean,
                "stddev": self.effective_stddev,
                "error_mean": self.error_mean,
                "last_recalculation": self.last_recalculation,
            }

    def get_hourly_baselines(self):
        """
        Return average traffic per hour.
        Used for dashboard graph.
        """
        with self.lock:
            output = {}

            for hour, samples in self.hourly_history.items():
                if samples:
                    output[hour] = round(statistics.mean(samples), 2)

            return output

    def start(self):
        """
        Start:
        - collect sample every second
        - recalculate every 60 sec
        """
        def worker():
            last_recalc = time.time()

            while True:
                self.collect_sample()

                now = time.time()

                if now - last_recalc >= 60:
                    self.recalculate()
                    last_recalc = now

                time.sleep(1)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()