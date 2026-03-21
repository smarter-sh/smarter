"""
This module provides a function to gather diagnostics information about the
current environment, including platform details, Python environment, resource
usage, and network connections. The diagnostics information is returned as a
structured dictionary that can be used for debugging and monitoring purposes.
"""

import os
import platform  # library to view information about the server host this module runs on
import sys
import threading
import time
from importlib.metadata import distributions  # library for accessing package metadata
from typing import Any

import psutil


def get_diagnostics() -> dict[str, Any]:
    """
    Gathers diagnostics information about the current environment, including
    platform details, Python environment, resource usage, and network connections.

    :return: A dictionary containing the diagnostics information.
    :rtype: dict[str, Any]
    """

    def get_installed_packages():
        return [(dist.metadata["Name"], dist.version) for dist in distributions()]

    packages = get_installed_packages()
    packages_dict = [{"name": name, "version": version} for name, version in packages]

    retval = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "environment": {
            "platform": {
                "os": {
                    "name": os.name,
                    "cwd": os.getcwd(),
                    "process_id": os.getpid(),
                    "parent_process_id": os.getppid(),
                    "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.Process().create_time())),
                    "uptime_seconds": int(time.time() - psutil.Process().create_time()),
                },
                "system": platform.system(),
                "release": platform.release(),
            },
            "python": {
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "python_compiler": platform.python_compiler(),
                "python_build": platform.python_build(),
                "python_installed_packages": packages_dict,
                "loaded_modules": list(sys.modules.keys()),
            },
            "resources": {
                "memory_info": psutil.Process().memory_info()._asdict(),
                "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
                "open_files": [f.path for f in psutil.Process().open_files()],
                "num_threads": psutil.Process().num_threads(),
                "thread_info": [
                    {
                        "id": t.ident,
                        "name": t.name,
                        "is_alive": t.is_alive(),
                    }
                    for t in threading.enumerate()
                ],
                "disk_usage": psutil.disk_usage(os.getcwd())._asdict(),
            },
            "network": {
                "connections": [
                    {
                        "fd": c.fd,
                        "family": str(c.family),
                        "type": str(c.type),
                        "laddr": c.laddr,
                        "raddr": c.raddr,
                        "status": c.status,
                    }
                    for c in psutil.Process().net_connections()
                ],
            },
        },
    }
    return retval
