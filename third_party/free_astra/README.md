# Embedded Prism/Astra bridge

This directory vendors the free-astra adapter used by the optional Jarvis Prism
integration.

Source repository: https://github.com/Zhao73/free-astra
Pinned source revision: 300cb71c4724f155ec4487f14ae3ecf8b4e39cc5

The adapter remains optional. Jarvis only uses it when a local Prism session file
is configured. It does not contain or execute a local LLM; model inference stays on
the remote Prism service.

The packaged Windows integration disables the upstream project's Unix/Bash
automatic refresh path. Jarvis does not scrape browser cookies or silently collect
credentials.

The upstream project is unsupported and its model availability can change. Jarvis
therefore treats Prism/Astra as a capability that must actually answer, and keeps
OmniRoute available as the normal fallback.
