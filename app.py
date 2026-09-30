import os
import psutil
from fastapi import FastAPI, status

from schemas import HealthResponse, SystemMetricsResponse

# ==============================================================================
# FastAPI Application Configuration
# ==============================================================================

app = FastAPI(
    title="VPS System Monitoring API",
    description="""
    A lightweight real-time telemetry and resource monitoring API for VPS and host systems.
    Exposes hardware consumption, memory, disk, network, system load, and top resource-consuming processes.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


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
    - **CPU Times**: Processing time distribution across user, kernel, and idle states.
    - **Load Average**: Linux system load averages for 1m, 5m, and 15m.
    - **Memory**: Physical RAM and Swap capacity, free, used, and percent indicators.
    - **Disk & Storage**: Mounted partitions and root partition storage consumption.
    - **Network Interfaces**: Inbound and outbound traffic bytes and packet counters per interface.
    - **Sensors**: Thermal and fan readings when supported by the hardware and kernel.
    - **Top Memory Processes**: The 10 most RAM-intensive processes running on the machine.
    - **Process Threads**: Thread breakdown for this monitoring agent.
    """
)
def get_computer_data():
    current_process = psutil.Process()
    try:
        process_threads = [t._asdict() for t in current_process.threads()]
    except Exception:
        process_threads = []

    # Safe sensor readings with fallback (Linux vs Windows/Docker)
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

    # Root storage path compatibility
    root_path = "/" if os.name != "nt" else os.path.abspath(os.sep)
    try:
        disk_usage = psutil.disk_usage(root_path)._asdict()
    except Exception:
        disk_usage = {"total": 0, "used": 0, "free": 0, "percent": 0.0}

    # Load average calculation (1m, 5m, 15m)
    raw_load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    load_average = {
        "last_1m": round(raw_load[0], 2),
        "last_5m": round(raw_load[1], 2),
        "last_15m": round(raw_load[2], 2)
    }

    # Top 10 memory-consuming processes
    top_memory_processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            info = proc.info
            top_memory_processes.append({
                "pid": info["pid"],
                "name": info["name"] or "unknown",
                "memory_percent": round(info.get("memory_percent") or 0.0, 2),
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_memory_processes.sort(key=lambda x: x["memory_percent"], reverse=True)

    # Safe network I/O
    try:
        network_stats = {k: v._asdict() for k, v in psutil.net_io_counters(pernic=True).items()}
    except Exception:
        network_stats = {}

    # Safe disk partitions
    try:
        partitions = [p._asdict() for p in psutil.disk_partitions(all=False)]
    except Exception:
        partitions = []

    return {
        "cpu_times": psutil.cpu_times()._asdict(),
        "load_average": load_average,
        "virtual_memory": psutil.virtual_memory()._asdict(),
        "swap_memory": psutil.swap_memory()._asdict(),
        "disk_partitions": partitions,
        "root_storage": disk_usage,
        "network_interfaces": network_stats,
        "temperatures": temperatures,
        "fans": fans,
        "top_memory_processes": top_memory_processes[:10],
        "process_threads": {
            "total_threads": current_process.num_threads(),
            "threads": process_threads
        }
    }
