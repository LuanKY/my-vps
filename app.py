import asyncio
import datetime
import os
import time
import docker
import psutil
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles

from schemas import HealthResponse, SystemMetricsResponse

# Initialize psutil baseline for non-blocking CPU percent measurements
psutil.cpu_percent(interval=None, percpu=True)

# ==============================================================================
# Helper Functions for Unit Conversion
# ==============================================================================

def bytes_to_gb(num_bytes: int) -> float:
    """Converts bytes to Gigabytes rounded to two decimal places."""
    return round(num_bytes / (1024 ** 3), 2)


def bytes_to_mb(num_bytes: int) -> float:
    """Converts bytes to Megabytes rounded to two decimal places."""
    return round(num_bytes / (1024 ** 2), 2)


def get_network_interfaces():
    """Collects network interfaces, attempting to read host /proc/net/dev if mounted in container, with psutil fallback."""
    host_net_path = "/host/proc/net/dev"
    if os.path.exists(host_net_path):
        try:
            interfaces = []
            with open(host_net_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for line in lines[2:]:
                parts = line.strip().split(":")
                if len(parts) != 2:
                    continue
                iface_name = parts[0].strip()
                data = parts[1].split()
                if len(data) >= 10:
                    rx_bytes = int(data[0])
                    rx_packets = int(data[1])
                    tx_bytes = int(data[8])
                    tx_packets = int(data[9])
                    interfaces.append({
                        "interface": iface_name,
                        "bytes_sent_mb": bytes_to_mb(tx_bytes),
                        "bytes_recv_mb": bytes_to_mb(rx_bytes),
                        "packets_sent": tx_packets,
                        "packets_recv": rx_packets,
                        "raw_bytes": {
                            "bytes_sent": tx_bytes,
                            "bytes_recv": rx_bytes
                        }
                    })
            if interfaces:
                return interfaces
        except Exception:
            pass

    interfaces = []
    try:
        for iface_name, net_stat in psutil.net_io_counters(pernic=True).items():
            interfaces.append({
                "interface": iface_name,
                "bytes_sent_mb": bytes_to_mb(net_stat.bytes_sent),
                "bytes_recv_mb": bytes_to_mb(net_stat.bytes_recv),
                "packets_sent": net_stat.packets_sent,
                "packets_recv": net_stat.packets_recv,
                "raw_bytes": {
                    "bytes_sent": net_stat.bytes_sent,
                    "bytes_recv": net_stat.bytes_recv
                }
            })
    except Exception:
        interfaces = []
    return interfaces


def get_docker_overview():
    """Collects Docker daemon status and a structured container summary for frontend cards."""
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
            "is_running": True,
            "summary": {
                "total": len(containers),
                "running": running_count,
                "stopped": stopped_count
            },
            "containers": containers,
            "error": None
        }
    except Exception as e:
        return {
            "is_running": False,
            "summary": {
                "total": 0,
                "running": 0,
                "stopped": 0
            },
            "containers": [],
            "error": str(e)
        }


# ==============================================================================
# FastAPI Application Configuration
# ==============================================================================

