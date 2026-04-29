from datetime import datetime
import threading


class AuditLogger:
    def __init__(self, log_file="audit.log"):
        self.log_file = log_file
        self.lock = threading.Lock()

    def log(self, action, ip="-", condition="-", rate="-", baseline="-", duration="-"):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        line = (
            f"[{timestamp}] "
            f"{action} {ip} | {condition} | {rate} | {baseline} | {duration}\n"
        )

        with self.lock:
            with open(self.log_file, "a") as f:
                f.write(line)