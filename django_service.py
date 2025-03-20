import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess

class DjangoService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'DjangoWebApp'
    _svc_display_name_ = 'Django Web Application Service'
    _svc_description_ = 'Runs Django web application as a Windows service'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        try:
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            self.process = subprocess.Popen(
                ['python', 'manage.py', 'runserver', '0.0.0.0:8000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.process.wait()
        except Exception as e:
            servicemanager.LogErrorMsg(str(e))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(DjangoService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(DjangoService)