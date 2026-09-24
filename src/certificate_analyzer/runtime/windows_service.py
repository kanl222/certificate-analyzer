import sys

from certificate_analyzer.constants import SERVICE_DISPLAY_NAME, SERVICE_NAME


def require_windows():
    if sys.platform != "win32":
        raise RuntimeError(
            "Управление службой доступно в Windows; на Linux используйте systemd"
        )


if sys.platform == "win32":
    import win32service
    import win32serviceutil

    from certificate_analyzer.runtime.worker import MonitoringWorker

    class CertificateAnalyzerService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME

        def __init__(self, args):
            super().__init__(args)
            self.worker = MonitoringWorker()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.worker.stop()

        def SvcDoRun(self):
            self.worker.run_forever()


def install_service():
    require_windows()
    win32serviceutil.InstallService(
        "certificate_analyzer.runtime.windows_service.CertificateAnalyzerService",
        SERVICE_NAME,
        SERVICE_DISPLAY_NAME,
        startType=win32service.SERVICE_AUTO_START,
    )


def remove_service():
    require_windows()
    win32serviceutil.RemoveService(SERVICE_NAME)


def run_as_service(args=None):
    require_windows()
    import servicemanager

    if not args:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CertificateAnalyzerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(
            CertificateAnalyzerService, argv=[sys.argv[0], *args]
        )
