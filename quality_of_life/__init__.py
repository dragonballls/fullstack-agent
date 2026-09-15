"""Optional quality-of-life capability layer for fullstack-agent."""

from .gods_eye import GeoPoint, GodsEye, LocationSnapshot, Place
from .intents import Intent, parse_intent
from .manifest import ToolRegistry, ToolSpec, default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityDenied, CapabilityPolicy
from .readiness import CheckStatus, ReadinessCheck, ReadinessReport, check_readiness, format_report
from .router import CloudModelRouter, ProviderTarget
from .runtime import JarvisRuntime

__all__ = [
    "Action",
    "Capability",
    "CapabilityDenied",
    "CapabilityPolicy",
    "CheckStatus",
    "CloudModelRouter",
    "ConfirmationHook",
    "GeoPoint",
    "GodsEye",
    "Intent",
    "JarvisRuntime",
    "LocationSnapshot",
    "Place",
    "ProviderTarget",
    "QoLOrchestrator",
    "ReadinessCheck",
    "ReadinessReport",
    "ToolRegistry",
    "ToolSpec",
    "check_readiness",
    "default_registry",
    "format_report",
    "parse_intent",
]
