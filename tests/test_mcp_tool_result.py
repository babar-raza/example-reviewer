"""Tests for ToolResult dataclass serialization."""
import json
import pytest
from src.mcp_tools.tools import ToolResult


class TestToolResultToDict:
    def test_success_result_includes_data(self):
        result = ToolResult(success=True, data={"count": 5, "files": ["a.md"]})
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"count": 5, "files": ["a.md"]}
        assert "error" not in d

    def test_error_result_includes_error(self):
        result = ToolResult(success=False, error="Something failed")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something failed"
        assert "data" not in d

    def test_filters_none_values(self):
        result = ToolResult(success=True)
        d = result.to_dict()
        assert d == {"success": True}
        assert "data" not in d
        assert "error" not in d


class TestToolResultToJson:
    def test_success_json_round_trip(self):
        result = ToolResult(success=True, data={"key": "value"})
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["key"] == "value"

    def test_error_json_round_trip(self):
        result = ToolResult(success=False, error="fail")
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["error"] == "fail"

    def test_complex_nested_data(self):
        result = ToolResult(success=True, data={
            "stats": {"compiled": 10, "failed": 2},
            "files": [{"path": "a.md", "examples": 3}],
            "nested": {"deep": {"value": True}},
        })
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["data"]["stats"]["compiled"] == 10
        assert parsed["data"]["files"][0]["examples"] == 3
        assert parsed["data"]["nested"]["deep"]["value"] is True
