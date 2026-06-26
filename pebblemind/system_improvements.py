"""System Improvements for Enhanced PebbleMind"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """Monitor and maintain system health across all components"""
    
    def __init__(self):
        self.component_health = {}
        self.error_log = []
        self.performance_thresholds = {
            "response_time": 10.0,  # seconds
            "memory_usage": 0.8,    # percentage
            "error_rate": 0.1       # percentage
        }
    
    def update_component_health(self, component: str, status: str, details: Dict[str, Any] = None):
        """Update health status for a component"""
        self.component_health[component] = {
            "status": status,
            "last_updated": time.monotonic(),
            "details": details or {}
        }
    
    def log_error(self, error: Exception, context: str = ""):
        """Log system errors for debugging and monitoring"""
        error_entry = {
            "timestamp": time.monotonic(),
            "error": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }
        self.error_log.append(error_entry)
        logger.error(f"System Error in {context}: {error}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get a comprehensive health report"""
        return {
            "components": self.component_health,
            "error_count": len(self.error_log),
            "recent_errors": self.error_log[-5:],  # Last 5 errors
            "overall_status": self._calculate_overall_status()
        }
    
    def _calculate_overall_status(self) -> str:
        """Calculate the overall system status"""
        if not self.component_health:
            return "unknown"
        
        # Count healthy components
        healthy_count = sum(1 for comp in self.component_health.values() if comp["status"] == "healthy")
        healthy_percentage = healthy_count / len(self.component_health)
        
        if healthy_percentage >= 0.8:
            return "healthy"
        elif healthy_percentage >= 0.5:
            return "degraded"
        else:
            return "critical"


class ContextOptimizer:
    """Optimize context management across all system components"""
    
    def __init__(self, max_context_tokens: int = 2048):
        self.max_context_tokens = max_context_tokens
        self.context_history = []
    
    async def optimize_context(self, 
                             text_context: List[str], 
                             memory_context: List[str],
                             tool_context: List[str],
                             agent_context: List[str]) -> List[str]:
        """Optimize and combine different context sources"""
        # Combine all contexts
        all_context = text_context + memory_context + tool_context + agent_context
        
        # If we have too much context, prioritize by importance
        if len(" ".join(all_context).split()) > self.max_context_tokens:
            # For now, we'll use a simple truncation approach
            # In a real implementation, we'd use more sophisticated prioritization
            optimized_context = self._prioritize_context(all_context)
        else:
            optimized_context = all_context
        
        # Update context history
        self.context_history.append({
            "timestamp": time.monotonic(),
            "context_count": len(optimized_context),
            "total_tokens": len(" ".join(optimized_context).split())
        })
        
        return optimized_context
    
    def _prioritize_context(self, context_list: List[str]) -> List[str]:
        """Prioritize context items based on relevance and recency"""
        # Simple prioritization: keep most recent items
        # In a real implementation, this would use more sophisticated methods
        # like semantic similarity to the current query
        max_items = 10  # Maximum number of context items to keep
        return context_list[-max_items:] if len(context_list) > max_items else context_list


class FallbackManager:
    """Manage fallback strategies when primary systems fail"""
    
    def __init__(self):
        self.fallback_strategies = {
            "llm_failure": self._llm_fallback,
            "tool_failure": self._tool_fallback,
            "memory_failure": self._memory_fallback,
            "service_failure": self._service_fallback
        }
    
    async def handle_failure(self, failure_type: str, original_request: Any, **kwargs) -> Any:
        """Handle system failures with appropriate fallbacks"""
        if failure_type in self.fallback_strategies:
            try:
                return await self.fallback_strategies[failure_type](original_request, **kwargs)
            except Exception as e:
                # Ultimate fallback - return a simple error message
                return f"System error occurred: {str(e)}. Please try again later."
        else:
            return f"Unknown failure type: {failure_type}. Please try again."
    
    async def _llm_fallback(self, original_request: Any, **kwargs) -> str:
        """Fallback when LLM is unavailable"""
        return f"I'm having trouble processing your request right now, but I received: {str(original_request)[:100]}..."
    
    async def _tool_fallback(self, original_request: Any, **kwargs) -> str:
        """Fallback when tools are unavailable"""
        return f"I can't access external tools right now, but I can help with general knowledge about: {str(original_request)}"
    
    async def _memory_fallback(self, original_request: Any, **kwargs) -> str:
        """Fallback when memory is unavailable"""
        return f"I'm working without access to our memory system, but I can still help with: {str(original_request)}"
    
    async def _service_fallback(self, original_request: Any, **kwargs) -> str:
        """Fallback when external services are unavailable"""
        return f"I can't reach external services right now, but I can help with my local capabilities regarding: {str(original_request)}"


