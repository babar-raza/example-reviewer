"""
Resource Detection Service for Example Reviewer Pipeline.
Detects GPU/VRAM availability and logs resource decisions to telemetry.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import GPU detection libraries - graceful degradation
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
    logger.debug("PyTorch not available - GPU detection via torch disabled")

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    logger.debug("pynvml not available - GPU detection via NVML disabled")

# psutil for CPU/RAM detection (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.debug("psutil not available - CPU/RAM monitoring limited")


@dataclass
class ResourceInfo:
    """Detected resource information."""
    gpu_detected: bool = False
    gpu_name: Optional[str] = None
    gpu_count: int = 0
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    cpu_count: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    detection_method: str = "none"
    detection_error: Optional[str] = None


@dataclass
class ResourceDecision:
    """
    Resource allocation decision for telemetry.

    Matches the spec telemetry.resource_decisions schema:
    - gpu_detected: boolean
    - vram_total_mb: integer
    - vram_used_mb: integer
    - cpu_mode: boolean
    - chosen_strategy: string
    - limits_applied: object
    """
    gpu_detected: bool
    vram_total_mb: int
    vram_used_mb: int
    cpu_mode: bool
    chosen_strategy: str
    limits_applied: Dict[str, Any] = field(default_factory=dict)

    def to_telemetry_dict(self) -> Dict[str, Any]:
        """Convert to telemetry-compatible dictionary."""
        return {
            'gpu_detected': self.gpu_detected,
            'vram_total_mb': self.vram_total_mb,
            'vram_used_mb': self.vram_used_mb,
            'cpu_mode': self.cpu_mode,
            'chosen_strategy': self.chosen_strategy,
            'limits_applied': self.limits_applied,
        }


class ResourceDetectionService:
    """
    Service for detecting hardware resources (GPU/VRAM/CPU/RAM).

    Supports multiple detection methods with graceful fallback:
    1. PyTorch CUDA (if torch installed with CUDA support)
    2. NVML (if pynvml installed)
    3. Platform-specific (psutil for CPU/RAM)
    4. Basic (os module fallback)

    All detection failures are handled gracefully - the pipeline
    continues even if resource detection fails.
    """

    def __init__(
        self,
        auto_detect_vram: bool = True,
        prefer_gpu_when_available: bool = True,
        fallback_to_cpu: bool = True,
    ):
        """
        Initialize resource detection service.

        Args:
            auto_detect_vram: Whether to attempt VRAM detection
            prefer_gpu_when_available: Strategy to prefer GPU when available
            fallback_to_cpu: Fallback to CPU if GPU unavailable/limited
        """
        self.auto_detect_vram = auto_detect_vram
        self.prefer_gpu_when_available = prefer_gpu_when_available
        self.fallback_to_cpu = fallback_to_cpu
        self._cached_info: Optional[ResourceInfo] = None

    def is_available(self) -> bool:
        """Check if any resource detection method is available."""
        return TORCH_AVAILABLE or PYNVML_AVAILABLE or PSUTIL_AVAILABLE

    def detect_resources(self, force_refresh: bool = False) -> ResourceInfo:
        """
        Detect available hardware resources.

        Args:
            force_refresh: Force re-detection even if cached

        Returns:
            ResourceInfo with detected hardware info
        """
        if self._cached_info is not None and not force_refresh:
            return self._cached_info

        info = ResourceInfo()

        # Try GPU detection if enabled
        if self.auto_detect_vram:
            # Try PyTorch first (most common in ML environments)
            if TORCH_AVAILABLE:
                gpu_info = self._detect_via_torch()
                if gpu_info.gpu_detected:
                    info = gpu_info

            # Fallback to NVML if torch didn't find GPU
            if not info.gpu_detected and PYNVML_AVAILABLE:
                gpu_info = self._detect_via_nvml()
                if gpu_info.gpu_detected:
                    info = gpu_info

        # Always detect CPU/RAM
        info = self._detect_cpu_ram(info)

        self._cached_info = info
        return info

    def _detect_via_torch(self) -> ResourceInfo:
        """Detect GPU via PyTorch CUDA."""
        info = ResourceInfo(detection_method="torch")

        try:
            if not torch.cuda.is_available():
                info.detection_error = "CUDA not available"
                return info

            device_count = torch.cuda.device_count()
            if device_count == 0:
                info.detection_error = "No CUDA devices found"
                return info

            # Get info from first device
            device = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(device)

            # Get memory info
            total_memory = props.total_memory
            # allocated is actively used, reserved is cached
            allocated = torch.cuda.memory_allocated(device)
            reserved = torch.cuda.memory_reserved(device)

            info.gpu_detected = True
            info.gpu_name = props.name
            info.gpu_count = device_count
            info.vram_total_mb = total_memory // (1024 * 1024)
            info.vram_used_mb = allocated // (1024 * 1024)
            info.vram_free_mb = (total_memory - reserved) // (1024 * 1024)

            logger.debug(f"Detected GPU via torch: {props.name} with {info.vram_total_mb}MB VRAM")

        except Exception as e:
            info.detection_error = str(e)
            logger.debug(f"PyTorch GPU detection failed: {e}")

        return info

    def _detect_via_nvml(self) -> ResourceInfo:
        """Detect GPU via NVIDIA NVML."""
        info = ResourceInfo(detection_method="nvml")

        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            if device_count == 0:
                pynvml.nvmlShutdown()
                info.detection_error = "No NVML devices found"
                return info

            # Get info from first device
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            pynvml.nvmlShutdown()

            info.gpu_detected = True
            info.gpu_name = name.decode() if isinstance(name, bytes) else name
            info.gpu_count = device_count
            info.vram_total_mb = mem_info.total // (1024 * 1024)
            info.vram_used_mb = mem_info.used // (1024 * 1024)
            info.vram_free_mb = mem_info.free // (1024 * 1024)

            logger.debug(f"Detected GPU via NVML: {info.gpu_name} with {info.vram_total_mb}MB VRAM")

        except Exception as e:
            info.detection_error = str(e)
            logger.debug(f"NVML GPU detection failed: {e}")

        return info

    def _detect_cpu_ram(self, info: ResourceInfo) -> ResourceInfo:
        """Detect CPU and RAM info."""
        # CPU count (always available)
        info.cpu_count = os.cpu_count() or 1

        # RAM info via psutil if available
        if PSUTIL_AVAILABLE:
            try:
                mem = psutil.virtual_memory()
                info.ram_total_mb = mem.total // (1024 * 1024)
                info.ram_available_mb = mem.available // (1024 * 1024)
            except Exception as e:
                logger.debug(f"psutil RAM detection failed: {e}")

        return info

    def make_resource_decision(
        self,
        cpu_max_percent: int = 90,
        ram_max_mb: int = 0,
        vram_max_mb: int = 0,
    ) -> ResourceDecision:
        """
        Make resource allocation decision based on detected resources and limits.

        Args:
            cpu_max_percent: Maximum CPU utilization threshold
            ram_max_mb: Maximum RAM limit (0 = no limit)
            vram_max_mb: Maximum VRAM limit (0 = no limit)

        Returns:
            ResourceDecision for telemetry logging
        """
        info = self.detect_resources()

        # Determine if GPU should be used
        use_gpu = False
        strategy = "cpu_only"

        if info.gpu_detected and self.prefer_gpu_when_available:
            # Check if VRAM limit is set and if we have enough
            if vram_max_mb > 0:
                if info.vram_free_mb >= vram_max_mb:
                    use_gpu = True
                    strategy = "gpu_preferred"
                else:
                    # Not enough VRAM, fall back to CPU
                    if self.fallback_to_cpu:
                        strategy = "cpu_fallback_vram_limit"
                    else:
                        strategy = "gpu_limited"
            else:
                # No VRAM limit, use GPU
                use_gpu = True
                strategy = "gpu_available"
        elif info.gpu_detected and not self.prefer_gpu_when_available:
            strategy = "cpu_preferred"
        elif self.fallback_to_cpu:
            strategy = "cpu_fallback"

        return ResourceDecision(
            gpu_detected=info.gpu_detected,
            vram_total_mb=info.vram_total_mb,
            vram_used_mb=info.vram_used_mb,
            cpu_mode=not use_gpu,
            chosen_strategy=strategy,
            limits_applied={
                'cpu_max_percent': cpu_max_percent,
                'ram_max_mb': ram_max_mb,
                'vram_max_mb': vram_max_mb,
            },
        )

    @classmethod
    def from_config(cls, resource_detection_config) -> 'ResourceDetectionService':
        """
        Create service from ResourceDetectionConfig.

        Args:
            resource_detection_config: ResourceDetectionConfig instance

        Returns:
            ResourceDetectionService instance
        """
        return cls(
            auto_detect_vram=resource_detection_config.auto_detect_vram,
            prefer_gpu_when_available=resource_detection_config.prefer_gpu_when_available,
            fallback_to_cpu=resource_detection_config.fallback_to_cpu,
        )
