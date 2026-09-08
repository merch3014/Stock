"""Email notification for the Phase 4 scheduled scan.

Plain SMTP only — no third-party notification service — so it works with
whatever email account you already have (Gmail/Fastmail/etc. via an app
password, or your own mail server). All configuration comes from
environment variables so credentials never sit in code, a config file
checked into git, or shell history.

Required environment variables (all of them, or `email_notifier_from_env`
returns None so the caller can fall back to printing instead of crashing):

    SMTP_HOST       e.g. smtp.gmail.com
    SMTP_PORT       e.g. 587
    SMTP_USER       login/username for the SMTP server
    SMTP_PASSWORD   password or app password
    SMTP_FROM       "From" address
    SMTP_TO         "To" address (your own inbox, most likely)

Optional:
    SMTP_USE_TLS    "false"/"0"/"no" to disable STARTTLS (default: enabled)

See scheduled_scan.py for how this fits into the actual cron-triggered scan,
and README.md's "Scheduling it yourself" section for a crontab example.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Callable, Mapping

REQUIRED_ENV_VARS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_TO"]


def send_email(
    subject: str,
    body: str,
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_addr: str,
    to_addr: str,
    use_tls: bool = True,
    smtp_cls: type = smtplib.SMTP,
) -> None:
    """Send a plain-text email via SMTP. `smtp_cls` is injectable (tests
    pass a fake) so nothing here ever needs a real SMTP server to test.
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)

    with smtp_cls(host, port, timeout=30) as server:
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.send_message(message)


def email_notifier_from_env(
    env: Mapping[str, str] | None = None, *, smtp_cls: type = smtplib.SMTP
) -> Callable[[str, str], None] | None:
    """Build a `notifier(subject, body)` callable from SMTP_* environment
    variables, or return None if any required one is missing — the caller
    decides what to do then (scheduled_scan.py falls back to printing).
    """
    env = env if env is not None else os.environ
    if any(not env.get(name) for name in REQUIRED_ENV_VARS):
        return None

    host = env["SMTP_HOST"]
    port = int(env["SMTP_PORT"])
    username = env["SMTP_USER"]
    password = env["SMTP_PASSWORD"]
    from_addr = env["SMTP_FROM"]
    to_addr = env["SMTP_TO"]
    use_tls = env.get("SMTP_USE_TLS", "true").strip().lower() not in ("false", "0", "no")

    def notifier(subject: str, body: str) -> None:
        send_email(
            subject,
            body,
            host=host,
            port=port,
            username=username,
            password=password,
            from_addr=from_addr,
            to_addr=to_addr,
            use_tls=use_tls,
            smtp_cls=smtp_cls,
        )

    return notifier


def console_notifier(subject: str, body: str) -> None:
    """Fallback notifier: just print. Always works, zero config — what
    `scheduled_scan.py` uses without `--email`.
    """
    print(f"Subject: {subject}\n")
    print(body)
