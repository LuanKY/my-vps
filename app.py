import datetime
import os
import time
import docker
import psutil
from fastapi import FastAPI, status

from schemas import HealthResponse, SystemMetricsResponse

# Initialize psutil baseline for non-blocking CPU percent measurements
psutil.cpu_percent(interval=None, percpu=True)

# ==============================================================================
# FastAPI Application Configuration
# ==============================================================================

app = FastAPI(
    title="VPS System Monitoring API",
    description="""
A lightweight real-time telemetry and resource monitoring API for VPS and host systems.
Exposes CPU (total and per-core), memory, swap, root storage, disk I/O, network, load average,
uptime, Docker container status, top CPU/memory processes, and active user sessions.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_docker_overview():
    """Collects Docker daemon status and a list of hosted containers."""
    try:
        client = docker.from_env()
        raw_containers = client.containers.list(all=True)

        containers = []
        running_count = 0
        stopped_count = 0

        for c in raw_containers:
            state = c.attrs.get("State", {}).get("Status", c.status)
            if state == "running":
                running_count += 1
            else:
                stopped_count += 1

            image_name = c.attrs.get("Config", {}).get("Image", "")
            if not image_name and c.image.tags:
                image_name = c.image.tags[0]

            containers.append({
                "id": c.short_id,
                "name": c.name.lstrip("/"),
                "image": image_name,
                "status": c.status,
                "state": state,
                "created": c.attrs.get("Created"),
                "ports": c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            })

        return {
            "installed": True,
            "total_containers": len(containers),
            "running_containers": running_count,
            "stopped_containers": stopped_count,
            "containers": containers,
            "error": None
        }
    except Exception as e:
        return {
            "installed": False,
            "total_containers": 0,
            "running_containers": 0,
            "stopped_containers": 0,
            "containers": [],
            "error": str(e)
        }


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get(
    "/",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the operational status of the monitoring service."
)
def health():
    return {"status": "healthy"}


@app.get(
    "/data",
    response_model=SystemMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get VPS system metrics",
    description="""
Collects and returns comprehensive real-time system metrics:
- **Uptime**: System uptime duration, human-readable format, and boot time.
- **CPU**: Total utilization (%), individual per-core percentage, core count, and execution times.
- **Load Average**: Linux system load averages for 1m, 5m, and 15m.
- **Memory**: Physical RAM and Swap capacity, free, used, and percent indicators.
- **Root Storage**: Root partition (/) capacity and storage consumption.
- **Disk I/O**: Read and write bytes and operation counters.
- **Network Interfaces**: Inbound and outbound traffic bytes and packet counters per interface.
- **Sensors**: Thermal and fan readings when supported by the hardware and kernel.
- **Docker**: Daemon status, container counts, and container runtime states.
- **Top CPU Processes**: The 10 processes consuming the most CPU power.
- **Top Memory Processes**: The 10 processes consuming the most RAM.
- **Logged in Users**: Active terminal and SSH user sessions on the system.
    """
)
def get_computer_data():
    # 1. System Uptime and Boot Time
    boot_timestamp = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_timestamp)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    boot_iso = datetime.datetime.fromtimestamp(boot_timestamp, datetime.timezone.utc).isoformat()

    uptime_data = {
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": uptime_str,
        "boot_time": boot_iso
    }

    # 2. CPU Metrics (overall and per individual core)
    cpu_data = {
        "total_percent": psutil.cpu_percent(interval=None),
        "per_core_percent": psutil.cpu_percent(interval=None, percpu=True),
        "core_count": psutil.cpu_count(logical=True) or 1,
        "times": psutil.cpu_times()._asdict()
    }

    # 3. Hardware Sensors (Linux vs Windows/Docker fallback)
    temperatures = {}
    if hasattr(psutil, "sensors_temperatures"):
        try:
            raw_temps = psutil.sensors_temperatures()
            if raw_temps:
                temperatures = {k: [item._asdict() for item in v] for k, v in raw_temps.items()}
        except Exception:
            temperatures = {}

    fans = {}
    if hasattr(psutil, "sensors_fans"):
        try:
            raw_fans = psutil.sensors_fans()
            if raw_fans:
                fans = {k: [item._asdict() for item in v] for k, v in raw_fans.items()}
        except Exception:
            fans = {}

    # 4. Root Storage Space
    root_path = "/" if os.name != "nt" else os.path.abspath(os.sep)
    try:
        disk_usage = psutil.disk_usage(root_path)._asdict()
    except Exception:
        disk_usage = {"total": 0, "used": 0, "free": 0, "percent": 0.0}

    # 5. Disk Read/Write I/O
    try:
        disk_io_raw = psutil.disk_io_counters()
        disk_io_data = disk_io_raw._asdict() if disk_io_raw else None
    except Exception:
        disk_io_data = None

    # 6. Load Average (1m, 5m, 15m)
    raw_load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    load_average = {
        "last_1m": round(raw_load[0], 2),
        "last_5m": round(raw_load[1], 2),
        "last_15m": round(raw_load[2], 2)
    }

    # 7. Docker Containers Overview
    docker_data = get_docker_overview()

    # 8. Processes (single iteration for both top CPU and top memory)
    all_processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            info = proc.info
            all_processes.append({
                "pid": info["pid"],
                "name": info["name"] or "unknown",
                "memory_percent": round(info.get("memory_percent") or 0.0, 2),
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_memory_processes = sorted(all_processes, key=lambda x: x["memory_percent"], reverse=True)[:10]
    top_cpu_processes = sorted(all_processes, key=lambda x: x["cpu_percent"], reverse=True)[:10]

    # 9. Network Traffic I/O
    try:
        network_stats = {k: v._asdict() for k, v in psutil.net_io_counters(pernic=True).items()}
    except Exception:
        network_stats = {}

    # 10. Active Logged-in Users (e.g. SSH sessions)
    logged_in_users = []
    try:
        for u in psutil.users():
            logged_in_users.append({
                "name": u.name,
                "terminal": u.terminal,
                "host": u.host,
                "started": u.started
            })
    except Exception:
        logged_in_users = []

    return {
        "uptime": uptime_data,
        "cpu": cpu_data,
        "load_average": load_average,
        "virtual_memory": psutil.virtual_memory()._asdict(),
        "swap_memory": psutil.swap_memory()._asdict(),
        "root_storage": disk_usage,
        "disk_io": disk_io_data,
        "network_interfaces": network_stats,
        "temperatures": temperatures,
        "fans": fans,
        "docker": docker_data,
        "top_cpu_processes": top_cpu_processes,
        "top_memory_processes": top_memory_processes,
        "logged_in_users": logged_in_users
    }
