"""Conformance tests for LLM adapters.

Verifies that all adapter classes inherit from BaseLLMAdapter (the abstract base
class at llm_adapters/base.py:302) and that BaseLLMAdapter itself is abstract.

This test exists to prevent regressions where a new adapter is added that
bypasses the shared ABC contract (token counting, cost estimation, constitutional
validation, health checks, etc.).
"""

from __future__ import annotations

import inspect

from enhanced_agent_bus.llm_adapters.anthropic_adapter import AnthropicAdapter
from enhanced_agent_bus.llm_adapters.azure_openai_adapter import AzureOpenAIAdapter
from enhanced_agent_bus.llm_adapters.base import BaseLLMAdapter
from enhanced_agent_bus.llm_adapters.bedrock_adapter import BedrockAdapter
from enhanced_agent_bus.llm_adapters.huggingface_adapter import HuggingFaceAdapter
from enhanced_agent_bus.llm_adapters.openai_adapter import OpenAIAdapter
from enhanced_agent_bus.llm_adapters.openclaw_adapter import OpenClawAdapter
from enhanced_agent_bus.llm_adapters.xai_adapter import XAIAdapter


def test_bedrock_is_base_llm_adapter() -> None:
    assert issubclass(BedrockAdapter, BaseLLMAdapter)


def test_anthropic_is_base_llm_adapter() -> None:
    assert issubclass(AnthropicAdapter, BaseLLMAdapter)


def test_openai_is_base_llm_adapter() -> None:
    assert issubclass(OpenAIAdapter, BaseLLMAdapter)


def test_azure_openai_is_base_llm_adapter() -> None:
    assert issubclass(AzureOpenAIAdapter, BaseLLMAdapter)


def test_huggingface_is_base_llm_adapter() -> None:
    assert issubclass(HuggingFaceAdapter, BaseLLMAdapter)


def test_openclaw_is_base_llm_adapter() -> None:
    assert issubclass(OpenClawAdapter, BaseLLMAdapter)


def test_xai_is_base_llm_adapter() -> None:
    # XAIAdapter inherits transitively via OpenAIAdapter.
    assert issubclass(XAIAdapter, BaseLLMAdapter)


def test_base_llm_adapter_is_abstract() -> None:
    assert inspect.isabstract(BaseLLMAdapter)
