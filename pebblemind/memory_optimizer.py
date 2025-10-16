"""Memory optimization utilities for PebbleMind"""

import gc
import psutil
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path


class MemoryOptimizer:
    """Optimize memory usage for efficient operation on lightweight devices"""
    
    def __init__(self):
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self.optimization_strategies = {
            "cache_clearing": True,
            "model_unloading": True,
            "context_truncation": True
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            "total_mb": memory.total / (1024 * 1024),
            "available_mb": memory.available / (1024 * 1024),
            "used_mb": memory.used / (1024 * 1024),
            "percent_used": memory.percent,
            "threshold_exceeded": memory.percent > (self.memory_threshold * 100)
        }
    
    def should_optimize(self) -> bool:
        """Determine if memory optimization is needed"""
        memory_info = self.get_memory_usage()
        return memory_info["threshold_exceeded"]
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization strategies"""
        results = {
            "optimization_performed": False,
            "strategies_applied": [],
            "memory_before_mb": self.get_memory_usage()["used_mb"],
            "memory_after_mb": None
        }
        
        # Clear Python garbage collector
        if self.optimization_strategies["cache_clearing"]:
            gc.collect()
            results["strategies_applied"].append("garbage_collection")
            results["optimization_performed"] = True
        
        # Get memory after optimization
        results["memory_after_mb"] = self.get_memory_usage()["used_mb"]
        
        return results
    
    async def manage_context_size(self, 
                                context: list, 
                                max_memory_mb: int = 512) -> list:
        """Dynamically manage context size based on available memory"""
        # If memory usage is high, reduce context size
        if self.should_optimize():
            # Keep only the most recent 2 items to save memory
            return context[-2:] if len(context) > 2 else context
        else:
            # Under normal memory conditions, allow more context
            return context[-5:] if len(context) > 5 else context
    
    def optimize_model_loading(self, 
                             model_path: str, 
                             use_mlock: bool = False, 
                             low_vram: bool = True) -> Dict[str, Any]:
        """Optimize model loading parameters for memory efficiency"""
        return {
            "model_path": model_path,
            "use_mlock": use_mlock,  # Don't lock model in memory to reduce pressure
            "use_mmap": True,        # Use memory mapping
            "low_vram": low_vram,    # Optimize for low VRAM (even on CPU)
        }
    
    def get_optimized_batch_size(self, available_memory_mb: float) -> int:
        """Determine optimal batch size based on available memory"""
        if available_memory_mb < 2048:  # Less than 2GB
            return 128
        elif available_memory_mb < 4096:  # Less than 4GB
            return 256
        else:  # 4GB or more
            return 512  # Default size


class ContextManager:
    """Efficiently manage conversation context to minimize memory usage"""
    
    def __init__(self, max_context_length: int = 2048, max_turns: int = 10):
        self.max_context_length = max_context_length
        self.max_turns = max_turns
        self.context_history = []
    
    def add_context(self, role: str, content: str):
        """Add context with memory-efficient management"""
        # Truncate content if it's extremely long
        if len(content) > self.max_context_length:
            content = content[:self.max_context_length] + "... [truncated]"
        
        # Add to history
        self.context_history.append({"role": role, "content": content})
        
        # Limit the number of turns to prevent memory accumulation
        if len(self.context_history) > self.max_turns:
            # Keep only the most recent turns
            self.context_history = self.context_history[-self.max_turns:]
    
    def get_context(self, max_items: Optional[int] = None) -> list:
        """Get context with optional limit"""
        if max_items is None:
            max_items = len(self.context_history)
        return self.context_history[-max_items:]
    
    def clear_context(self):
        """Clear all context to free memory"""
        self.context_history.clear()
        gc.collect()
    
    def get_memory_estimate(self) -> int:
        """Estimate memory usage of context in bytes"""
        total_chars = sum(len(item["content"]) for item in self.context_history)
        # Rough estimate: 1 character = 1 byte (for ASCII)
        return total_chars