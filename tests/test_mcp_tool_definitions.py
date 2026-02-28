"""Tests for MCP tool definition integrity and schema-method alignment."""
import inspect
import pytest
from src.mcp_tools.tools import TOOL_DEFINITIONS, ExampleReviewerTools
from src.mcp_tools.server import MCPServer


# Extract tool names from each source
DEFINED_TOOL_NAMES = {d["name"] for d in TOOL_DEFINITIONS}

# Methods on ExampleReviewerTools that are actual tools (public, not __init__, not orchestrator property)
_SKIP_METHODS = {"orchestrator"}  # property, not a tool
TOOL_METHOD_NAMES = {
    name for name, method in inspect.getmembers(ExampleReviewerTools, predicate=inspect.isfunction)
    if not name.startswith("_") and name not in _SKIP_METHODS
}

# Build a lookup: tool name -> definition
TOOL_DEF_LOOKUP = {d["name"]: d for d in TOOL_DEFINITIONS}


class TestRegistrationCompleteness:
    """Every tool method must have a definition and handler, and vice versa."""

    def test_every_method_has_definition(self):
        """Every public method on ExampleReviewerTools should have a TOOL_DEFINITIONS entry."""
        missing = TOOL_METHOD_NAMES - DEFINED_TOOL_NAMES
        assert not missing, f"Methods missing from TOOL_DEFINITIONS: {missing}"

    def test_every_definition_has_method(self):
        """Every TOOL_DEFINITIONS entry should have a corresponding method."""
        missing = DEFINED_TOOL_NAMES - TOOL_METHOD_NAMES
        assert not missing, f"TOOL_DEFINITIONS entries without methods: {missing}"

    def test_every_method_has_handler(self):
        """Every tool method should be registered in MCPServer._tool_handlers."""
        # We can't easily access _tool_handlers without instantiation,
        # but we can check the source code pattern
        server_src = inspect.getsource(MCPServer.__init__)
        for name in TOOL_METHOD_NAMES:
            assert f'"{name}"' in server_src, f"Method '{name}' not registered in _tool_handlers"

    def test_no_extra_handlers(self):
        """No handler should exist without a corresponding method."""
        server_src = inspect.getsource(MCPServer.__init__)
        # Extract handler names from source pattern: "name": self.tools.name
        import re
        handler_names = set(re.findall(r'"(\w+)":\s*self\.tools\.\w+', server_src))
        extra = handler_names - TOOL_METHOD_NAMES
        assert not extra, f"Handlers without methods: {extra}"


class TestSchemaIntegrity:
    """Every tool definition must have proper JSON Schema structure."""

    @pytest.mark.parametrize("tool_def", TOOL_DEFINITIONS, ids=lambda d: d["name"])
    def test_has_required_fields(self, tool_def):
        """Each definition must have name, description, inputSchema."""
        assert "name" in tool_def
        assert "description" in tool_def
        assert "inputSchema" in tool_def
        assert isinstance(tool_def["description"], str)
        assert len(tool_def["description"]) > 0

    @pytest.mark.parametrize("tool_def", TOOL_DEFINITIONS, ids=lambda d: d["name"])
    def test_input_schema_structure(self, tool_def):
        """Each inputSchema must have type=object and properties dict."""
        schema = tool_def["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert isinstance(schema["properties"], dict)

    @pytest.mark.parametrize("tool_def", TOOL_DEFINITIONS, ids=lambda d: d["name"])
    def test_property_types_are_valid(self, tool_def):
        """All property types must be valid JSON Schema types."""
        valid_types = {"string", "integer", "boolean", "number", "array", "object"}
        for prop_name, prop_def in tool_def["inputSchema"]["properties"].items():
            assert "type" in prop_def, f"Property '{prop_name}' in tool '{tool_def['name']}' missing 'type'"
            assert prop_def["type"] in valid_types, (
                f"Property '{prop_name}' in tool '{tool_def['name']}' has invalid type '{prop_def['type']}'"
            )

    @pytest.mark.parametrize("tool_def", TOOL_DEFINITIONS, ids=lambda d: d["name"])
    def test_required_is_subset_of_properties(self, tool_def):
        """If required array exists, all entries must be in properties."""
        schema = tool_def["inputSchema"]
        if "required" in schema:
            props = set(schema["properties"].keys())
            required = set(schema["required"])
            missing = required - props
            assert not missing, f"Required fields not in properties for '{tool_def['name']}': {missing}"


class TestSchemaMethodAlignment:
    """Tool definition schemas must match their corresponding method signatures."""

    @pytest.mark.parametrize("tool_name", sorted(TOOL_METHOD_NAMES))
    def test_schema_covers_all_method_params(self, tool_name):
        """Every method parameter (except self) must appear in the schema properties."""
        method = getattr(ExampleReviewerTools, tool_name)
        sig = inspect.signature(method)
        method_params = {
            name for name, param in sig.parameters.items()
            if name != "self"
        }

        if tool_name not in TOOL_DEF_LOOKUP:
            pytest.fail(f"Tool '{tool_name}' has no TOOL_DEFINITIONS entry")

        schema_props = set(TOOL_DEF_LOOKUP[tool_name]["inputSchema"]["properties"].keys())
        missing = method_params - schema_props
        assert not missing, (
            f"Tool '{tool_name}': method params {missing} not in schema properties"
        )

    @pytest.mark.parametrize("tool_name", sorted(DEFINED_TOOL_NAMES))
    def test_schema_has_no_extra_properties(self, tool_name):
        """Schema properties should not contain entries that don't exist in the method."""
        if tool_name not in TOOL_METHOD_NAMES:
            pytest.skip(f"Tool '{tool_name}' has no method (covered by registration test)")

        method = getattr(ExampleReviewerTools, tool_name)
        sig = inspect.signature(method)
        method_params = {
            name for name, param in sig.parameters.items()
            if name != "self"
        }

        schema_props = set(TOOL_DEF_LOOKUP[tool_name]["inputSchema"]["properties"].keys())
        extra = schema_props - method_params
        assert not extra, (
            f"Tool '{tool_name}': schema has extra properties {extra} not in method"
        )
