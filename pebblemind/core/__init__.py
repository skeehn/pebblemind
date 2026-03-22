"""Core components for PebbleMind"""

from .llm import LLMEngine


def __getattr__(name):
    if name == "PebbleMind":
        from ..pebblemind_app import PebbleMind

        return PebbleMind
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["LLMEngine", "PebbleMind"]
