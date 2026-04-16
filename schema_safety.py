"""Schema-safety helpers for tool-facing JSON schemas.

These helpers normalize tool input schemas into a conservative subset that
works across stricter validators:
- top-level tool schemas are always objects
- reserved property names such as ``format`` are renamed
- JSON Schema combinators are stripped from tool-facing schemas
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict as ImportedJSONDict
else:
    try:
        from enhanced_agent_bus._compat.types import JSONDict as ImportedJSONDict
    except ImportError:
        ImportedJSONDict: TypeAlias = dict[str, Any]

JSONDict: TypeAlias = ImportedJSONDict

_COMBINATOR_KEYS = {"anyOf", "oneOf", "allOf"}
_SAFE_PROPERTY_RENAMES = {"format": "outputFormat"}
_ALLOWED_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}


def sanitize_schema_fragment(schema: Any) -> JSONDict:
    """Normalize a nested JSON Schema fragment into a validator-safe shape."""
    return _sanitize_schema_fragment(schema, top_level=False)


def sanitize_tool_input_schema(schema: Any) -> JSONDict:
    """Normalize a tool input schema into a validator-safe top-level object."""
    normalized = _sanitize_schema_fragment(schema, top_level=True)
    normalized.setdefault("type", "object")
    normalized.setdefault("properties", {})
    normalized.setdefault("required", [])
    normalized.setdefault("additionalProperties", False)
    return normalized


def _sanitize_schema_fragment(schema: Any, *, top_level: bool) -> JSONDict:
    if not isinstance(schema, Mapping):
        return _default_top_level_schema() if top_level else {"type": "string"}

    sanitized: JSONDict = {}
    required_names: list[str] = []
    rename_map: dict[str, str] = {}

    for key, value in schema.items():
        if key in _COMBINATOR_KEYS:
            continue
        if key == "properties":
            properties, rename_map = _sanitize_properties(value)
            sanitized["properties"] = properties
            continue
        if key == "required":
            if isinstance(value, list):
                required_names = [str(item) for item in value if isinstance(item, str)]
            continue
        if key == "items":
            sanitized["items"] = _sanitize_schema_fragment(value, top_level=False)
            continue
        if key == "type":
            normalized_type = _normalize_type(value)
            if normalized_type is not None:
                sanitized["type"] = normalized_type
            continue
        if key == "additionalProperties":
            sanitized["additionalProperties"] = bool(value)
            continue
        sanitized[key] = _clone_jsonish(value)

    if "enum" in sanitized and "type" not in sanitized:
        enum_type = _infer_enum_type(sanitized["enum"])
        if enum_type is not None:
            sanitized["type"] = enum_type

    if "properties" in sanitized:
        sanitized["type"] = "object"
        sanitized["required"] = _sanitize_required(
            required_names, sanitized["properties"], rename_map
        )
        sanitized.setdefault("additionalProperties", False)
    elif sanitized.get("type") == "array":
        sanitized["items"] = _sanitize_schema_fragment(sanitized.get("items", {}), top_level=False)

    if not top_level:
        return sanitized

    if sanitized.get("type") == "object":
        sanitized.setdefault("properties", {})
        sanitized["required"] = _sanitize_required(
            required_names, sanitized["properties"], rename_map
        )
        sanitized.setdefault("additionalProperties", False)
        return sanitized

    if sanitized:
        return _wrap_primitive_schema(sanitized)
    return _default_top_level_schema()


def _sanitize_properties(raw_properties: Any) -> tuple[JSONDict, dict[str, str]]:
    if not isinstance(raw_properties, Mapping):
        return {}, {}

    properties: JSONDict = {}
    rename_map: dict[str, str] = {}
    for raw_name, raw_schema in raw_properties.items():
        if not isinstance(raw_name, str):
            continue
        safe_name = _safe_property_name(raw_name, properties)
        rename_map[raw_name] = safe_name
        properties[safe_name] = _sanitize_schema_fragment(raw_schema, top_level=False)
    return properties, rename_map


def _safe_property_name(name: str, existing: Mapping[str, Any]) -> str:
    candidate = _SAFE_PROPERTY_RENAMES.get(name, name)
    if candidate not in existing:
        return candidate
    if candidate == name:
        return name
    suffix = 1
    while f"{candidate}{suffix}" in existing:
        suffix += 1
    return f"{candidate}{suffix}"


def _sanitize_required(
    raw_required: list[str],
    properties: Mapping[str, Any],
    rename_map: Mapping[str, str],
) -> list[str]:
    sanitized: list[str] = []
    for name in raw_required:
        safe_name = rename_map.get(name, name)
        if safe_name in properties and safe_name not in sanitized:
            sanitized.append(safe_name)
    return sanitized


def _wrap_primitive_schema(schema: JSONDict) -> JSONDict:
    return {
        "type": "object",
        "properties": {"input": schema},
        "required": ["input"],
        "additionalProperties": False,
    }


def _default_top_level_schema() -> JSONDict:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def _normalize_type(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized if normalized in _ALLOWED_TYPES else None
    return None


def _infer_enum_type(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    if all(isinstance(item, str) for item in value):
        return "string"
    if all(isinstance(item, bool) for item in value):
        return "boolean"
    if all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        return "integer"
    if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        return "number"
    return None


def _clone_jsonish(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_jsonish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_jsonish(item) for item in value]
    return value


__all__ = ["sanitize_schema_fragment", "sanitize_tool_input_schema"]