app = FastAPI(
    title="VPS System Monitoring API",
    description="""
A lightweight real-time telemetry and resource monitoring API for VPS and host systems.
Exposes CPU, memory, swap, root storage, disk I/O, network, load average,
uptime, Docker container summary, top CPU/memory processes, and active user sessions.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the operational status of the monitoring service."
)
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
Collects and returns comprehensive real-time system metrics formatted for frontend dashboards:
- **Uptime**: System uptime duration, formatted text, and boot time.
- **CPU**: Total utilization (%), individual per-core percentage, core count, and execution times.
- **Load Average**: Linux system load averages for 1m, 5m, and 15m.
- **Memory**: Physical RAM and Swap formatted in GB, percent, and raw bytes.
- **Root Storage**: Root partition (/) capacity and storage consumption in GB and percent.
- **Disk I/O**: Read and write data in Megabytes (MB) and operation counters.
- **Network Interfaces**: List of network adapters with traffic in Megabytes (MB).
- **Sensors**: Thermal and fan readings when supported by the hardware and kernel.
- **Docker**: Daemon status, container counts summary, and container runtime states.
- **Top CPU Processes**: The 10 processes consuming the most CPU power.
- **Top Memory Processes**: The 10 processes consuming the most RAM.
- **Logged in Users**: Active terminal and SSH user sessions on the system with ISO timestamps.
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

    # 4. Virtual Memory (RAM) formatted in GB and percentage
    vm = psutil.virtual_memory()
    virtual_memory_data = {
        "total_gb": bytes_to_gb(vm.total),
        "used_gb": bytes_to_gb(vm.used),
        "available_gb": bytes_to_gb(vm.available),
        "percent": round(vm.percent, 2),
        "raw_bytes": vm._asdict()
    }

    # 5. Swap Memory formatted in GB and percentage
    sm = psutil.swap_memory()
    swap_memory_data = {
        "total_gb": bytes_to_gb(sm.total),
        "used_gb": bytes_to_gb(sm.used),
        "free_gb": bytes_to_gb(sm.free),
        "percent": round(sm.percent, 2),
        "raw_bytes": sm._asdict()
    }

    # 6. Root Storage Space formatted in GB and percentage
    root_path = "/" if os.name != "nt" else os.path.abspath(os.sep)
    try:
        du = psutil.disk_usage(root_path)
        disk_usage_data = {
            "total_gb": bytes_to_gb(du.total),
            "used_gb": bytes_to_gb(du.used),
            "free_gb": bytes_to_gb(du.free),
            "percent": round(du.percent, 2),
            "raw_bytes": du._asdict()
        }
    except Exception:
        disk_usage_data = {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent": 0.0,
            "raw_bytes": {}
        }

    # 7. Disk Read/Write I/O formatted in Megabytes (MB)
    try:
        dio = psutil.disk_io_counters()
        if dio:
            disk_io_data = {
                "read_mb": bytes_to_mb(dio.read_bytes),
                "write_mb": bytes_to_mb(dio.write_bytes),
                "read_count": dio.read_count,
                "write_count": dio.write_count,
                "raw_bytes": {
                    "read_bytes": dio.read_bytes,
                    "write_bytes": dio.write_bytes
                }
            }
        else:
            disk_io_data = None
    except Exception:
        disk_io_data = None

    # 8. Load Average (1m, 5m, 15m)
    raw_load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    load_average = {
        "last_1m": round(raw_load[0], 2),
        "last_5m": round(raw_load[1], 2),
        "last_15m": round(raw_load[2], 2)
    }

    # 9. Docker Containers Overview
    docker_data = get_docker_overview()

    # 10. Processes (single iteration for both top CPU and top memory)
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

    # 11. Network Traffic I/O formatted as an array for easy frontend mapping
    network_interfaces_list = get_network_interfaces()

    # 12. Active Logged-in Users with ISO timestamps
    logged_in_users = []
    try:
        for u in psutil.users():
            session_iso = datetime.datetime.fromtimestamp(u.started, datetime.timezone.utc).isoformat() if u.started else ""
            logged_in_users.append({
                "name": u.name,
                "terminal": u.terminal,
                "host": u.host,
                "started_at": session_iso
            })
    except Exception:
        logged_in_users = []

    return {
        "uptime": uptime_data,
        "cpu": cpu_data,
        "load_average": load_average,
        "virtual_memory": virtual_memory_data,
        "swap_memory": swap_memory_data,
        "root_storage": disk_usage_data,
        "disk_io": disk_io_data,
        "network_interfaces": network_interfaces_list,
        "temperatures": temperatures,
        "fans": fans,
        "docker": docker_data,
        "top_cpu_processes": top_cpu_processes,
        "top_memory_processes": top_memory_processes,
        "logged_in_users": logged_in_users
    }


@app.websocket("/ws/data")
async def websocket_system_metrics(
    websocket: WebSocket,
    interval: float = Query(3.0, ge=0.5, le=60.0, description="Interval in seconds between metric updates")
):
    """
    WebSocket endpoint for real-time VPS telemetry streaming.
    Serializes and delivers metrics validated against SystemMetricsResponse.
    """
    await websocket.accept()
    try:
        while True:
            raw_metrics = await asyncio.to_thread(get_computer_data)
            metrics_payload = SystemMetricsResponse(**raw_metrics).model_dump(mode="json")
            await websocket.send_json(metrics_payload)
            await asyncio.sleep(interval)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


# ==============================================================================
# Static Frontend Files Mount (Single-port deployment)
# ==============================================================================

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="frontend_dashboard")
    # Redireciona a raiz "/" para o dashboard se chamado via navegador (HTML)
    @app.get("/ui", include_in_schema=False)
    def redirect_to_dashboard():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard/")

