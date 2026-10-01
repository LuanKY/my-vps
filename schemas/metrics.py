from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UptimeInfo(BaseModel):
    """System uptime and boot time metadata."""
    uptime_seconds: int = Field(
        ...,
        description="System uptime duration in seconds",
        examples=[345600]
    )
    uptime_formatted: str = Field(
        ...,
        description="Human-readable system uptime representation",
        examples=["4d 2h 15m"]
    )
    boot_time: str = Field(
        ...,
        description="ISO 8601 timestamp of the last system boot event",
        examples=["2026-09-26T08:45:00+00:00"]
    )


class CpuTimes(BaseModel):
    """CPU execution times breakdown in seconds."""
    model_config = ConfigDict(extra="allow")

    user: float = Field(
        ...,
        description="Time spent by normal processes executing in user mode (seconds)",
        examples=[12450.5]
    )
    system: float = Field(
        ...,
        description="Time spent by processes executing in kernel mode (seconds)",
        examples=[8920.1]
    )
    idle: float = Field(
        ...,
        description="Time the CPU spent completely idle (seconds)",
        examples=[984320.0]
    )


class CpuMetrics(BaseModel):
    """Real-time CPU metrics including per-core utilization and execution breakdown."""
    total_percent: float = Field(
        ...,
        description="Overall CPU utilization percentage across all cores combined (%)",
        examples=[28.5]
    )
    per_core_percent: List[float] = Field(
        ...,
        description="Real-time CPU utilization percentage for each individual CPU core / vCPU (%)",
        examples=[[15.2, 85.0, 4.1, 12.8]]
    )
    core_count: int = Field(
        ...,
        description="Total number of logical CPU cores (vCPUs) available on the host",
        examples=[4]
    )
    times: CpuTimes = Field(
        ...,
        description="Cumulative CPU processing times distribution"
    )


class LoadAverage(BaseModel):
    """System load average representing system demand over 1, 5, and 15 minutes."""
    last_1m: float = Field(
        ...,
        description="Average system load over the past 1 minute",
        examples=[0.25]
    )
    last_5m: float = Field(
        ...,
        description="Average system load over the past 5 minutes",
        examples=[0.35]
    )
    last_15m: float = Field(
        ...,
        description="Average system load over the past 15 minutes",
        examples=[0.40]
    )


class VirtualMemory(BaseModel):
    """System RAM utilization statistics formatted for frontend presentation."""
    model_config = ConfigDict(extra="allow")

    total_gb: float = Field(
        ...,
        description="Total physical RAM installed (Gigabytes)",
        examples=[16.0]
    )
    used_gb: float = Field(
        ...,
        description="Physical RAM currently occupied by processes (Gigabytes)",
        examples=[8.2]
    )
    available_gb: float = Field(
        ...,
        description="Memory available immediately for new processes without swapping (Gigabytes)",
        examples=[7.8]
    )
    percent: float = Field(
        ...,
        description="Percentage of physical memory used (%)",
        examples=[51.25]
    )
    raw_bytes: Dict[str, Any] = Field(
        ...,
        description="Exact raw memory measurements in bytes",
        examples=[{"total": 17179869184, "used": 8804682752, "available": 8375186432, "free": 4194304000, "percent": 51.25}]
    )


class SwapMemory(BaseModel):
    """System virtual swap memory metrics formatted for frontend presentation."""
    model_config = ConfigDict(extra="allow")

    total_gb: float = Field(
        ...,
        description="Total configured swap storage space (Gigabytes)",
        examples=[4.0]
    )
    used_gb: float = Field(
        ...,
        description="Swap storage space currently in use (Gigabytes)",
        examples=[1.0]
    )
    free_gb: float = Field(
        ...,
        description="Available unused swap storage space (Gigabytes)",
        examples=[3.0]
    )
    percent: float = Field(
        ...,
        description="Percentage of swap memory used (%)",
        examples=[25.0]
    )
    raw_bytes: Dict[str, Any] = Field(
        ...,
        description="Exact raw swap space measurements in bytes",
        examples=[{"total": 4294967296, "used": 1073741824, "free": 3221225472, "percent": 25.0}]
    )