class ComponentOrchestrator:
    """Orchestrate and coordinate all system components"""
    
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.context_optimizer = ContextOptimizer()
        self.fallback_manager = FallbackManager()
        self.component_initialization_order = [
            "memory_manager",
            "tool_manager", 
            "agent_orchestrator",
            "multimodal_manager",
            "service_integration_manager",
            "llm_engine"
        ]
    
    async def coordinate_request(self, 
                               pebblemind_instance,
                               user_message: str,
                               **options) -> str:
        """Coordinate processing of a user request across all components"""
        try:
            # Check overall system health
            health_report = self.health_monitor.get_health_report()
            if health_report["overall_status"] == "critical":
                return "System is currently in critical state. Please try again later."
            
            # Gather context from all components
            text_context = [user_message]
            memory_context = []
            tool_context = []
            agent_context = []
            
            # Try to get memory context (with fallback)
            try:
                if hasattr(pebblemind_instance, 'memory_manager'):
                    memory_context = await pebblemind_instance.memory_manager.retrieve_relevant_context(
                        query=user_message, 
                        max_memories=3
                    )
                    self.health_monitor.update_component_health("memory", "healthy")
            except Exception as e:
                self.health_monitor.log_error(e, "memory_retrieval")
                memory_context = []
                # Use fallback
                fallback_result = await self.fallback_manager.handle_failure(
                    "memory_failure", user_message
                )
                if fallback_result != user_message:
                    memory_context = [fallback_result]
            
            # Process with tools if enabled
            try:
                if options.get("use_tools", True) and hasattr(pebblemind_instance, 'tool_manager'):
                    from .tool_integration import process_tool_calls
                    tool_results = await process_tool_calls(user_message, pebblemind_instance.tool_manager)
                    if tool_results.strip():
                        tool_context = [tool_results]
                    self.health_monitor.update_component_health("tools", "healthy")
            except Exception as e:
                self.health_monitor.log_error(e, "tool_processing")
                tool_context = []
            
            # Process with specialized agents if needed
            try:
                if "agent" in user_message.lower() and hasattr(pebblemind_instance, 'agent_orchestrator'):
                    agent_result = await pebblemind_instance.agent_orchestrator.route_task(user_message)
                    if agent_result and "result" in agent_result:
                        agent_context = [str(agent_result["result"])]
                    self.health_monitor.update_component_health("agents", "healthy")
            except Exception as e:
                self.health_monitor.log_error(e, "agent_processing")
                agent_context = []
            
            # Optimize the combined context
            optimized_context = await self.context_optimizer.optimize_context(
                text_context=text_context,
                memory_context=memory_context,
                tool_context=tool_context,
                agent_context=agent_context
            )
            
            # Prepare the final context
            final_context = optimized_context if len(optimized_context) <= 1 else optimized_context[1:]  # Exclude original message from context
            
            # Generate response with LLM (with fallback)
            try:
                if hasattr(pebblemind_instance, 'llm_engine'):
                    # Check if we need to enhance reasoning
                    enhance_reasoning = options.get("enhance_reasoning", True)
                    reasoning_type = options.get("reasoning_type", "analytical")
                    use_memory = options.get("use_memory", True)
                    use_tools = options.get("use_tools", True)
                    
                    # Call the main query method with optimized parameters
                    response = await pebblemind_instance.query(
                        message=user_message,
                        context=final_context,
                        enhance_reasoning=enhance_reasoning,
                        reasoning_type=reasoning_type,
                        use_memory=use_memory,
                        use_tools=use_tools
                    )
                    self.health_monitor.update_component_health("llm", "healthy", {"response_length": len(response)})
                    return response
                else:
                    # Ultimate fallback if no LLM is available
                    return self._ultimate_fallback(user_message, optimized_context)
            except Exception as e:
                self.health_monitor.log_error(e, "llm_generation")
                fallback_result = await self.fallback_manager.handle_failure(
                    "llm_failure", user_message
                )
                return fallback_result
                
        except Exception as e:
            # Catch any unexpected errors and use fallback
            self.health_monitor.log_error(e, "request_coordination")
            return await self.fallback_manager.handle_failure(
                "system_failure", user_message
            )
    
    def _ultimate_fallback(self, user_message: str, context: List[str]) -> str:
        """Ultimate fallback when no components are available"""
        return f"I'm currently operating with limited capabilities, but I can acknowledge your request: '{user_message}'. Please try again when systems are fully operational."


