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
from audit_logger import AuditLogger

BASE_DIR = os.path.dirname(__file__)


def load_config():
    config_path = os.path.join(BASE_DIR, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    audit_logger = AuditLogger(os.path.join(BASE_DIR, "audit.log"))

    audit_logger.log(
        action="STARTUP",
        ip="-",
        condition="detector started",
        rate="-",
        baseline="-",
        duration="-",
    )

    # =========================
    # CORE COMPONENTS
    # =========================

    monitor = TrafficMonitor(config["log_file"])
    monitor.start()

    blocker = IPBlocker(config=config, audit_logger=audit_logger)

    notifier = SlackNotifier(config["slack_webhook"])

    baseline = TrafficBaseline(monitor=monitor, audit_logger=audit_logger)
    baseline.start()

    detector = AnomalyDetector(
        monitor=monitor,
        baseline=baseline,
        blocker=blocker,
        notifier=notifier,
        config=config,
    )
    detector.start()

    unbanner = AutoUnbanner(
        blocker=blocker, notifier=notifier, audit_logger=audit_logger, interval=10
    )
    unbanner.start()

    dashboard = MetricsDashboard(monitor=monitor, baseline=baseline, blocker=blocker)
    dashboard.start()

    # =========================
    # KEEP PROCESS ALIVE
    # =========================

    print("🚀 HNG Anomaly Detection System Started")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
