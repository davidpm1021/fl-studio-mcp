"""FL Studio MCP tools."""

from fl_studio_mcp.tools.channels import register_channel_tools
from fl_studio_mcp.tools.general import register_general_tools
from fl_studio_mcp.tools.mixer import register_mixer_tools
from fl_studio_mcp.tools.patterns import register_patterns_tools
from fl_studio_mcp.tools.piano_roll import register_piano_roll_tools
from fl_studio_mcp.tools.plugins import register_plugin_tools
from fl_studio_mcp.tools.transport import register_transport_tools
from fl_studio_mcp.tools.ui import register_ui_tools

__all__ = [
    "register_transport_tools",
    "register_mixer_tools",
    "register_channel_tools",
    "register_plugin_tools",
    "register_piano_roll_tools",
    "register_general_tools",
    "register_ui_tools",
    "register_patterns_tools",
]
