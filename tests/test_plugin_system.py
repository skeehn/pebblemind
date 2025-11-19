"""Tests for plugin system"""

import pytest
import asyncio
from pebblemind.plugins import (
    Plugin,
    PluginManager,
    PluginType,
    PluginMetadata,
    ToolPlugin
)


class TestToolPlugin(ToolPlugin):
    """Test plugin for testing"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test_tool",
            version="1.0.0",
            author="Test",
            description="Test tool plugin",
            plugin_type=PluginType.TOOL
        )

    async def initialize(self, config: dict) -> bool:
        self.config = config
        return True

    async def shutdown(self):
        pass

    async def invoke(self, *args, **kwargs):
        return {"result": "test_result", "args": args, "kwargs": kwargs}

    @property
    def tool_schema(self) -> dict:
        return {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {}
        }


@pytest.mark.asyncio
async def test_plugin_manager_initialization():
    """Test plugin manager initialization"""
    manager = PluginManager()
    assert manager is not None
    assert len(manager._plugins) == 0


@pytest.mark.asyncio
async def test_plugin_loading():
    """Test plugin loading"""
    manager = PluginManager()

    # Register plugin class manually for testing
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    # Load plugin
    success = await manager.load_plugin("TestToolPlugin", {"test": "config"})
    assert success is True
    assert "TestToolPlugin" in manager._plugins

    # Check plugin instance
    plugin = manager.get_plugin("TestToolPlugin")
    assert plugin is not None
    assert plugin.config == {"test": "config"}


@pytest.mark.asyncio
async def test_plugin_invocation():
    """Test plugin invocation"""
    manager = PluginManager()
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    await manager.load_plugin("TestToolPlugin")
    plugin = manager.get_plugin("TestToolPlugin")

    # Invoke plugin
    result = await plugin.invoke("arg1", "arg2", key="value")
    assert result["result"] == "test_result"
    assert result["args"] == ("arg1", "arg2")
    assert result["kwargs"] == {"key": "value"}


@pytest.mark.asyncio
async def test_plugin_unloading():
    """Test plugin unloading"""
    manager = PluginManager()
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    await manager.load_plugin("TestToolPlugin")
    assert "TestToolPlugin" in manager._plugins

    await manager.unload_plugin("TestToolPlugin")
    assert "TestToolPlugin" not in manager._plugins


@pytest.mark.asyncio
async def test_get_plugins_by_type():
    """Test getting plugins by type"""
    manager = PluginManager()
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    await manager.load_plugin("TestToolPlugin")

    tool_plugins = manager.get_plugins_by_type(PluginType.TOOL)
    assert len(tool_plugins) == 1
    assert isinstance(tool_plugins[0], ToolPlugin)


@pytest.mark.asyncio
async def test_plugin_hooks():
    """Test plugin event hooks"""
    manager = PluginManager()
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    loaded_plugins = []

    def on_plugin_loaded(plugin):
        loaded_plugins.append(plugin.metadata.name)

    manager.register_hook("plugin_loaded", on_plugin_loaded)

    await manager.load_plugin("TestToolPlugin")

    assert "test_tool" in loaded_plugins


@pytest.mark.asyncio
async def test_list_plugins():
    """Test listing available plugins"""
    manager = PluginManager()
    manager._plugin_classes["TestToolPlugin"] = TestToolPlugin

    await manager.load_plugin("TestToolPlugin")

    plugins = manager.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "TestToolPlugin"
    assert plugins[0]["loaded"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
