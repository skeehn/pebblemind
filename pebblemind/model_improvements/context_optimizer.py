"""
Context window optimization for better token usage and relevance.

Intelligently manages the context window to maximize useful information
while staying within model limits.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import tiktoken

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Context compression strategies"""
    SLIDING_WINDOW = "sliding_window"  # Keep most recent messages
    SUMMARIZE_OLD = "summarize_old"  # Summarize old messages
    SEMANTIC_FILTERING = "semantic_filtering"  # Keep most relevant
    HIERARCHICAL = "hierarchical"  # Summarize at different levels


@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    tokens: int
    importance: float = 1.0
    timestamp: Optional[float] = None


@dataclass
class ContextWindow:
    """Optimized context window"""
    messages: List[Message]
    total_tokens: int
    compression_ratio: float
    strategy_used: CompressionStrategy


class ContextOptimizer:
    """
    Optimize context window usage for better model performance.

    Features:
    - Token counting and budgeting
    - Intelligent message summarization
    - Recency vs relevance balancing
    - Automatic compression
    """

    def __init__(
        self,
        max_context_tokens: int = 2048,
        target_context_tokens: Optional[int] = None,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize context optimizer

        Args:
            max_context_tokens: Maximum context window size
            target_context_tokens: Target size (for safety margin)
            encoding_name: Tokenizer encoding to use
        """
        self.max_context_tokens = max_context_tokens
        self.target_context_tokens = target_context_tokens or int(max_context_tokens * 0.8)

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Could not load tiktoken encoding: {e}, using fallback")
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: rough estimate
            return len(text) // 4

    def optimize_context(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        strategy: CompressionStrategy = CompressionStrategy.SLIDING_WINDOW,
        system_message: Optional[str] = None
    ) -> ContextWindow:
        """
        Optimize context window to fit within token limit

        Args:
            messages: List of messages
            max_tokens: Maximum tokens (uses default if None)
            strategy: Compression strategy
            system_message: System message to always include

        Returns:
            Optimized context window
        """
        max_tokens = max_tokens or self.target_context_tokens

        # Convert to Message objects with token counts
        msg_objects = []
        for msg in messages:
            content = msg.get("content", "")
            msg_obj = Message(
                role=msg.get("role", "user"),
                content=content,
                tokens=self.count_tokens(content),
                importance=self._calculate_importance(msg),
                timestamp=msg.get("timestamp")
            )
            msg_objects.append(msg_obj)

        # Reserve tokens for system message
        reserved_tokens = 0
        if system_message:
            reserved_tokens = self.count_tokens(system_message)

        available_tokens = max_tokens - reserved_tokens

        # Apply compression strategy
        if strategy == CompressionStrategy.SLIDING_WINDOW:
            optimized = self._sliding_window(msg_objects, available_tokens)
        elif strategy == CompressionStrategy.SUMMARIZE_OLD:
            optimized = self._summarize_old(msg_objects, available_tokens)
        elif strategy == CompressionStrategy.SEMANTIC_FILTERING:
            optimized = self._semantic_filtering(msg_objects, available_tokens)
        else:
            optimized = self._sliding_window(msg_objects, available_tokens)

        total_tokens = sum(msg.tokens for msg in optimized)
        original_tokens = sum(msg.tokens for msg in msg_objects)
        compression_ratio = total_tokens / original_tokens if original_tokens > 0 else 1.0

        logger.info(
            f"Context optimized: {original_tokens} → {total_tokens} tokens "
            f"({compression_ratio:.1%}, strategy: {strategy.value})"
        )

        return ContextWindow(
            messages=optimized,
            total_tokens=total_tokens,
            compression_ratio=compression_ratio,
            strategy_used=strategy
        )

    def _calculate_importance(self, message: Dict[str, str]) -> float:
        """
        Calculate message importance score

        Args:
            message: Message dict

        Returns:
            Importance score (0.0 to 1.0)
        """
        importance = 1.0

        # System messages are most important
        if message.get("role") == "system":
            importance = 2.0

        # Recent messages are more important
        # (handled by position in list)

        # Longer messages might be more important
        content = message.get("content", "")
        if len(content) > 500:
            importance *= 1.2

        # Messages with code blocks are important
        if "```" in content:
            importance *= 1.3

        # Messages with questions are important
        if "?" in content:
            importance *= 1.1

        return min(importance, 2.0)

    def _sliding_window(
        self,
        messages: List[Message],
        max_tokens: int
    ) -> List[Message]:
        """
        Keep most recent messages that fit in window

        Args:
            messages: List of messages
            max_tokens: Maximum tokens

        Returns:
            Filtered messages
        """
        result = []
        current_tokens = 0

        # Work backwards from most recent
        for msg in reversed(messages):
            if current_tokens + msg.tokens <= max_tokens:
                result.insert(0, msg)
                current_tokens += msg.tokens
            else:
                # Try to fit partial message
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # Only if we have reasonable space
                    truncated = self._truncate_message(msg, remaining_tokens)
                    if truncated:
                        result.insert(0, truncated)
                break

        return result

    def _summarize_old(
        self,
        messages: List[Message],
        max_tokens: int
    ) -> List[Message]:
        """
        Summarize older messages to save space

        Args:
            messages: List of messages
            max_tokens: Maximum tokens

        Returns:
            Optimized messages with summaries
        """
        if len(messages) <= 3:
            return self._sliding_window(messages, max_tokens)

        # Always keep last few messages
        keep_recent = 3
        recent_messages = messages[-keep_recent:]
        old_messages = messages[:-keep_recent]

        # Calculate tokens in recent messages
        recent_tokens = sum(msg.tokens for msg in recent_messages)

        # If recent messages fit, see if we can fit more
        if recent_tokens >= max_tokens:
            return self._sliding_window(messages, max_tokens)

        available_for_old = max_tokens - recent_tokens

        # Create summary of old messages
        summary = self._create_summary(old_messages)
        summary_tokens = self.count_tokens(summary)

        result = []

        if summary_tokens < available_for_old:
            # Add summary
            result.append(Message(
                role="system",
                content=f"[Summary of earlier conversation: {summary}]",
                tokens=summary_tokens,
                importance=0.8
            ))
        else:
            # Summary too long, use sliding window on old messages
            old_window = self._sliding_window(old_messages, available_for_old)
            result.extend(old_window)

        # Add recent messages
        result.extend(recent_messages)

        return result

    def _semantic_filtering(
        self,
        messages: List[Message],
        max_tokens: int
    ) -> List[Message]:
        """
        Keep most important/relevant messages

        Args:
            messages: List of messages
            max_tokens: Maximum tokens

        Returns:
            Filtered messages by importance
        """
        # Sort by importance (descending)
        sorted_messages = sorted(messages, key=lambda m: m.importance, reverse=True)

        result = []
        current_tokens = 0

        for msg in sorted_messages:
            if current_tokens + msg.tokens <= max_tokens:
                result.append(msg)
                current_tokens += msg.tokens

        # Re-sort by original order
        result.sort(key=lambda m: messages.index(m))

        return result

    def _truncate_message(
        self,
        message: Message,
        max_tokens: int
    ) -> Optional[Message]:
        """
        Truncate message to fit token limit

        Args:
            message: Message to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated message or None
        """
        if max_tokens < 50:  # Too small to be useful
            return None

        # Estimate how many characters to keep
        chars_per_token = len(message.content) / message.tokens if message.tokens > 0 else 4
        max_chars = int(max_tokens * chars_per_token * 0.9)  # Safety margin

        if max_chars >= len(message.content):
            return message

        truncated_content = message.content[:max_chars] + "..."

        return Message(
            role=message.role,
            content=truncated_content,
            tokens=self.count_tokens(truncated_content),
            importance=message.importance * 0.8,  # Reduce importance for truncated
            timestamp=message.timestamp
        )

    def _create_summary(self, messages: List[Message]) -> str:
        """
        Create a brief summary of messages

        Args:
            messages: Messages to summarize

        Returns:
            Summary text
        """
        if not messages:
            return ""

        # Simple extractive summary
        key_points = []

        for msg in messages:
            # Extract first sentence or first 100 chars
            content = msg.content.strip()
            if content:
                first_sentence = content.split('.')[0]
                if len(first_sentence) > 100:
                    first_sentence = content[:100] + "..."
                key_points.append(f"{msg.role}: {first_sentence}")

        # Limit summary length
        summary = ". ".join(key_points[:5])
        if len(summary) > 500:
            summary = summary[:500] + "..."

        return summary

    def format_messages_for_llm(
        self,
        context_window: ContextWindow,
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Format optimized context for LLM input

        Args:
            context_window: Optimized context
            system_message: Optional system message to prepend

        Returns:
            List of message dicts
        """
        messages = []

        # Add system message if provided
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })

        # Add context messages
        for msg in context_window.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return messages

    def estimate_tokens_for_response(
        self,
        context_tokens: int,
        max_response_tokens: int = 512
    ) -> int:
        """
        Estimate how many tokens to reserve for response

        Args:
            context_tokens: Tokens used by context
            max_response_tokens: Desired max response length

        Returns:
            Recommended max_tokens for generation
        """
        available = self.max_context_tokens - context_tokens

        # Reserve some buffer (10%)
        available = int(available * 0.9)

        # Cap at desired max
        return min(available, max_response_tokens)


# Global context optimizer
_context_optimizer: Optional[ContextOptimizer] = None


def get_context_optimizer(max_context_tokens: int = 2048) -> ContextOptimizer:
    """Get context optimizer instance"""
    global _context_optimizer
    if _context_optimizer is None:
        _context_optimizer = ContextOptimizer(max_context_tokens=max_context_tokens)
    return _context_optimizer
