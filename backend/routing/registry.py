"""Backward-compatible shim — canonical registry lives in provision.registry."""

from provision.registry import (
    CAPABILITY_REQUIRES_LABELS,
    TOOL_REGISTRY,
    iter_control_tower_capabilities,
    register_tool,
)

__all__ = [
    "CAPABILITY_REQUIRES_LABELS",
    "TOOL_REGISTRY",
    "register_tool",
    "iter_control_tower_capabilities",
]
