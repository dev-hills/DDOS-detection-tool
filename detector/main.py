import time
import yaml
import os

from monitor import TrafficMonitor
from baseline import TrafficBaseline
from detector import AnomalyDetector
from blocker import IPBlocker
from notifier import SlackNotifier
from unbanner import AutoUnbanner
from dashboard import MetricsDashboard

BASE_DIR = os.path.dirname(__file__)


def load_config():
    config_path = os.path.join(BASE_DIR, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def write_audit_log(action, ip, condition, rate, baseline, duration):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    log_line = (
        f"[{timestamp}] {action} {ip} | "
        f"{condition} | {rate} | {baseline} | {duration}"
    )

    print(log_line)

    log_path = os.path.join(BASE_DIR, "audit.log")
    with open(log_path, "a") as f:
        f.write(log_line + "\n")


def main():
    config = load_config()

    # =========================
    # CORE COMPONENTS
    # =========================

    monitor = TrafficMonitor(config["log_file"])
    monitor.start()

    blocker = IPBlocker(
        config=config,
        audit_logger=write_audit_log
    )

    notifier = SlackNotifier(config["slack_webhook"])

    baseline = TrafficBaseline(
        monitor=monitor,
        audit_logger=write_audit_log
    )
    baseline.start()

    detector = AnomalyDetector(
        monitor=monitor,
        baseline=baseline,
        blocker=blocker,
        notifier=notifier,
        config=config
    )
    detector.start()

    unbanner = AutoUnbanner(
        blocker=blocker,
        notifier=notifier,
        interval=10
    )
    unbanner.start()

    dashboard = MetricsDashboard(
        monitor=monitor,
        baseline=baseline,
        blocker=blocker
    )
    dashboard.start()

    # =========================
    # KEEP PROCESS ALIVE
    # =========================

    print("🚀 HNG Anomaly Detection System Started")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()