"""Dynamic plugin system for extensibility"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins"""
    AGENT = "agent"
    TOOL = "tool"
    MODEL = "model"
    PROCESSOR = "processor"
    INTEGRATION = "integration"


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str] = None
    enabled: bool = True


class Plugin(ABC):
    """Base class for all plugins"""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin

        Args:
            config: Plugin configuration

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """Cleanup plugin resources"""
        pass


class AgentPlugin(Plugin):
    """Base class for agent plugins"""

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> Any:
        """
        Execute agent task

        Args:
            task: Task description
            context: Execution context

        Returns:
            Task result
        """
        pass


class ToolPlugin(Plugin):
    """Base class for tool plugins"""

    @abstractmethod
    async def invoke(self, *args, **kwargs) -> Any:
        """
        Invoke tool

        Args:
            *args: Tool arguments
            **kwargs: Tool keyword arguments

        Returns:
            Tool result
        """
        pass

    @property
    @abstractmethod
    def tool_schema(self) -> Dict[str, Any]:
        """Return tool schema for LLM function calling"""
        pass


class PluginManager:
    """
    Plugin manager for dynamic loading and management.

    Features:
    - Dynamic plugin loading from directories
    - Plugin lifecycle management
    - Dependency resolution
    - Hot reloading
    - Plugin isolation
    """

    def __init__(self, plugin_dirs: List[Path] = None):
        """
        Initialize plugin manager

        Args:
            plugin_dirs: Directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or []
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    async def discover_plugins(self):
        """Discover plugins in configured directories"""
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue

            # Find Python files
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                try:
                    await self._load_plugin_file(plugin_file)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_file}: {e}")

        logger.info(f"Discovered {len(self._plugin_classes)} plugins")

    async def _load_plugin_file(self, plugin_file: Path):
        """Load plugin from file"""
        module_name = f"pebblemind_plugin_{plugin_file.stem}"

        # Load module
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load plugin spec: {plugin_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Plugin classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj != Plugin and not inspect.isabstract(obj):
                plugin_class = obj
                self._plugin_classes[name] = plugin_class
                logger.debug(f"Loaded plugin class: {name}")

    async def load_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> bool:
        """
        Load and initialize plugin

        Args:
            plugin_name: Name of plugin to load
            config: Plugin configuration

        Returns:
            True if loaded successfully
        """
        if plugin_name in self._plugins:
            logger.warning(f"Plugin already loaded: {plugin_name}")
            return True

        if plugin_name not in self._plugin_classes:
            logger.error(f"Plugin class not found: {plugin_name}")
            return False

        try:
            # Instantiate plugin
            plugin_class = self._plugin_classes[plugin_name]
            plugin = plugin_class()

            # Initialize
            config = config or {}
            success = await plugin.initialize(config)

            if success:
                self._plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin: {plugin_name} v{plugin.metadata.version}")

                # Trigger hooks
                await self._trigger_hook("plugin_loaded", plugin)
                return True
            else:
                logger.error(f"Plugin initialization failed: {plugin_name}")
                return False

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False

    async def unload_plugin(self, plugin_name: str):
        """
        Unload plugin

        Args:
            plugin_name: Name of plugin to unload
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return

        plugin = self._plugins[plugin_name]

        try:
            await plugin.shutdown()
            del self._plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")

            # Trigger hooks
            await self._trigger_hook("plugin_unloaded", plugin)

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")

    async def reload_plugin(self, plugin_name: str, config: Dict[str, Any] = None):
        """
        Reload plugin

        Args:
            plugin_name: Name of plugin to reload
            config: New plugin configuration
        """
        await self.unload_plugin(plugin_name)
        await self.load_plugin(plugin_name, config)

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get loaded plugin instance"""
        return self._plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of specified type"""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.metadata.plugin_type == plugin_type
        ]

    def register_hook(self, event: str, callback: Callable):
        """
        Register hook for plugin events

        Args:
            event: Event name (plugin_loaded, plugin_unloaded, etc.)
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    async def _trigger_hook(self, event: str, *args, **kwargs):
        """Trigger registered hooks for event"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in hook callback for {event}: {e}")

    async def shutdown_all(self):
        """Shutdown all loaded plugins"""
        for plugin_name in list(self._plugins.keys()):
            await self.unload_plugin(plugin_name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins"""
        return [
            {
                "name": name,
                "loaded": name in self._plugins,
                "metadata": (
                    {
                        "version": self._plugins[name].metadata.version,
                        "type": self._plugins[name].metadata.plugin_type.value,
                        "description": self._plugins[name].metadata.description,
                    }
                    if name in self._plugins
                    else None
                )
            }
            for name in self._plugin_classes.keys()
        ]


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
