from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


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


class DiskPartition(BaseModel):
    """Mounted filesystem partition details."""
    model_config = ConfigDict(extra="allow")

    device: str = Field(
        ...,
        description="Device name or drive letter (e.g. /dev/sda1 or C:\\)",
        examples=["/dev/sda1"]
    )
    mountpoint: str = Field(
        ...,
        description="Path where the partition is mounted in the filesystem hierarchy",
        examples=["/"]
    )
    fstype: str = Field(
        ...,
        description="Filesystem format type (e.g. ext4, xfs, NTFS)",
        examples=["ext4"]
    )
    opts: str = Field(
        ...,
        description="Mount options applied to this partition",
        examples=["rw,relatime"]
    )


class DiskUsage(BaseModel):
    """Storage space capacity and consumption for a filesystem path."""
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


class ThreadDetail(BaseModel):
    """Thread execution metrics."""
    model_config = ConfigDict(extra="allow")

    id: int = Field(
        ...,
        description="Operating system Thread Identifier (TID)",
        examples=[1204]
    )
    user_time: float = Field(
        ...,
        description="CPU time spent executing in user mode (seconds)",
        examples=[0.12]
    )
    system_time: float = Field(
        ...,
        description="CPU time spent executing in kernel/system mode (seconds)",
        examples=[0.05]
    )


class ProcessThreads(BaseModel):
    """Active threads profile for the current API service process."""
    total_threads: int = Field(
        ...,
        description="Total number of active threads spawned by the API process",
        examples=[4]
    )
    threads: List[ThreadDetail] = Field(
        default_factory=list,
        description="Individual metrics and identifiers for each active thread"
    )


class SystemMetricsResponse(BaseModel):
    """Comprehensive real-time VPS telemetry schema."""
    cpu_times: CpuTimes = Field(
        ...,
        description="Breakdown of CPU processing times"
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
    disk_partitions: List[DiskPartition] = Field(
        ...,
        description="List of active mounted disk partitions"
    )
    root_storage: DiskUsage = Field(
        ...,
        description="Storage space usage for the root filesystem (/)"
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
    top_memory_processes: List[ProcessDetail] = Field(
        ...,
        description="Top 10 running system processes consuming the highest percentage of RAM"
    )
    process_threads: ProcessThreads = Field(
        ...,
        description="Thread count and runtime metrics for the monitoring API process"
    )
