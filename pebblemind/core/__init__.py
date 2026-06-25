"""Core components for PebbleMind"""

from .llm import LLMEngine


def __getattr__(name):
    if name == "PebbleMind":
        from ..pebblemind_app import PebbleMind

        return PebbleMind
    if name == "quick_start":
        from ..pebblemind_app import quick_start

        return quick_start
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["LLMEngine", "PebbleMind", "quick_start"]
