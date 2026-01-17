"""
Tests for ResourceDetectionService.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.services.resource_detection_service import (
    ResourceDetectionService,
    ResourceInfo,
    ResourceDecision,
    TORCH_AVAILABLE,
    PYNVML_AVAILABLE,
    PSUTIL_AVAILABLE,
)


class TestResourceInfo:
    """Tests for ResourceInfo dataclass."""

    def test_default_values(self):
        """Test that ResourceInfo has sensible defaults."""
        info = ResourceInfo()
        assert info.gpu_detected is False
        assert info.gpu_name is None
        assert info.gpu_count == 0
        assert info.vram_total_mb == 0
        assert info.detection_method == "none"


class TestResourceDecision:
    """Tests for ResourceDecision dataclass."""

    def test_to_telemetry_dict(self):
        """Test conversion to telemetry dictionary."""
        decision = ResourceDecision(
            gpu_detected=True,
            vram_total_mb=8192,
            vram_used_mb=2048,
            cpu_mode=False,
            chosen_strategy="gpu_preferred",
            limits_applied={"cpu_max_percent": 90},
        )

        telemetry = decision.to_telemetry_dict()

        assert telemetry['gpu_detected'] is True
        assert telemetry['vram_total_mb'] == 8192
        assert telemetry['vram_used_mb'] == 2048
        assert telemetry['cpu_mode'] is False
        assert telemetry['chosen_strategy'] == "gpu_preferred"
        assert telemetry['limits_applied'] == {"cpu_max_percent": 90}


class TestResourceDetectionService:
    """Tests for ResourceDetectionService."""

    def test_is_available_with_libraries(self):
        """Test is_available returns True when libraries present."""
        service = ResourceDetectionService()
        # Should return True if any library is available
        assert service.is_available() == (TORCH_AVAILABLE or PYNVML_AVAILABLE or PSUTIL_AVAILABLE)

    def test_detect_resources_returns_resource_info(self):
        """Test detect_resources returns ResourceInfo."""
        service = ResourceDetectionService()
        info = service.detect_resources()

        assert isinstance(info, ResourceInfo)
        assert info.cpu_count > 0  # Should always detect CPU

    def test_detect_resources_caches_result(self):
        """Test that resource detection is cached."""
        service = ResourceDetectionService()
        info1 = service.detect_resources()
        info2 = service.detect_resources()

        assert info1 is info2

    def test_detect_resources_force_refresh(self):
        """Test force_refresh bypasses cache."""
        service = ResourceDetectionService()
        info1 = service.detect_resources()
        info2 = service.detect_resources(force_refresh=True)

        # They should be equal but not the same object
        assert info2 is not info1

    def test_make_resource_decision_cpu_only(self):
        """Test resource decision when GPU not detected."""
        service = ResourceDetectionService(
            auto_detect_vram=False,  # Disable GPU detection
        )
        decision = service.make_resource_decision()

        assert isinstance(decision, ResourceDecision)
        assert decision.cpu_mode is True  # Should be in CPU mode without GPU

    def test_make_resource_decision_with_limits(self):
        """Test resource decision applies limits correctly."""
        service = ResourceDetectionService()
        decision = service.make_resource_decision(
            cpu_max_percent=80,
            ram_max_mb=16384,
            vram_max_mb=4096,
        )

        assert decision.limits_applied['cpu_max_percent'] == 80
        assert decision.limits_applied['ram_max_mb'] == 16384
        assert decision.limits_applied['vram_max_mb'] == 4096


class TestResourceDetectionServiceWithMockedGPU:
    """Tests with mocked GPU detection."""

    @patch('src.services.resource_detection_service.TORCH_AVAILABLE', True)
    @patch('src.services.resource_detection_service.torch')
    def test_detect_via_torch(self, mock_torch):
        """Test GPU detection via PyTorch."""
        # Setup mock
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.current_device.return_value = 0

        mock_props = MagicMock()
        mock_props.name = "NVIDIA RTX 4090"
        mock_props.total_memory = 24 * 1024 * 1024 * 1024  # 24GB
        mock_torch.cuda.get_device_properties.return_value = mock_props
        mock_torch.cuda.memory_allocated.return_value = 2 * 1024 * 1024 * 1024
        mock_torch.cuda.memory_reserved.return_value = 4 * 1024 * 1024 * 1024

        service = ResourceDetectionService()
        info = service._detect_via_torch()

        assert info.gpu_detected is True
        assert info.gpu_name == "NVIDIA RTX 4090"
        assert info.vram_total_mb == 24 * 1024  # 24GB in MB

    @patch('src.services.resource_detection_service.TORCH_AVAILABLE', True)
    @patch('src.services.resource_detection_service.torch')
    def test_detect_via_torch_no_cuda(self, mock_torch):
        """Test GPU detection when CUDA not available."""
        mock_torch.cuda.is_available.return_value = False

        service = ResourceDetectionService()
        info = service._detect_via_torch()

        assert info.gpu_detected is False
        assert info.detection_error == "CUDA not available"


class TestResourceDetectionFromConfig:
    """Tests for creating service from config."""

    def test_from_config(self):
        """Test creating service from config object."""
        # Mock config object
        config = MagicMock()
        config.auto_detect_vram = True
        config.prefer_gpu_when_available = False
        config.fallback_to_cpu = True

        service = ResourceDetectionService.from_config(config)

        assert service.auto_detect_vram is True
        assert service.prefer_gpu_when_available is False
        assert service.fallback_to_cpu is True