class SystemImprovementManager:
    """Main improvement manager that ties all enhancements together"""
    
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.context_optimizer = ContextOptimizer()
        self.fallback_manager = FallbackManager()
        self.orchestrator = ComponentOrchestrator()
        
        # Initialize improvement components
        self._initialize_improvements()
    
    def _initialize_improvements(self):
        """Initialize all system improvements"""
        logger.info("Initializing PebbleMind system improvements...")
        
        # Log the initialization of each component
        self.health_monitor.update_component_health("improvements", "initialized")
        self.health_monitor.update_component_health("context_optimizer", "initialized")
        self.health_monitor.update_component_health("fallback_manager", "initialized")
        self.health_monitor.update_component_health("orchestrator", "initialized")
    
    async def enhance_pebblemind(self, pebblemind_instance):
        """Apply all improvements to a PebbleMind instance"""
        # Add improvement components to the PebbleMind instance
        pebblemind_instance.health_monitor = self.health_monitor
        pebblemind_instance.context_optimizer = self.context_optimizer
        pebblemind_instance.fallback_manager = self.fallback_manager
        pebblemind_instance.coordinator = self.orchestrator
        
        # Update health status
        self.health_monitor.update_component_health("pebblemind_enhanced", "healthy", {
            "timestamp": time.monotonic(),
            "version": "enhanced_1.0"
        })
        
        logger.info("PebbleMind enhanced with system improvements successfully")
        
        return pebblemind_instance
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return {
            "health_report": self.health_monitor.get_health_report(),
            "context_history_count": len(self.context_optimizer.context_history),
            "total_errors_logged": len(self.health_monitor.error_log)
        }


# Utility functions for system improvements
async def add_resilience_to_query_method(pebblemind_class):
    """Add resilience features to the query method"""
    original_query = pebblemind_class.query
    
    async def resilient_query(self, message: str, **kwargs):
        """Enhanced query method with built-in resilience"""
        try:
            # Use the coordinator if available
            if hasattr(self, 'coordinator'):
                return await self.coordinator.coordinate_request(self, message, **kwargs)
            else:
                # Fall back to original method
                return await original_query(self, message, **kwargs)
        
        except Exception as e:
            # Log the error
            if hasattr(self, 'health_monitor'):
                self.health_monitor.log_error(e, "query_method")
            
            # Try to use fallback manager
            if hasattr(self, 'fallback_manager'):
                return await self.fallback_manager.handle_failure(
                    "query_failure", message, **kwargs
                )
            else:
                # Return a basic error response
                return f"Error processing your request: {str(e)}"
    
    # Replace the query method
    pebblemind_class.query = resilient_query
    return pebblemind_class


async def apply_all_improvements():
    """Apply all system improvements to PebbleMind"""
    improvement_manager = SystemImprovementManager()
    
    # This would return the improvement manager that can be used to enhance PebbleMind instances
    return improvement_manager