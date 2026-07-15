import logging
import secrets
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[tuple[str, bytes, str | None]] | None = None,
) -> bool:
    settings = get_settings()
    if not settings.smtp_enabled:
        logger.warning("SMTP disabled — email not sent to %s (subject: %s)", to_email, subject)
        return False
    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("SMTP not configured — email not sent")
        return False

    msg = MIMEMultipart("mixed" if attachments else "alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    if attachments:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)
        for filename, content, mime in attachments:
            part = MIMEApplication(content, Name=filename)
            part.add_header("Content-Disposition", "attachment", filename=Path(filename).name)
            if mime:
                part.set_type(mime)
            msg.attach(part)
    else:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as exc:
        logger.exception("Failed to send email to %s: %s", to_email, exc)
        return False


def send_faculty_welcome_email(
    to_email: str,
    full_name: str,
    temporary_password: str,
    portal_url: str,
) -> bool:
    subject = "ECE Department Portal — Your login credentials"
    text = f"""Dear {full_name},

An account has been created for you on the Automation Portal.

Login URL: {portal_url}
Email: {to_email}
Temporary password: {temporary_password}

Please sign in and change your password from Profile / Settings.

This is a portal password — not your institutional email password.

Regards,
ECE Department Portal
"""
    html = f"""
<p>Dear {full_name},</p>
<p>Your portal account is ready.</p>
<ul>
  <li><strong>Login URL:</strong> <a href="{portal_url}">{portal_url}</a></li>
  <li><strong>Email:</strong> {to_email}</li>
  <li><strong>Temporary password:</strong> {temporary_password}</li>
</ul>
<p>Please sign in and <strong>change your password</strong> from Profile / Settings.</p>
<p><em>This is a portal password — not your Gmail/outlook password.</em></p>
"""
    return send_email(to_email, subject, text, html)


def generate_temporary_password(length: int = 12) -> str:
    """Generate a strong temporary password for reset emails."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_password_reset_email(
    to_email: str,
    full_name: str,
    temporary_password: str,
    portal_url: str,
) -> bool:
    subject = "ECE Department Portal — Temporary password"
    text = f"""Dear {full_name},

We received a request to reset your portal password.

Login URL: {portal_url}
Email: {to_email}
Temporary password: {temporary_password}

Please sign in and immediately change your password from Profile / Settings.

Regards,
ECE Department Portal
"""
    html = f"""
<p>Dear {full_name},</p>
<p>We received a request to reset your portal password.</p>
<ul>
  <li><strong>Login URL:</strong> <a href="{portal_url}">{portal_url}</a></li>
  <li><strong>Email:</strong> {to_email}</li>
  <li><strong>Temporary password:</strong> {temporary_password}</li>
</ul>
<p>Please sign in and <strong>change your password immediately</strong> from Profile / Settings.</p>
"""
    return send_email(to_email, subject, text, html)
