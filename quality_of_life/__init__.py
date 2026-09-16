"""Optional quality-of-life capability layer for fullstack-agent."""

from .agent_orchestrator import AgentOrchestrator, OrchestrationEvent, OrchestrationResult
from .capabilities import OPERATION_CATALOG, OperationRisk, OperationSpec, operation, operations_for
from .computer_use import ComputerUseAction, ComputerUseAgent, ComputerUseResult, RouterComputerUsePlanner, ScreenObserver
from .gods_eye import GeoPoint, GodsEye, LocationSnapshot, Place
from .health_monitor import HealthMonitor, HealthSnapshot
from .intents import Intent, parse_intent
from .jarvis_voice import JarvisVoiceRuntime, VoiceRouteResult
from .manifest import ToolRegistry, ToolSpec, default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .orchestration import OrchestrationPlan, RequestProfile, SpecialistTask, build_plan, classify_request
from .permissions import Capability, CapabilityDenied, CapabilityPolicy
from .readiness import CheckStatus, ReadinessCheck, ReadinessReport, check_readiness, format_report
from .router import CloudModelRouter, ProviderResult, ProviderTarget
from .runtime import JarvisRuntime
from .voice_activation import VoiceActivationConfig, VoiceSessionLock, WakeDecision, WakeWordGate
from .voice_listener import LocalWakeWordListener, VoiceListenerUnavailable, WakeEvent

__all__ = [
    "Action",
    "AgentOrchestrator",
    "Capability",
    "CapabilityDenied",
    "CapabilityPolicy",
    "CheckStatus",
    "CloudModelRouter",
    "ComputerUseAction",
    "ComputerUseAgent",
    "ComputerUseResult",
    "ConfirmationHook",
    "GeoPoint",
    "GodsEye",
    "HealthMonitor",
    "HealthSnapshot",
    "Intent",
    "JarvisRuntime",
    "JarvisVoiceRuntime",
    "LocalWakeWordListener",
    "LocationSnapshot",
    "OPERATION_CATALOG",
    "OperationRisk",
    "OperationSpec",
    "OrchestrationEvent",
    "OrchestrationPlan",
    "OrchestrationResult",
    "Place",
    "ProviderResult",
    "ProviderTarget",
    "QoLOrchestrator",
    "ReadinessCheck",
    "ReadinessReport",
    "RequestProfile",
    "RouterComputerUsePlanner",
    "ScreenObserver",
    "SpecialistTask",
    "ToolRegistry",
    "ToolSpec",
    "VoiceActivationConfig",
    "VoiceListenerUnavailable",
    "VoiceRouteResult",
    "VoiceSessionLock",
    "WakeDecision",
    "WakeEvent",
    "WakeWordGate",
    "build_plan",
    "check_readiness",
    "classify_request",
    "default_registry",
    "format_report",
    "operation",
    "operations_for",
    "parse_intent",
]
