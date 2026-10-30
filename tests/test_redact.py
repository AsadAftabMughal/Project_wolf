from wolf.chat.redact import redact, safe_message

FAKE_TOKEN = "A" * 24 + "." + "B" * 6 + "." + "C" * 27


def test_discord_token_redacted():
    out = redact("token is " + FAKE_TOKEN + " ok")
    assert FAKE_TOKEN not in out
    assert "[REDACTED]" in out


def test_key_value_keeps_name_hides_value():
    out = redact("api_key=abc123 and client_secret: xyz789")
    assert "api_key" in out and "client_secret" in out
    assert "abc123" not in out and "xyz789" not in out


def test_bearer_redacted():
    out = redact("Authorization: Bearer abc.def.ghi")
    assert "abc.def.ghi" not in out


def test_long_hex_redacted():
    h = "0123456789abcdef" * 2
    assert h not in redact("hash " + h)


def test_exact_secret_redacted():
    assert "hunter22secret" not in redact("pw hunter22secret", ("hunter22secret",))


def test_short_secret_ignored():
    assert redact("about abc", ("ab",)) == "about abc"


def test_normal_text_unchanged():
    msg = "BLOCKED: RISK_TOO_HIGH on XAUUSD 0.03 lots, spread 0.30"
    assert redact(msg) == msg


def test_mentions_defused():
    out = safe_message("alert @everyone and @here")
    assert "@everyone" not in out and "@here" not in out


def test_truncated():
    out = safe_message("word " * 1000, limit=100)
    assert len(out) <= 100
    assert out.endswith("...")
