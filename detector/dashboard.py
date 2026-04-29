import time
import psutil
from flask import Flask, jsonify, render_template_string


class MetricsDashboard:
    def __init__(self, monitor, baseline, blocker):
        self.monitor = monitor
        self.baseline = baseline
        self.blocker = blocker
        self.started_at = time.time()

        self.app = Flask(__name__)
        self._setup_routes()

    def _get_metrics(self):
        baseline_data = self.baseline.get_baseline()

        return {
            "uptime_seconds": int(time.time() - self.started_at),
            "global_requests_per_minute": self.monitor.get_global_rate(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "effective_mean": round(baseline_data["mean"], 2),
            "effective_stddev": round(baseline_data["stddev"], 2),
            "error_mean": round(baseline_data["error_mean"], 2),
            "top_ips": self.monitor.get_top_ips(10),
            "banned_ips": self.blocker.get_blocked_ips(),
            "hourly_baselines": self.baseline.get_hourly_baselines()
        }

    def _setup_routes(self):
        @self.app.route("/api/metrics")
        def api_metrics():
            return jsonify(self._get_metrics())

        @self.app.route("/")
        def dashboard():
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>HNG Traffic Monitor</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body { font-family: Arial; margin: 30px; background: #111; color: #fff; }
        h1, h2 { color: #00d4ff; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #444; padding: 10px; text-align: left; }
        th { background: #222; }
        .card { background: #1a1a1a; padding: 20px; margin-bottom: 20px; border-radius: 10px; }
    </style>
</head>
<body>
    <h1>HNG Anomaly Detection Dashboard</h1>

    <div class="card">
        <p><strong>Global Requests/Minute:</strong> {{ data.global_requests_per_minute }}</p>
        <p><strong>CPU Usage:</strong> {{ data.cpu_percent }}%</p>
        <p><strong>Memory Usage:</strong> {{ data.memory_percent }}%</p>
        <p><strong>Effective Mean:</strong> {{ data.effective_mean }}</p>
        <p><strong>Effective StdDev:</strong> {{ data.effective_stddev }}</p>
        <p><strong>Error Baseline:</strong> {{ data.error_mean }}</p>
        <p><strong>Uptime:</strong> {{ data.uptime_seconds }} sec</p>
    </div>

    <h2>Top 10 Source IPs</h2>
    <table>
        <tr><th>IP Address</th><th>Total Requests</th></tr>
        {% for ip, count in data.top_ips %}
        <tr><td>{{ ip }}</td><td>{{ count }}</td></tr>
        {% endfor %}
    </table>

    <h2>Banned IPs</h2>
    <table>
        <tr><th>IP</th><th>Ban Count</th><th>Remaining</th></tr>
        {% for ip in data.banned_ips %}
        <tr>
            <td>{{ ip.ip }}</td>
            <td>{{ ip.ban_count }}</td>
            <td>
                {% if ip.expires_in is none %}
                    PERMANENT
                {% else %}
                    {{ ip.expires_in }} sec
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <h2>Hourly Baseline</h2>
    <table>
        <tr><th>Hour</th><th>Avg Traffic</th></tr>
        {% for hour, avg in data.hourly_baselines.items() %}
        <tr><td>{{ hour }}</td><td>{{ avg }}</td></tr>
        {% endfor %}
    </table>

</body>
</html>
            """, data=self._get_metrics())

    def start(self, host="0.0.0.0", port=5000):
        """
        Start dashboard in production-safe mode.
        """

        def run():
            self.app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False
            )

        import threading
        thread = threading.Thread(target=run, daemon=True)
        thread.start()