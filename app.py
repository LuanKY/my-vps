import asyncio
import base64
import datetime
import json
import os
import secrets
import time
from typing import Optional

import docker
import psutil
from fastapi import FastAPI, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from schemas import HealthResponse, SystemMetricsResponse

# ==============================================================================
# Environment Configuration & Basic Auth Settings
# ==============================================================================

SERVER_NAME = os.getenv("SERVER_NAME", "MyVPS").strip() or "MyVPS"
UPDATE_INTERVAL = float(os.getenv("UPDATE_INTERVAL", "3.0"))
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "").strip()
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "").strip()
AUTH_ENABLED = bool(AUTH_USERNAME and AUTH_PASSWORD)
SESSION_TOKENS = set()

PUBLIC_PATHS = {
    "/health",
    "/favicon.ico",
    "/manifest.json",
    "/manifest.webmanifest",
    "/sw.js",
    "/dashboard/manifest.json",
    "/dashboard/manifest.webmanifest",
    "/dashboard/sw.js",
    "/dashboard/favicon.ico",
    "/api/config",
}


def verify_basic_credentials(auth_header: Optional[str]) -> bool:
    """Validates HTTP Basic Auth credentials using constant-time string comparison."""
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        encoded_creds = auth_header.split(" ", 1)[1].strip()
        decoded = base64.b64decode(encoded_creds).decode("utf-8")
        if ":" not in decoded:
            return False
        username, password = decoded.split(":", 1)
        return secrets.compare_digest(username, AUTH_USERNAME) and secrets.compare_digest(password, AUTH_PASSWORD)
    except Exception:
        return False


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

# Optional Basic Auth Middleware for HTTP endpoints and Static Dashboard
if AUTH_ENABLED:
    @app.middleware("http")
    async def basic_auth_middleware(request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/dashboard/icons/"):
            return await call_next(request)

        session_token = request.cookies.get("myvps_session")

        if session_token and session_token in SESSION_TOKENS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not verify_basic_credentials(auth_header):
            return Response(
                content="Unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": f'Basic realm="{SERVER_NAME}"'}
            )

        session_token = secrets.token_urlsafe(32)
        SESSION_TOKENS.add(session_token)

        response = await call_next(request)

        response.set_cookie(
            key="myvps_session",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400
        )

        return response


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
def health():
    return {"status": "healthy"}


@app.get(
    "/",
    summary="Root endpoint",
    description="Redirects to the dashboard.",
    include_in_schema=False
)
def root_endpoint():
    return RedirectResponse(url="/dashboard/")




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
    root_path = "/host/root" if os.path.exists("/host/root") else ("/" if os.name != "nt" else os.path.abspath(os.sep))
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
        "logged_in_users": logged_in_users,
        "server_name": SERVER_NAME,
        "update_interval": UPDATE_INTERVAL
    }


@app.websocket("/ws/data")
async def websocket_system_metrics(
    websocket: WebSocket,
    interval: Optional[float] = Query(None, ge=0.5, le=60.0, description="Interval in seconds between metric updates"),
    auth: Optional[str] = Query(None, description="Optional base64 basic auth string for WebSocket clients")
):
    """
    WebSocket endpoint for real-time VPS telemetry streaming.
    Serializes and delivers metrics validated against SystemMetricsResponse.
    """
    if AUTH_ENABLED:
        auth_header = websocket.headers.get("authorization")
        is_authenticated = verify_basic_credentials(auth_header)

        if not is_authenticated and auth:
            is_authenticated = verify_basic_credentials(f"Basic {auth}")

        if not is_authenticated:
            session_token = websocket.cookies.get("myvps_session")
            is_authenticated = bool(session_token and session_token in SESSION_TOKENS)

        if not is_authenticated:
            await websocket.close(code=1008)
            return

    await websocket.accept()
    sleep_interval = interval if interval is not None else UPDATE_INTERVAL
    try:
        while True:
            raw_metrics = await asyncio.to_thread(get_computer_data)
            metrics_payload = SystemMetricsResponse(**raw_metrics).model_dump(mode="json")
            await websocket.send_json(metrics_payload)
            await asyncio.sleep(sleep_interval)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass



# ==============================================================================
# Static Frontend Files Mount (Single-port deployment) & PWA Endpoints
# ==============================================================================

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")


@app.get("/api/config", include_in_schema=False)
def get_config():
    """Returns server runtime configuration metadata."""
    return {
        "server_name": SERVER_NAME,
        "update_interval": UPDATE_INTERVAL
    }


def build_manifest_payload():
    short_name = SERVER_NAME if len(SERVER_NAME) <= 12 else SERVER_NAME[:12].strip()
    return {
        "name": SERVER_NAME,
        "short_name": short_name,
        "description": f"{SERVER_NAME} - Real-time VPS Monitoring & Telemetry Dashboard",
        "start_url": "/dashboard/",
        "scope": "/dashboard/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0b0d11",
        "theme_color": "#0b0d11",
        "icons": [
            {
                "src": "/dashboard/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/dashboard/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/dashboard/icons/maskable-icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/dashboard/icons/maskable-icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            }
        ],
        "categories": ["utilities", "productivity", "developer"]
    }


@app.get("/manifest.webmanifest", include_in_schema=False)
@app.head("/manifest.webmanifest", include_in_schema=False)
@app.get("/manifest.json", include_in_schema=False)
@app.head("/manifest.json", include_in_schema=False)
@app.get("/dashboard/manifest.webmanifest", include_in_schema=False)
@app.head("/dashboard/manifest.webmanifest", include_in_schema=False)
@app.get("/dashboard/manifest.json", include_in_schema=False)
@app.head("/dashboard/manifest.json", include_in_schema=False)
def get_pwa_manifest():
    manifest_data = build_manifest_payload()
    return Response(
        content=json.dumps(manifest_data, ensure_ascii=False),
        media_type="application/manifest+json"
    )


@app.get("/favicon.ico", include_in_schema=False)
@app.head("/favicon.ico", include_in_schema=False)
def get_favicon_root():
    fav_path = os.path.join(frontend_dir, "icons", "favicon.ico")
    if os.path.exists(fav_path):
        return FileResponse(fav_path, media_type="image/x-icon")
    return Response(status_code=404)


@app.get("/sw.js", include_in_schema=False)
@app.head("/sw.js", include_in_schema=False)
def get_service_worker_root():
    sw_path = os.path.join(frontend_dir, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"}
        )
    return Response(status_code=404)



if os.path.exists(frontend_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="frontend_dashboard")

    @app.get("/ui", include_in_schema=False)
    def redirect_to_dashboard():
        return RedirectResponse(url="/dashboard/")