class DiskUsage(BaseModel):
    """Storage space capacity and consumption for the root filesystem (/)." """
    model_config = ConfigDict(extra="allow")

    total_gb: float = Field(
        ...,
        description="Total storage capacity (Gigabytes)",
        examples=[476.9]
    )
    used_gb: float = Field(
        ...,
        description="Used storage space (Gigabytes)",
        examples=[119.2]
    )
    free_gb: float = Field(
        ...,
        description="Available free storage space (Gigabytes)",
        examples=[357.7]
    )
    percent: float = Field(
        ...,
        description="Percentage of disk capacity consumed (%)",
        examples=[25.0]
    )
    raw_bytes: Dict[str, Any] = Field(
        ...,
        description="Exact raw disk storage measurements in bytes",
        examples=[{"total": 512110190592, "used": 128027547648, "free": 384082642944, "percent": 25.0}]
    )


class DiskIO(BaseModel):
    """Cumulative disk read and write I/O metrics."""
    model_config = ConfigDict(extra="allow")

    read_mb: float = Field(
        ...,
        description="Total data read from physical disks (Megabytes)",
        examples=[1024.0]
    )
    write_mb: float = Field(
        ...,
        description="Total data written to physical disks (Megabytes)",
        examples=[5120.0]
    )
    read_count: int = Field(
        ...,
        description="Total count of disk read operations performed",
        examples=[45120]
    )
    write_count: int = Field(
        ...,
        description="Total count of disk write operations performed",
        examples=[89400]
    )
    raw_bytes: Dict[str, Any] = Field(
        ...,
        description="Exact raw disk I/O measurements in bytes",
        examples=[{"read_bytes": 1073741824, "write_bytes": 5368709120}]
    )


class NetworkInterfaceIO(BaseModel):
    """Network traffic statistics for an interface formatted for array rendering."""
    model_config = ConfigDict(extra="allow")

    interface: str = Field(
        ...,
        description="Network adapter name (e.g. eth0, docker0)",
        examples=["eth0"]
    )
    bytes_sent_mb: float = Field(
        ...,
        description="Total data transmitted through this interface (Megabytes)",
        examples=[100.0]
    )
    bytes_recv_mb: float = Field(
        ...,
        description="Total data received through this interface (Megabytes)",
        examples=[500.0]
    )
    packets_sent: int = Field(
        ...,
        description="Total packets sent through this interface",
        examples=[45020]
    )
    packets_recv: int = Field(
        ...,
        description="Total packets received through this interface",
        examples=[89045]
    )
    raw_bytes: Dict[str, Any] = Field(
        ...,
        description="Exact raw network bytes counters",
        examples=[{"bytes_sent": 104857600, "bytes_recv": 524288000}]
    )


class ProcessDetail(BaseModel):
    """Process execution profile and resource consumption."""
    pid: int = Field(
        ...,
        description="Operating system Process Identifier (PID)",
        examples=[1042]
    )
    name: str = Field(
        ...,
        description="Executable name or process binary",
        examples=["dockerd"]
    )
    memory_percent: float = Field(
        ...,
        description="Percentage of total system RAM utilized by this process (%)",
        examples=[12.45]
    )
    cpu_percent: float = Field(
        ...,
        description="CPU utilization percentage attributed to this process (%)",
        examples=[1.20]
    )


class LoggedInUser(BaseModel):
    """Details of active user sessions (e.g. SSH logins)."""
    model_config = ConfigDict(extra="allow")

    name: str = Field(
        ...,
        description="System account username",
        examples=["ubuntu"]
    )
    terminal: Optional[str] = Field(
        None,
        description="Terminal session identifier (e.g. pts/0)",
        examples=["pts/0"]
    )
    host: Optional[str] = Field(
        None,
        description="Remote client IP address or hostname",
        examples=["198.51.100.1"]
    )
    started_at: str = Field(
        ...,
        description="ISO 8601 timestamp marking when the session was initiated",
        examples=["2026-09-29T14:30:00+00:00"]
    )


