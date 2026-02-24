"""
LLM Provider Abstraction

Provides an abstract base class and implementations for mock/live LLM access.
The factory function returns the appropriate provider based on EVERCRED_MOCK_MODE.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
import json

from config import MOCK_MODE, LLM_MODEL

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def query(self, prompt: str, system: str = "") -> str:
        """
        Query the LLM with a prompt.

        Args:
            prompt: The user prompt
            system: The system prompt

        Returns:
            The LLM's response as a string
        """
        pass

    @abstractmethod
    def get_tokens_used(self) -> int:
        """Get total tokens used in this session."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing without Claude API calls.

    Returns canned responses based on pattern matching in the prompt.
    Simulates realistic token counts and small delays.
    """

    def __init__(self):
        self.total_tokens_used = 0
        # Import here to avoid circular dependency
        from llm.mock_responses import get_mock_llm_response, estimate_mock_tokens
        self._get_response = get_mock_llm_response
        self._estimate_tokens = estimate_mock_tokens

    async def query(self, prompt: str, system: str = "") -> str:
        """
        Query the mock LLM.

        Args:
            prompt: The user prompt
            system: The system prompt

        Returns:
            JSON response string
        """
        import asyncio
        import random

        logger.info("LLM: Mock query: prompt_len=%d system_len=%d", len(prompt), len(system))

        # Simulate realistic latency (100-300ms)
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Track token usage
        tokens = self._estimate_tokens(prompt, system)
        self.total_tokens_used += tokens

        response = self._get_response(prompt, system)
        logger.info("LLM: Mock response: tokens=%d length=%d", tokens, len(response))
        logger.debug("LLM: Mock response preview: %.200s", response)
        return response

    def get_tokens_used(self) -> int:
        """Get total tokens used in this session."""
        return self.total_tokens_used

    def reset_tokens(self):
        """Reset token counter."""
        self.total_tokens_used = 0


class LiveLLMProvider(LLMProvider):
    """
    Live LLM provider using Claude via claude_agent_sdk.

    Authenticates via Claude Code credentials at ~/.claude/.credentials.json.
    No separate API key needed.
    """

    def __init__(self, model: str = LLM_MODEL):
        self.model = model
        self.total_tokens_used = 0

    async def query(self, prompt: str, system: str = "") -> str:
        """
        Query Claude via the SDK.

        Args:
            prompt: The user prompt
            system: The system prompt

        Returns:
            The LLM's response as a string
        """
        from claude_agent_sdk import (
            query as sdk_query,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            ResultMessage,
        )
        from claude_agent_sdk._errors import ProcessError

        logger.info("LLM: Live query: model=%s prompt_len=%d system_len=%d", self.model, len(prompt), len(system))

        def stderr_cb(line: str) -> None:
            logger.warning("[Claude CLI stderr] %s", line)

        options = ClaudeAgentOptions(
            system_prompt=system,
            model=self.model,
            permission_mode="bypassPermissions",
            max_turns=1,
            stderr=stderr_cb,
        )
        chunks: list[str] = []
        try:
            async for message in sdk_query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
                elif isinstance(message, ResultMessage):
                    if getattr(message, "is_error", False):
                        err_msg = getattr(message, "result", None) or "".join(chunks)
                        logger.error("[Claude CLI error] %s", err_msg)
        except ProcessError as e:
            actual = "".join(chunks).strip() if chunks else None
            if actual:
                logger.error("[Claude CLI exit %d] %s", e.exit_code, actual)
                raise RuntimeError(f"Claude CLI failed: {actual}") from e
            raise
        response_text = "".join(chunks)
        input_approx = len(prompt) // 4 + len(system) // 4
        output_approx = len(response_text) // 4
        self.total_tokens_used += input_approx + output_approx
        logger.info("LLM: Live response: tokens=%d length=%d", input_approx + output_approx, len(response_text))
        logger.debug("LLM: Live response preview: %.200s", response_text)
        return response_text

    def get_tokens_used(self) -> int:
        """Get total tokens used in this session."""
        return self.total_tokens_used


class LLMError(Exception):
    """Custom exception for LLM errors."""

    def __init__(
        self,
        message: str,
        error_type: str,
        suggestion: str = "",
        recoverable: bool = False
    ):
        super().__init__(message)
        self.error_type = error_type
        self.suggestion = suggestion
        self.recoverable = recoverable


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the appropriate LLM provider.

    Returns:
        MockLLMProvider if MOCK_MODE is True, else LiveLLMProvider
    """
    if MOCK_MODE:
        logger.info("LLM: Using MockLLMProvider")
        return MockLLMProvider()
    else:
        logger.info("LLM: Using LiveLLMProvider (model=%s)", LLM_MODEL)
        return LiveLLMProvider()
