import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

import importlib.util
import os

module_path = os.path.join(os.path.dirname(__file__), 'ui-displayer.py')
spec = importlib.util.spec_from_file_location('uidisp', module_path)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)

def main():
    app = QApplication(sys.argv)
    w = ui.HMIWindow()
    w.show()

    def emit_alarm():
        ui.ALARM_BUS.alarm_triggered.emit({
            "timestamp": "",
            "gauge_name": "Test Gauge",
            "gauge_type": "Pressure",
            "alarm_type": "HIGH",
            "value": 12.3,
            "limit": 10.0,
            "unit": "bar",
            "status": "TRIGGERED"
        })

    def stop_app():
        app.quit()

    QTimer.singleShot(1000, emit_alarm)
    QTimer.singleShot(4000, stop_app)
    app.exec_()

if __name__ == "__main__":
    main()
