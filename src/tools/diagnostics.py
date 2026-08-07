import os
import sys
import time
import shutil
import socket
import logging
import sqlite3
from typing import Dict, Any

from src.tools.base import BaseTool
from src.config import settings
from src.memory import memory_manager

logger = logging.getLogger("blaine.tools.diagnostics")

START_TIME = time.time()

class DiagnosticsTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_system_diagnostics"

    @property
    def description(self) -> str:
        return "Gathers real-time Docker container, CPU/RAM load, disk storage, SQLite database, and Redis queue diagnostics for Blaine."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def _get_ram_info(self) -> Dict[str, Any]:
        """Reads /proc/meminfo if available (Linux/Docker) or falls back gracefully."""
        meminfo_path = "/proc/meminfo"
        if os.path.exists(meminfo_path):
            try:
                mem = {}
                with open(meminfo_path, "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            if v.isdigit():
                                mem[k] = int(v) * 1024  # convert kB to Bytes
                total = mem.get("MemTotal", 0)
                available = mem.get("MemAvailable", mem.get("MemFree", 0))
                used = total - available
                percent = round((used / total) * 100, 1) if total > 0 else 0
                return {
                    "total_mb": round(total / (1024 * 1024), 1),
                    "used_mb": round(used / (1024 * 1024), 1),
                    "available_mb": round(available / (1024 * 1024), 1),
                    "percent_used": percent
                }
            except Exception as e:
                logger.debug(f"Error reading /proc/meminfo: {e}")

        return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent_used": 0}

    def _get_redis_info(self) -> Dict[str, Any]:
        if not settings.REDIS_HOST:
            return {"connected": False, "status": "Not configured"}
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((settings.REDIS_HOST, settings.REDIS_PORT))
            return {"connected": True, "status": "Online", "host": settings.REDIS_HOST, "port": settings.REDIS_PORT}
        except Exception as e:
            return {"connected": False, "status": f"Unreachable ({e})"}
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass

    def _get_db_path(self) -> str:
        if hasattr(memory_manager, "db_path"):
            return memory_manager.db_path
        elif hasattr(memory_manager, "_context") and hasattr(memory_manager._context, "db"):
            return memory_manager._context.db.db_path
        return ""

    def _get_db_info(self) -> Dict[str, Any]:
        db_path = self._get_db_path()
        exists = os.path.exists(db_path) if db_path else False
        size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2) if exists else 0

        counts = {"messages": 0, "facts": 0, "reminders": 0, "lists": 0}
        if exists:
            conn = None
            try:
                conn = sqlite3.connect(db_path, timeout=5.0)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chat_messages")
                counts["messages"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM user_facts")
                counts["facts"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM reminders WHERE status='PENDING'")
                counts["reminders"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM user_lists")
                counts["lists"] = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"Error querying SQLite stats: {e}")
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        return {
            "path": db_path,
            "exists": exists,
            "size_mb": size_mb,
            "counts": counts
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Container detection
        is_docker = os.path.exists("/.dockerenv") or os.path.exists("/proc/1/cgroup")
        hostname = socket.gethostname()

        # Uptime
        uptime_seconds = int(time.time() - START_TIME)
        uptime_hours = round(uptime_seconds / 3600, 2)

        # Load Average
        load_avg = [round(x, 2) for x in os.getloadavg()] if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]

        # Disk usage for data storage
        db_path = self._get_db_path()
        target_dir = os.path.dirname(db_path) if db_path else "/"

        disk_total_gb = disk_used_gb = disk_free_gb = disk_percent = 0.0
        try:
            usage = shutil.disk_usage(target_dir)
            disk_total_gb = round(usage.total / (1024**3), 2)
            disk_used_gb = round(usage.used / (1024**3), 2)
            disk_free_gb = round(usage.free / (1024**3), 2)
            disk_percent = round((usage.used / usage.total) * 100, 1)
        except Exception as e:
            logger.error(f"Error checking disk usage: {e}")

        ram = self._get_ram_info()
        redis_info = self._get_redis_info()
        db_info = self._get_db_info()

        # Build formatted message
        env_label = "🐋 Docker Container" if is_docker else "💻 Host System"
        msg_lines = [
            f"🛠️ <b>Blaine System Diagnostics</b> ({env_label})",
            f"• <b>Hostname</b>: <code>{hostname}</code>",
            f"• <b>Uptime</b>: {uptime_hours} hrs ({uptime_seconds}s)",
            f"• <b>Python</b>: v{sys.version.split()[0]}",
            "",
            "📊 <b>System Performance</b>",
            f"• <b>Load Avg (1/5/15m)</b>: {load_avg[0]}, {load_avg[1]}, {load_avg[2]}",
        ]

        if ram["total_mb"] > 0:
            msg_lines.append(f"• <b>RAM Usage</b>: {ram['used_mb']} MB / {ram['total_mb']} MB ({ram['percent_used']}%)")

        msg_lines.extend([
            f"• <b>Disk Storage</b>: {disk_used_gb} GB / {disk_total_gb} GB used ({disk_free_gb} GB free, {disk_percent}%)",
            "",
            "💾 <b>Database & State</b>",
            f"• <b>SQLite DB</b>: {db_info['size_mb']} MB",
            f"• <b>Pending Reminders</b>: {db_info['counts']['reminders']}",
            f"• <b>Saved Facts</b>: {db_info['counts']['facts']}",
            f"• <b>Saved List Items</b>: {db_info['counts']['lists']}",
            "",
            "🔌 <b>Connected Services</b>",
            f"• <b>AI Engine</b>: Gemini (<code>{settings.GEMINI_MODEL_NAME}</code>)",
            f"• <b>Task Queue (Redis)</b>: {'🟢 Online' if redis_info['connected'] else '🔴 Offline/Unreachable'}",
            f"• <b>Cloud Storage</b>: MEGA S3 & Google Drive Ready"
        ])

        formatted_msg = "\n".join(msg_lines)

        return {
            "status": "SUCCESS",
            "is_docker": is_docker,
            "hostname": hostname,
            "uptime_seconds": uptime_seconds,
            "load_avg": load_avg,
            "ram": ram,
            "disk": {
                "total_gb": disk_total_gb,
                "used_gb": disk_used_gb,
                "free_gb": disk_free_gb,
                "percent_used": disk_percent
            },
            "database": db_info,
            "redis": redis_info,
            "message": formatted_msg
        }
