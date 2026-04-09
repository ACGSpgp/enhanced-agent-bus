"""Tests for schema safety normalization on tool-facing JSON schemas."""

from enhanced_agent_bus.mcp_integration.server import InternalTool
from enhanced_agent_bus.mcp_integration.tool_registry import ToolInputSchema
from enhanced_agent_bus.schema_safety import (
    sanitize_schema_fragment,
    sanitize_tool_input_schema,
)
from enhanced_agent_bus.tool_documentation import (
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)


class TestSchemaSafetyHelpers:
    def test_top_level_primitive_is_wrapped_into_object(self):
        schema = sanitize_tool_input_schema({"type": "string"})
        assert schema["type"] == "object"
        assert schema["required"] == ["input"]
        assert schema["properties"]["input"]["type"] == "string"

    def test_reserved_format_property_is_renamed(self):
        schema = sanitize_tool_input_schema(
            {
                "type": "object",
                "properties": {"format": {"type": "string"}},
                "required": ["format"],
            }
        )
        assert "format" not in schema["properties"]
        assert "outputFormat" in schema["properties"]
        assert schema["required"] == ["outputFormat"]

    def test_combinators_are_removed_from_schema_fragments(self):
        schema = sanitize_schema_fragment(
            {
                "description": "value",
                "oneOf": [{"type": "string"}, {"type": "integer"}],
                "enum": ["a", "b"],
            }
        )
        assert "oneOf" not in schema
        assert schema["type"] == "string"


class TestSchemaSafetyIntegration:
    def test_tool_definition_sanitizes_openai_schema(self):
        tool = ToolDefinition(
            name="export_data",
            description="Export data",
            category=ToolCategory.UTILITY,
            parameters=[ToolParameter(name="format", type="string", description="Export format")],
        )
        schema = tool.to_openai_schema()
        assert schema["parameters"]["type"] == "object"
        assert "outputFormat" in schema["parameters"]["properties"]
        assert "format" not in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["outputFormat"]

    def test_tool_input_schema_sanitizes_server_schemas(self):
        schema = ToolInputSchema(
            type="object",
            properties={"format": {"type": "string"}},
            required=["format"],
        )
        as_dict = schema.to_dict()
        assert as_dict["type"] == "object"
        assert "outputFormat" in as_dict["properties"]
        assert as_dict["required"] == ["outputFormat"]

    def test_internal_tool_sanitizes_non_object_schema(self):
        async def _noop(args):
            return {"ok": True}

        tool = InternalTool(
            name="primitive_tool",
            description="Primitive schema tool",
            input_schema={"type": "string"},
            handler=_noop,
        )
        definition = tool.to_mcp_definition()
        assert definition["inputSchema"]["type"] == "object"
        assert definition["inputSchema"]["required"] == ["input"]
