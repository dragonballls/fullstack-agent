"""Jarvis voice orchestration boundary: wake-gated input, OmniRoute-only brain."""

from __future__ import annotations

from dataclasses import dataclass

from .orchestration import RequestProfile
from .router import CloudModelRouter, ProviderTarget
from .voice_activation import VoiceActivationConfig, VoiceSessionLock, WakeDecision, WakeWordGate


@dataclass(frozen=True)
class VoiceRouteResult:
    decision: WakeDecision
    response: str | None
    provider: str | None


class JarvisVoiceRuntime:
    """Bind local wake gating to the existing Jarvis cloud brain without adding another brain."""

    def __init__(self, config: VoiceActivationConfig | None = None) -> None:
        self.config = config or VoiceActivationConfig.from_env()
        self.gate = WakeWordGate(self.config)
        self.session = VoiceSessionLock()

    @property
    def brain_target(self) -> ProviderTarget:
        if self.config.brain != "omniroute" or not self.config.require_omniroute or self.config.allow_claude:
            raise RuntimeError("Jarvis voice brain is restricted to OmniRoute")
        return CloudModelRouter.omniroute_target(CloudModelRouter.profile_model(RequestProfile.SMART))

    def accept(self, transcript: str, confidence: float) -> WakeDecision:
        return self.gate.evaluate(transcript, confidence)

    def route(self, transcript: str, confidence: float, profile: RequestProfile | str = RequestProfile.SMART) -> VoiceRouteResult:
        decision = self.gate.evaluate(transcript, confidence)
        if not decision.accepted:
            return VoiceRouteResult(decision, None, None)
        if not self.session.acquire():
            return VoiceRouteResult(
                WakeDecision(False, decision.confidence, decision.phrase, decision.deadline_monotonic),
                None,
                None,
            )
        try:
            target = CloudModelRouter.omniroute_target(CloudModelRouter.profile_model(profile))
            router = CloudModelRouter((target,))
            response, provider = router.complete([
                {"role": "user", "content": decision.phrase}
            ])
            return VoiceRouteResult(decision, response, provider)
        finally:
            self.session.release()
