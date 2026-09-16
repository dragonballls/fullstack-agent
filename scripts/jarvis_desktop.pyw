"""Windows no-console entrypoint for the Jarvis desktop host."""

from scripts.jarvis_desktop import main


if __name__ == "__main__":
    raise SystemExit(main())
