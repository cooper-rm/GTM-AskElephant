"""
LLM utility — calls Claude via CLI subprocess.
Uses Claude Code subscription, no API key needed.
"""
import subprocess


def ask_claude(
    prompt: str,
    system: str = "",
    timeout: int = 60,
    model: str = "sonnet",
) -> str:
    """
    Send a prompt to Claude via the CLI using stdin pipe.

    Args:
        prompt: The prompt to send
        system: Optional system prompt
        timeout: Seconds before timeout (default 60)
        model: Model to use — "haiku" (fast/cheap), "sonnet", "opus"
    """
    if system:
        prompt = f"[System: {system}]\n\n{prompt}"

    cmd = ["/opt/homebrew/bin/claude", "-p", "--model", model]

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr}")

    return result.stdout.strip()
