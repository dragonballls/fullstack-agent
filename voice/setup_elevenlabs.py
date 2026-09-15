"""Guided ElevenLabs setup for the Jarvis voice.

This helper keeps the secret out of source control, verifies the API key,
finds the requested voice by name, and performs a real speech test.
It intentionally never creates an ElevenLabs account or prints the API key.
"""

from __future__ import annotations

import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

API_BASE = "https://api.elevenlabs.io/v1"
PREFERRED_VOICE = "Tarquin"
PREFERRED_MODEL = "eleven_multilingual_v2"
TEST_TEXT = "Hello. I am ready. What are we working on today?"


class VoiceSetupError(RuntimeError):
    pass


def request_json(url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"xi-api-key": api_key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise VoiceSetupError("ElevenLabs rejected the API key.") from exc
        raise VoiceSetupError(f"ElevenLabs request failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise VoiceSetupError(f"Could not reach ElevenLabs: {exc.reason}") from exc


def get_voices(api_key: str) -> list[dict]:
    data = request_json(f"{API_BASE}/voices", api_key)
    return data.get("voices", [])


def choose_voice(voices: list[dict]) -> dict:
    exact = [v for v in voices if str(v.get("name", "")).casefold() == PREFERRED_VOICE.casefold()]
    if exact:
        return exact[0]

    # Conservative fallback: choose a voice whose metadata most closely
    # matches a British, authoritative, masculine assistant voice.
    scored: list[tuple[int, dict]] = []
    for voice in voices:
        text = json.dumps(
            {
                "name": voice.get("name"),
                "labels": voice.get("labels", {}),
                "description": voice.get("description", ""),
            },
            ensure_ascii=False,
        ).casefold()
        score = 0
        score += 8 * ("british" in text or "english" in text)
        score += 5 * ("male" in text or "masculine" in text)
        score += 3 * ("authoritative" in text or "professional" in text)
        score += 2 * ("deep" in text or "calm" in text or "baritone" in text)
        if score:
            scored.append((score, voice))
    if not scored:
        raise VoiceSetupError(
            f"The requested voice '{PREFERRED_VOICE}' is not available in this account's voice list."
        )
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", ""))))
    return scored[0][1]


def synthesize(api_key: str, voice_id: str, output: Path) -> None:
    payload = json.dumps(
        {"text": TEST_TEXT, "model_id": PREFERRED_MODEL}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        data=payload,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise VoiceSetupError(f"Speech generation failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise VoiceSetupError(f"Speech generation could not reach ElevenLabs: {exc.reason}") from exc


def play_audio(path: Path) -> None:
    if sys.platform.startswith("win"):
        # Use Windows' registered player without invoking a shell.
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Start-Process",
                "-FilePath",
                str(path),
                "-Wait",
            ],
            check=True,
        )
    elif shutil.which("open"):
        subprocess.run(["open", str(path)], check=True)
    elif shutil.which("xdg-open"):
        subprocess.run(["xdg-open", str(path)], check=True)
    else:
        raise VoiceSetupError("No supported audio opener was found for the speech test.")


def main() -> int:
    print("Jarvis voice setup: ElevenLabs")
    print("I will handle the technical setup. Your API key is never printed or written to this repository.")

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Opening the official ElevenLabs dashboard so you can sign in or create your account.")
        webbrowser.open("https://elevenlabs.io/app")
        api_key = getpass.getpass("Paste your ElevenLabs API key (input stays hidden): ").strip()
    if not api_key:
        raise VoiceSetupError("No ElevenLabs API key was supplied.")

    voices = get_voices(api_key)
    voice = choose_voice(voices)
    voice_name = str(voice.get("name", "Unknown"))
    voice_id = str(voice.get("voice_id", ""))
    if not voice_id:
        raise VoiceSetupError("ElevenLabs returned a voice without a voice ID.")

    print(f"Selected voice: {voice_name}")
    print("Testing real ElevenLabs speech before setup is considered complete...")

    with tempfile.TemporaryDirectory(prefix="jarvis-voice-") as temp_dir:
        audio = Path(temp_dir) / "jarvis-test.mp3"
        synthesize(api_key, voice_id, audio)
        play_audio(audio)

    print(f"VOICE VERIFIED: ElevenLabs voice '{voice_name}' successfully generated test speech.")
    print("Set ELEVENLABS_API_KEY in the user's secure environment/credential store before starting backtalk.")
    print(f"VOICE_ID={voice_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VoiceSetupError as exc:
        print(f"VOICE SETUP FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
