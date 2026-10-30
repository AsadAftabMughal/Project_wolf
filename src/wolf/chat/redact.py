import re

_DISCORD = re.compile(
    r"[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_KV = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:token|secret|password|passwd|api[_-]?key)"
    r"[A-Za-z0-9_]*)\s*[=:]\s*\S+")
_HEX = re.compile(r"\b[A-Fa-f0-9]{32,}\b")
_OPAQUE = re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}")


def redact(text, secrets=()):
    """Remove anything that looks like a credential. Errs on the side of hiding."""
    out = text
    for s in secrets:
        if s and len(s) >= 6:
            out = out.replace(s, "[REDACTED]")
    out = _DISCORD.sub("[REDACTED]", out)
    out = _BEARER.sub("Bearer [REDACTED]", out)
    out = _KV.sub(lambda m: m.group(1) + "=[REDACTED]", out)
    out = _HEX.sub("[REDACTED]", out)
    out = _OPAQUE.sub("[REDACTED]", out)
    return out


def safe_message(text, secrets=(), limit=1800):
    """Redact, defuse @mentions, and stay under Discord's 2000 character cap."""
    out = redact(text, secrets).replace("@", "@\u200b")
    if len(out) > limit:
        out = out[: limit - 3] + "..."
    return out
