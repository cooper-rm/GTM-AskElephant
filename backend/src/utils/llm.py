"""
LLM utility — calls Claude via SDK (deployed) or CLI (local dev).

If ANTHROPIC_API_KEY is set → uses the Anthropic Python SDK (Heroku, production).
If not → falls back to the Claude CLI binary (local dev with Claude Code subscription).
"""
import os
import subprocess


# Model name mapping — short aliases to full model IDs (SDK only)
MODEL_MAP = {
    'haiku': 'claude-haiku-4-5-20251001',
    'sonnet': 'claude-sonnet-4-6',
    'opus': 'claude-opus-4-6',
}

_client = None


def _get_client():
    """Lazy-init the Anthropic SDK client. Returns None if no API key."""
    global _client
    if _client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
        if api_key:
            import anthropic
            _client = anthropic.Anthropic(api_key=api_key)
    return _client


def ask_claude(
    prompt: str,
    system: str = "",
    timeout: int = 60,
    model: str = "sonnet",
) -> str:
    """
    Send a prompt to Claude.

    Routing:
        ANTHROPIC_API_KEY set → SDK call (works on Heroku / any server)
        No API key           → CLI subprocess (local dev with Claude Code sub)
    """
    client = _get_client()
    if client is not None:
        return _call_sdk(client, prompt, system, timeout, model)
    else:
        return _call_cli(prompt, system, timeout, model)


def _call_sdk(client, prompt: str, system: str, timeout: int, model: str) -> str:
    """Call Claude via the Anthropic Python SDK."""
    model_id = MODEL_MAP.get(model, model)

    kwargs = {
        'model': model_id,
        'max_tokens': 4096,
        'messages': [{'role': 'user', 'content': prompt}],
        'timeout': timeout,
    }
    if system:
        kwargs['system'] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text.strip()


def _call_cli(prompt: str, system: str, timeout: int, model: str) -> str:
    """Call Claude via the local CLI binary (Claude Code subscription)."""
    if system:
        prompt = f"[System: {system}]\n\n{prompt}"

    # Try common CLI locations
    cli_paths = [
        '/opt/homebrew/bin/claude',
        '/usr/local/bin/claude',
        'claude',  # rely on PATH
    ]

    cmd = None
    for path in cli_paths:
        try:
            subprocess.run([path, '--version'], capture_output=True, timeout=5)
            cmd = path
            break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    if cmd is None:
        raise RuntimeError(
            "No Claude access: ANTHROPIC_API_KEY not set and Claude CLI not found. "
            "Set ANTHROPIC_API_KEY in .env or install the Claude CLI."
        )

    result = subprocess.run(
        [cmd, '-p', '--model', model],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr}")

    return result.stdout.strip()
