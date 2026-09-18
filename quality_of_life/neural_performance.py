"""Adaptive presentation budgets for the Neural JARVIS renderer.

This controller only adjusts Jarvis-owned rendering/capture budgets. It does not
terminate processes, inject into games, or alter third-party application state.
"""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
import threading
import time


@dataclass(frozen=True)
class RenderBudget:
    quality: str
    max_neurons: int
    max_relations: int
    particle_cap: int
    target_fps: int
    device_pixel_ratio: float
    capture_interval_ms: int
    physics_level: int

    def as_dict(self) -> dict[str, object]:
        return {
            "quality": self.quality,
            "max_neurons": self.max_neurons,
            "max_relations": self.max_relations,
            "particle_cap": self.particle_cap,
            "target_fps": self.target_fps,
            "device_pixel_ratio": self.device_pixel_ratio,
            "capture_interval_ms": self.capture_interval_ms,
            "physics_level": self.physics_level,
        }


@dataclass(frozen=True)
class SystemPressure:
    cpu_percent: float | None
    memory_percent: float | None
    gpu_percent: float | None
    gpu_memory_percent: float | None

    @property
    def score(self) -> float:
        return max((value for value in (
            self.cpu_percent,
            self.memory_percent,
            self.gpu_percent,
            self.gpu_memory_percent,
        ) if value is not None), default=0.0)

    def as_dict(self) -> dict[str, object]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "gpu_percent": self.gpu_percent,
            "gpu_memory_percent": self.gpu_memory_percent,
            "pressure_score": self.score,
        }


class AdaptivePerformanceController:
    """Hysteresis-controlled performance budgets with throttled sampling."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mode = "foreground"
        self._budget = self._budget_for("maximum")
        self._pressure = SystemPressure(None, None, None, None)
        self._last_sample = 0.0

    @staticmethod
    def _budget_for(quality: str) -> RenderBudget:
        return {
            "maximum": RenderBudget("maximum", 1800, 4200, 180, 60, 1.50, 1500, 3),
            "balanced": RenderBudget("balanced", 1000, 2400, 110, 60, 1.20, 2200, 2),
            "performance": RenderBudget("performance", 600, 1200, 70, 50, 1.00, 3200, 1),
            "minimal": RenderBudget("minimal", 320, 600, 0, 20, 1.00, 5000, 0),
        }[quality]

    def set_mode(self, mode: str) -> str:
        normalized = str(mode).strip().lower()
        if normalized not in {"foreground", "background"}:
            raise ValueError("mode must be foreground or background")
        with self._lock:
            self._mode = normalized
            if normalized == "background":
                self._budget = self._budget_for("minimal")
        return normalized

    def mode(self) -> str:
        with self._lock:
            return self._mode

    @staticmethod
    def _nvidia() -> tuple[float | None, float | None]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=0.5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None, None
            parts = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
            if len(parts) != 3:
                return None, None
            util, used, total = map(float, parts)
            return util, (used / total * 100.0) if total > 0 else None
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None, None

    def sample(self, *, force: bool = False) -> tuple[SystemPressure, RenderBudget]:
        now = time.monotonic()
        with self._lock:
            if not force and now - self._last_sample < 1.5:
                return self._pressure, self._budget
            mode = self._mode

        cpu = memory = None
        try:
            import psutil  # type: ignore
            cpu = float(psutil.cpu_percent(interval=None))
            memory = float(psutil.virtual_memory().percent)
        except (ImportError, OSError):
            pass

        gpu, gpu_memory = self._nvidia()
        pressure = SystemPressure(cpu, memory, gpu, gpu_memory)

        with self._lock:
            previous = self._budget.quality
            if mode == "background":
                quality = "minimal"
            else:
                score = pressure.score
                quality = previous
                if previous == "maximum" and score >= 72:
                    quality = "balanced"
                elif previous == "balanced":
                    if score >= 86:
                        quality = "performance"
                    elif score <= 54:
                        quality = "maximum"
                elif previous == "performance":
                    if score >= 94:
                        quality = "minimal"
                    elif score <= 68:
                        quality = "balanced"
                elif previous == "minimal" and score <= 58:
                    quality = "performance"
            self._pressure = pressure
            self._budget = self._budget_for(quality)
            self._last_sample = now
            return pressure, self._budget

    def snapshot(self, *, force: bool = False) -> dict[str, object]:
        pressure, budget = self.sample(force=force)
        payload = pressure.as_dict()
        payload.update(budget.as_dict())
        payload["mode"] = self.mode()
        return payload
