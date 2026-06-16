"""Report-ready email — fires when the RQ generation job completes
successfully.  Best-effort: errors are logged, never raised.  Skipped
silently when:

  * the athlete isn't linked to a user account (parent-only trainees),
  * the linked user has no email on file,
  * the user has ``monthly_report = false`` in their notification prefs.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Literal

import aiosmtplib
import asyncpg

from src.config import settings
from src.invites.og_landing import _superuser_dsn

log = logging.getLogger(__name__)

ReportEmailLocale = Literal["en", "id"]


_SUBJECT = {
    "en": "Your Coachito report is ready",
    "id": "Laporan Coachito-mu siap",
}

_GREETING = {
    "en": "Hi {name},",
    "id": "Halo {name},",
}

_BODY_P1 = {
    "en": (
        "Your latest progress report ({period}) is ready.  Tap the button "
        "below to open it."
    ),
    "id": (
        "Laporan progres kamu ({period}) sudah siap. Ketuk tombol di bawah "
        "untuk membukanya."
    ),
}

_CTA = {"en": "View report", "id": "Lihat laporan"}

_FALLBACK_LINK_LABEL = {
    "en": "Or paste this link in your browser:",
    "id": "Atau salin tautan ini di browser:",
}

_FOOTER_PREF_NOTE = {
    "en": (
        "You're receiving this because monthly-report alerts are on.  "
        "Turn them off any time in your Coachito profile."
    ),
    "id": (
        "Kamu menerima email ini karena notifikasi laporan bulanan aktif.  "
        "Matikan kapan saja di profil Coachito kamu."
    ),
}


def _build_email(
    *,
    to_email: str,
    locale: ReportEmailLocale,
    trainee_first_name: str,
    period_label: str,
    pdf_url: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = _SUBJECT[locale]

    greet = _GREETING[locale].format(name=trainee_first_name)
    body = _BODY_P1[locale].format(period=period_label)

    msg.set_content(
        f"{greet}\n\n"
        f"{body}\n\n"
        f"{pdf_url}\n\n"
        f"— Coachito\n\n"
        f"{_FOOTER_PREF_NOTE[locale]}"
    )
    msg.add_alternative(
        f"""<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,sans-serif;background:#FBF6EC;color:#1F1B16;max-width:480px;margin:0 auto;padding:24px;">
  <p>{greet}</p>
  <p>{body}</p>
  <p style="margin:24px 0;"><a href="{pdf_url}" style="display:inline-block;padding:12px 20px;background:#C66B47;color:#F5EBD9;text-decoration:none;border-radius:8px;font-weight:500;">{_CTA[locale]}</a></p>
  <p style="color:#3A332B;font-size:13px;">{_FALLBACK_LINK_LABEL[locale]}<br><span style="word-break:break-all;">{pdf_url}</span></p>
  <p style="color:#8A8278;font-size:12px;margin-top:32px;">{_FOOTER_PREF_NOTE[locale]}</p>
</body></html>""",
        subtype="html",
    )
    return msg


async def maybe_send_report_ready_email(*, report_id: str) -> bool:
    """Look up the report + trainee user + notification pref and send the
    email if everything aligns.  Returns True iff an email was sent.

    Opens its own asyncpg connection — runs from the RQ worker context,
    which doesn't share the API process's SQLAlchemy engine.
    """
    try:
        conn = await asyncpg.connect(_superuser_dsn())
    except Exception:
        log.exception("report_email_db_connect_failed", extra={"report_id": report_id})
        return False
    try:
        row = await conn.fetchrow(
            """
            SELECT r.pdf_url,
                   r.period_start,
                   r.period_end,
                   r.session_id IS NOT NULL AS is_session_report,
                   a.display_name AS trainee_display_name,
                   u.email,
                   u.preferred_locale,
                   COALESCE(np.monthly_report, TRUE) AS monthly_report_on
            FROM reports r
            JOIN athletes a ON a.id = r.athlete_id
            LEFT JOIN users u ON u.id = a.user_id
            LEFT JOIN user_notification_prefs np ON np.user_id = u.id
            WHERE r.id = $1
            """,
            report_id,
        )
    finally:
        await conn.close()

    if row is None:
        log.warning("report_email_no_row", extra={"report_id": report_id})
        return False
    if row["email"] is None:
        # Parent-only trainees / not-yet-claimed invites.
        return False
    if not row["monthly_report_on"]:
        log.info(
            "report_email_skipped_pref_off",
            extra={"report_id": report_id},
        )
        return False
    if not row["pdf_url"]:
        log.warning("report_email_missing_pdf_url", extra={"report_id": report_id})
        return False

    locale: ReportEmailLocale = (
        "id" if row["preferred_locale"] == "id" else "en"
    )
    full_name = (row["trainee_display_name"] or "").strip()
    first_name = full_name.split()[0] if full_name else "there"
    if row["is_session_report"]:
        period_label = row["period_start"].strftime("%-d %b %Y")
    else:
        period_label = row["period_end"].strftime("%B %Y")

    msg = _build_email(
        to_email=row["email"],
        locale=locale,
        trainee_first_name=first_name,
        period_label=period_label,
        pdf_url=row["pdf_url"],
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
        )
    except Exception:
        log.exception("report_email_send_failed", extra={"report_id": report_id})
        return False
    log.info("report_email_sent", extra={"report_id": report_id})
    return True
