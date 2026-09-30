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
    """System RAM utilization statistics."""
    model_config = ConfigDict(extra="allow")

    total: int = Field(
        ...,
        description="Total physical RAM installed (bytes)",
        examples=[16777216000]
    )
    available: int = Field(
        ...,
        description="Memory available immediately for new processes without swapping (bytes)",
        examples=[8388608000]
    )
    percent: float = Field(
        ...,
        description="Percentage of physical memory used (%)",
        examples=[50.0]
    )
    used: int = Field(
        ...,
        description="Memory currently occupied by running processes (bytes)",
        examples=[8388608000]
    )
    free: int = Field(
        ...,
        description="Completely unallocated physical memory (bytes)",
        examples=[4194304000]
    )


class SwapMemory(BaseModel):
    """System virtual swap memory metrics."""
    model_config = ConfigDict(extra="allow")

    total: int = Field(
        ...,
        description="Total configured swap storage space (bytes)",
        examples=[4294967296]
    )
    used: int = Field(
        ...,
        description="Swap storage space currently in use (bytes)",
        examples=[1048576000]
    )
    free: int = Field(
        ...,
        description="Available unused swap storage space (bytes)",
        examples=[3246391296]
    )
    percent: float = Field(
        ...,
        description="Percentage of swap memory used (%)",
        examples=[24.4]
    )


class DiskUsage(BaseModel):
    """Storage space capacity and consumption for the root filesystem (/)." """
    model_config = ConfigDict(extra="allow")

    total: int = Field(
        ...,
        description="Total storage capacity (bytes)",
        examples=[512110190592]
    )
    used: int = Field(
        ...,
        description="Used storage space (bytes)",
        examples=[128027547648]
    )
    free: int = Field(
        ...,
        description="Available free storage space (bytes)",
        examples=[384082642944]
    )
    percent: float = Field(
        ...,
        description="Percentage of disk capacity consumed (%)",
        examples=[25.0]
    )


class DiskIO(BaseModel):
    """Cumulative disk read and write I/O metrics."""
    model_config = ConfigDict(extra="allow")

    read_bytes: int = Field(
        ...,
        description="Total bytes read from physical storage disks",
        examples=[1073741824]
    )
    write_bytes: int = Field(
        ...,
        description="Total bytes written to physical storage disks",
        examples=[5368709120]
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


class NetworkInterfaceIO(BaseModel):
    """Cumulative network traffic statistics for a network adapter."""
    model_config = ConfigDict(extra="allow")

    bytes_sent: int = Field(
        ...,
        description="Total bytes transmitted through this interface",
        examples=[104857600]
    )
    bytes_recv: int = Field(
        ...,
        description="Total bytes received through this interface",
        examples=[524288000]
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
    started: float = Field(
        ...,
        description="UNIX timestamp marking when the session was initiated",
        examples=[1727690000.0]
    )


class SystemMetricsResponse(BaseModel):
    """Comprehensive real-time VPS telemetry schema."""
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
        description="Physical RAM capacity and utilization metrics"
    )
    swap_memory: SwapMemory = Field(
        ...,
        description="Virtual swap space capacity and utilization metrics"
    )
    root_storage: DiskUsage = Field(
        ...,
        description="Storage space usage for the root filesystem (/)"
    )
    disk_io: Optional[DiskIO] = Field(
        None,
        description="Disk input/output activity (bytes and operation counts)"
    )
    network_interfaces: Dict[str, NetworkInterfaceIO] = Field(
        ...,
        description="Network traffic I/O counters grouped by interface name"
    )
    temperatures: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hardware thermal sensor readings (available on supported Linux hardware)"
    )
    fans: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cooling fan RPM sensor readings (available on supported Linux hardware)"
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
