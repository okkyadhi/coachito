"""Outbound SMTP via aiosmtplib.

Dev: Mailpit at smtp://mailpit:1025 (anonymous, no auth).
Prod: Gmail SMTP (smtp.gmail.com:587 + App Password) or any other relay.
Configure via SMTP_* env vars in .env — see .env.example for Gmail setup.
"""

import asyncio
import logging
from email.message import EmailMessage
from typing import Literal

import aiosmtplib

from src.config import settings

# ── Brand palette (kept inline since most mail clients strip <style>) ──
_BG = "#FBF6EC"
_INK = "#1F1B16"
_INK_SOFT = "#3A332B"
_INK_MUTED = "#8A8278"
_CLAY = "#C66B47"  # CTA
_CREAM = "#F5EBD9"  # CTA text

_BODY_OPEN = (
    f'<body style="font-family:-apple-system,BlinkMacSystemFont,\'SF Pro Text\','
    f'system-ui,sans-serif;background:{_BG};color:{_INK};max-width:480px;'
    f'margin:0 auto;padding:24px;">'
)


def _cta_button(href: str, label: str) -> str:
    return (
        f'<p style="margin:24px 0;"><a href="{href}" '
        f'style="display:inline-block;padding:12px 20px;background:{_CLAY};'
        f'color:{_CREAM};text-decoration:none;border-radius:8px;'
        f'font-weight:500;">{label}</a></p>'
    )


def _link_fallback(link: str) -> str:
    return (
        f'<p style="color:{_INK_SOFT};font-size:13px;">Or paste this link in '
        f'your browser:<br><span style="word-break:break-all;">{link}</span>'
        f"</p>"
    )


def _signature() -> str:
    return f'<p style="color:{_INK_MUTED};font-size:12px;margin-top:32px;">— Coachito</p>'


_log = logging.getLogger(__name__)


async def _send(msg: EmailMessage) -> None:
    """Send via configured SMTP, with auth + TLS when env says so.

    Mailpit (dev): no auth, no TLS. Gmail: username + app-password +
    STARTTLS on 587 (or implicit TLS on 465).
    Hard timeout of 10 s so a missing/misconfigured SMTP host never
    blocks the request for a full TCP-timeout minute.
    """
    kwargs: dict[str, object] = {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "use_tls": settings.smtp_use_tls,
        "start_tls": settings.smtp_start_tls,
        "timeout": 10,
    }
    if settings.smtp_username:
        kwargs["username"] = settings.smtp_username
        kwargs["password"] = settings.smtp_password
    try:
        await aiosmtplib.send(msg, **kwargs)  # type: ignore[arg-type]
    except Exception as exc:
        _log.warning("SMTP send failed (to=%s): %s", msg["To"], exc)


# ── Magic-link (existing flow, retained) ─────────────────────────


async def send_magic_link_email(*, email: str, link: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg["Subject"] = "Your Coachito sign-in link"
    msg.set_content(
        "Hi,\n\n"
        "Tap the link below to sign in to Coachito. It expires in 15 minutes.\n\n"
        f"{link}\n\n"
        "If you didn't request this, you can safely ignore it.\n\n"
        "— Coachito"
    )
    msg.add_alternative(
        f"""<!doctype html>
<html>{_BODY_OPEN}
  <p>Hi,</p>
  <p>Tap the button below to sign in to Coachito. It expires in 15 minutes.</p>
  {_cta_button(link, "Sign in to Coachito")}
  {_link_fallback(link)}
  <p style="color:{_INK_SOFT};font-size:13px;">If you didn't request this, you can safely ignore it.</p>
  {_signature()}
</body></html>""",
        subtype="html",
    )
    await _send(msg)


# ── Welcome email (sent after self-signup) ──────────────────────


Role = Literal["coach", "club_admin"]


async def send_welcome_email(
    *,
    email: str,
    display_name: str,
    role: Role,
    workspace_name: str,
) -> None:
    cta_url = settings.web_url.rstrip("/") + (
        "/today" if role == "coach" else "/settings/coaches"
    )
    cta_label = "Open Coachito"
    role_blurb = (
        "Your solo coaching workspace is set up and ready."
        if role == "coach"
        else "Your club workspace is ready. Invite your first coach to get going."
    )
    next_blurb = (
        "Add your first trainee to start tracking sessions."
        if role == "coach"
        else "From Settings → Coaches you can send invite links via WhatsApp."
    )

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg["Subject"] = f"Welcome to Coachito, {display_name.split()[0]}"
    msg.set_content(
        f"Hi {display_name},\n\n"
        f"{role_blurb}\n\n"
        f'Workspace: "{workspace_name}".\n'
        f"{next_blurb}\n\n"
        f"Open the app: {cta_url}\n\n"
        "— Coachito"
    )
    msg.add_alternative(
        f"""<!doctype html>
<html>{_BODY_OPEN}
  <p>Hi {display_name},</p>
  <p>{role_blurb}</p>
  <p style="color:{_INK_SOFT};">Workspace: <strong>{workspace_name}</strong>.</p>
  <p>{next_blurb}</p>
  {_cta_button(cta_url, cta_label)}
  {_signature()}
</body></html>""",
        subtype="html",
    )
    await _send(msg)


# ── Password reset (forgot-password flow) ────────────────────────


async def send_password_reset_email(*, email: str, link: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg["Subject"] = "Reset your Coachito password"
    msg.set_content(
        "Hi,\n\n"
        "We got a request to reset your Coachito password. The link below "
        "expires in 30 minutes:\n\n"
        f"{link}\n\n"
        "If you didn't ask for this, ignore this email — your password stays "
        "the same.\n\n"
        "— Coachito"
    )
    msg.add_alternative(
        f"""<!doctype html>
<html>{_BODY_OPEN}
  <p>Hi,</p>
  <p>We got a request to reset your Coachito password. The link below expires in 30 minutes.</p>
  {_cta_button(link, "Reset password")}
  {_link_fallback(link)}
  <p style="color:{_INK_SOFT};font-size:13px;">If you didn't ask for this, ignore this email — your password stays the same.</p>
  {_signature()}
</body></html>""",
        subtype="html",
    )
    await _send(msg)