class ContainerInfo(BaseModel):
    """Summary of an individual Docker container."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(
        ...,
        description="Short container ID (12 characters)",
        examples=["a1b2c3d4e5f6"]
    )
    name: str = Field(
        ...,
        description="Container name",
        examples=["postgres-db"]
    )
    image: str = Field(
        ...,
        description="Docker image tag or repository used",
        examples=["postgres:16-alpine"]
    )
    status: str = Field(
        ...,
        description="Human-readable status string (e.g. 'Up 2 hours', 'Exited (0)')",
        examples=["Up 2 hours"]
    )
    state: str = Field(
        ...,
        description="Lifecycle state (e.g. running, exited, restarting, paused)",
        examples=["running"]
    )
    created: Optional[str] = Field(
        None,
        description="Creation ISO 8601 timestamp",
        examples=["2026-09-28T12:00:00Z"]
    )
    ports: Dict[str, Any] = Field(
        default_factory=dict,
        description="Container port bindings mapped to the host"
    )


class DockerSummary(BaseModel):
    """Counter summary of Docker containers for dashboard cards."""
    total: int = Field(0, description="Total number of existing containers", examples=[5])
    running: int = Field(0, description="Number of currently active containers", examples=[4])
    stopped: int = Field(0, description="Number of stopped/exited containers", examples=[1])


class DockerOverview(BaseModel):
    """Status and metrics of Docker daemon and all hosted containers."""
    model_config = ConfigDict(extra="allow")

    is_running: bool = Field(
        ...,
        description="Indicates whether the Docker daemon is running and reachable via socket",
        examples=[True]
    )
    summary: DockerSummary = Field(
        default_factory=DockerSummary,
        description="Container counter summary"
    )
    containers: List[ContainerInfo] = Field(
        default_factory=list,
        description="List of all detected containers and their details"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if Docker socket connection failed",
        examples=[None]
    )


class SystemMetricsResponse(BaseModel):
    """Comprehensive real-time VPS telemetry schema formatted for frontend dashboards."""
    uptime: UptimeInfo = Field(
        ...,
        description="System uptime duration, formatted text, and boot timestamp"
    )
    cpu: CpuMetrics = Field(
        ...,
        description="Real-time CPU metrics, individual per-core usage, and core count"
    )
    load_average: LoadAverage = Field(
        ...,
        description="System load average measured over 1, 5, and 15-minute intervals"
    )
    virtual_memory: VirtualMemory = Field(
        ...,
        description="Physical RAM capacity and utilization metrics in GB and percentage"
    )
    swap_memory: SwapMemory = Field(
        ...,
        description="Virtual swap space capacity and utilization metrics in GB and percentage"
    )
    root_storage: DiskUsage = Field(
        ...,
        description="Storage space usage for the root filesystem (/) in GB and percentage"
    )
    disk_io: Optional[DiskIO] = Field(
        None,
        description="Disk input/output activity in MB and operation counts"
    )
    network_interfaces: List[NetworkInterfaceIO] = Field(
        ...,
        description="List of network adapters with traffic metrics formatted for array mapping"
    )
    temperatures: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hardware thermal sensor readings (available on supported Linux hardware)"
    )
    fans: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cooling fan RPM sensor readings (available on supported Linux hardware)"
    )
    docker: DockerOverview = Field(
        ...,
        description="Docker engine status, container summary, and container list"
    )
    top_cpu_processes: List[ProcessDetail] = Field(
        ...,
        description="Top 10 running system processes consuming the highest percentage of CPU"
    )
    top_memory_processes: List[ProcessDetail] = Field(
        ...,
        description="Top 10 running system processes consuming the highest percentage of RAM"
    )
    logged_in_users: List[LoggedInUser] = Field(
        default_factory=list,
        description="Active terminal/SSH user sessions currently established on the VPS"
    )
    server_name: Optional[str] = Field(
        default="MyVPS",
        description="Custom display name or hostname for the VPS instance",
        examples=["Production VPS"]
    )

