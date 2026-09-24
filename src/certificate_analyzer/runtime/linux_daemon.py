import signal

from certificate_analyzer.runtime.worker import MonitoringWorker


def run(settings=None):
    worker = MonitoringWorker(settings)
    previous = {}
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: worker.stop())
        worker.run_forever()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
