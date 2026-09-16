"""Lightweight Windows presentation host for the Jarvis runtime.

The module deliberately contains no alternate tool execution path. All requests
are delegated to the existing JarvisRuntime/AgentOrchestrator stack.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import threading
from typing import Any, Callable

from quality_of_life.permissions import CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


_LOG_DIR = Path.home() / "AppData" / "Local" / "Jarvis"
_LOG_FILE = _LOG_DIR / "launcher.log"


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("jarvis.desktop")
    if logger.handlers:
        return logger
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger


LOGGER = _configure_logging()


def build_runtime() -> JarvisRuntime:
    """Build the existing guarded Jarvis runtime with default-deny policy."""
    return JarvisRuntime(CapabilityPolicy())


@dataclass(frozen=True)
class DesktopRequestResult:
    """UI-safe result wrapper used when the orchestrator raises."""

    text: str
    verified: bool = False
    needs_confirmation: bool = False
    error: str | None = None


class JarvisDesktopController:
    """Thin host/controller around the existing Jarvis orchestrator."""

    def __init__(self, runtime: JarvisRuntime | None = None) -> None:
        self.runtime = runtime or build_runtime()
        self.orchestrator = self.runtime._assistant_orchestrator()

    def execute_request(self, text: str, confirmed: bool = False) -> Any:
        """Delegate a request without changing the runtime's safety semantics."""
        prompt = text.strip()
        if not prompt:
            raise ValueError("request cannot be empty")
        return self.orchestrator.execute(prompt, confirmed=confirmed)

    def close(self) -> None:
        """Release optional long-lived runtime services."""
        try:
            self.runtime.stop_health_monitor()
        except Exception:  # noqa: BLE001
            LOGGER.exception("failed while closing Jarvis runtime")


class JarvisDesktopApp:
    """Minimal Tk chat bar with asynchronous requests and explicit confirmation."""

    def __init__(self, root: Any, controller: JarvisDesktopController) -> None:
        self.root = root
        self.controller = controller
        self._pending_confirmation: str | None = None
        self._working = False
        self._build_ui()

    def _build_ui(self) -> None:
        import tkinter as tk

        self.root.title("Jarvis")
        self.root.geometry("640x118")
        self.root.minsize(420, 118)
        self.root.resizable(True, False)
        self.root.attributes("-topmost", True)
        self.root.configure(padx=12, pady=10)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.bind("<Return>", lambda _event: self.submit())

        self.response = tk.StringVar(value="Jarvis is ready.")
        response_label = tk.Label(
            self.root,
            textvariable=self.response,
            anchor="w",
            justify="left",
            wraplength=610,
        )
        response_label.pack(fill="x", pady=(0, 8))

        row = tk.Frame(self.root)
        row.pack(fill="x")

        self.entry = tk.Entry(row)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.focus_set()

        self.send_button = tk.Button(row, text="Send", command=self.submit, width=8)
        self.send_button.pack(side="left", padx=(8, 0))

    def submit(self) -> None:
        if self._working:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._start_request(text, confirmed=False)

    def _start_request(self, text: str, confirmed: bool) -> None:
        self._working = True
        self.send_button.configure(state="disabled")
        self.response.set("Working…")

        def worker() -> None:
            try:
                result = self.controller.execute_request(text, confirmed=confirmed)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Jarvis request failed")
                self.root.after(0, lambda: self._finish_error(str(exc)))
                return
            self.root.after(0, lambda: self._finish_result(text, result))

        threading.Thread(target=worker, name="jarvis-request", daemon=True).start()

    def _finish_error(self, error: str) -> None:
        self._working = False
        self.send_button.configure(state="normal")
        self.response.set(f"I couldn't complete that safely: {error}")
        self.entry.focus_set()

    def _finish_result(self, original_text: str, result: Any) -> None:
        self._working = False
        self.send_button.configure(state="normal")

        needs_confirmation = bool(getattr(result, "needs_confirmation", False))
        if needs_confirmation:
            self._pending_confirmation = original_text
            self.response.set(
                getattr(result, "text", "This action requires your confirmation before Jarvis can proceed.")
            )
            self._ask_for_confirmation()
        else:
            self._pending_confirmation = None
            self.response.set(str(getattr(result, "text", result)))
        self.entry.focus_set()

    def _ask_for_confirmation(self) -> None:
        import tkinter.messagebox as messagebox

        pending = self._pending_confirmation
        if not pending:
            return
        approved = messagebox.askyesno(
            "Confirm Jarvis action",
            "Jarvis is asking for confirmation before performing this action.\n\n" + pending,
            parent=self.root,
        )
        if approved:
            self._start_request(pending, confirmed=True)
        else:
            self._pending_confirmation = None
            self.response.set("Cancelled.")

    def close(self) -> None:
        self.controller.close()
        self.root.destroy()


def main() -> int:
    try:
        import tkinter as tk

        root = tk.Tk()
        controller = JarvisDesktopController()
        JarvisDesktopApp(root, controller)
        root.mainloop()
        return 0
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Jarvis desktop host failed to start")
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror("Jarvis", f"Jarvis could not start safely.\n\n{exc}")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
