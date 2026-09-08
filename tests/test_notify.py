from __future__ import annotations

from unittest.mock import MagicMock

from stock_analyzer.notify import console_notifier, email_notifier_from_env, send_email

_FULL_ENV = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "me@example.com",
    "SMTP_PASSWORD": "secret",
    "SMTP_FROM": "me@example.com",
    "SMTP_TO": "me@example.com",
}


def _fake_smtp_cls():
    instance = MagicMock()
    cls = MagicMock()
    cls.return_value.__enter__.return_value = instance
    return cls, instance


def test_send_email_builds_message_and_uses_tls_and_login():
    cls, instance = _fake_smtp_cls()

    send_email(
        "Subject line",
        "Body text",
        host="smtp.example.com",
        port=587,
        username="me@example.com",
        password="secret",
        from_addr="me@example.com",
        to_addr="you@example.com",
        smtp_cls=cls,
    )

    cls.assert_called_once_with("smtp.example.com", 587, timeout=30)
    instance.starttls.assert_called_once()
    instance.login.assert_called_once_with("me@example.com", "secret")
    instance.send_message.assert_called_once()
    sent = instance.send_message.call_args[0][0]
    assert sent["Subject"] == "Subject line"
    assert sent["From"] == "me@example.com"
    assert sent["To"] == "you@example.com"
    assert sent.get_content().strip() == "Body text"


def test_send_email_skips_starttls_when_use_tls_false():
    cls, instance = _fake_smtp_cls()

    send_email(
        "s", "b", host="h", port=25, username="u", password="p",
        from_addr="a@example.com", to_addr="b@example.com", use_tls=False, smtp_cls=cls,
    )

    instance.starttls.assert_not_called()
    instance.login.assert_called_once()


def test_email_notifier_from_env_returns_none_when_any_var_missing():
    incomplete = dict(_FULL_ENV)
    del incomplete["SMTP_PASSWORD"]
    assert email_notifier_from_env(env=incomplete) is None
    assert email_notifier_from_env(env={}) is None


def test_email_notifier_from_env_builds_working_notifier():
    cls, instance = _fake_smtp_cls()

    notifier = email_notifier_from_env(env=_FULL_ENV, smtp_cls=cls)
    assert notifier is not None

    notifier("Watchlist scan", "the digest text")

    cls.assert_called_once_with("smtp.example.com", 587, timeout=30)
    instance.login.assert_called_once_with("me@example.com", "secret")
    sent = instance.send_message.call_args[0][0]
    assert sent["Subject"] == "Watchlist scan"
    assert sent.get_content().strip() == "the digest text"


def test_email_notifier_from_env_respects_smtp_use_tls_false():
    cls, instance = _fake_smtp_cls()
    env = {**_FULL_ENV, "SMTP_USE_TLS": "false"}

    notifier = email_notifier_from_env(env=env, smtp_cls=cls)
    notifier("s", "b")

    instance.starttls.assert_not_called()


def test_console_notifier_prints_subject_and_body(capsys):
    console_notifier("My Subject", "My Body")
    out = capsys.readouterr().out
    assert "My Subject" in out
    assert "My Body" in out
