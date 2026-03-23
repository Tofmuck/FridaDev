from __future__ import annotations

import logging
import os
import threading
import time

from . import admin_logs

logger = logging.getLogger("frida.adminactions")


def restart_runtime_async(target_name: str = "FridaDev", delay_s: float = 0.5) -> None:
    def worker() -> None:
        time.sleep(max(0.0, float(delay_s)))
        try:
            admin_logs.log_event(
                "runtime_restart",
                target=target_name,
                mode="container_self_exit",
                delay_s=delay_s,
                ok=True,
            )
            logger.info(
                "runtime_restart target=%s mode=container_self_exit delay_s=%s",
                target_name,
                delay_s,
            )
            os._exit(0)
        except Exception as exc:
            admin_logs.log_event(
                "runtime_restart_error",
                level="ERROR",
                target=target_name,
                error=str(exc),
            )
            logger.error("runtime_restart_error target=%s err=%s", target_name, exc)

    threading.Thread(target=worker, daemon=True).start()
