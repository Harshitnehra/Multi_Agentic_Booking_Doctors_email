"""
Notification service — sends email alerts to users on booking and cancellation.

Set these environment variables in your .env:
  SMTP_HOST     e.g. smtp.gmail.com
  SMTP_PORT     e.g. 587
  SMTP_USER     your sender email address
  SMTP_PASSWORD your email password or app-password
  NOTIFY_FROM   display name / address for From header (optional)
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _send_email(to_address: str, subject: str, body_html: str, body_text: str) -> bool:
    """Low-level helper — returns True on success, False on failure."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("NOTIFY_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials not configured — email notification skipped.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_address, msg.as_string())
        logger.info("Email sent to %s — %s", to_address, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


def _resolve_email(id_number: int) -> str | None:
    """
    Map a patient ID to their email address.
    Replace this stub with a real DB look-up in production.
    """
    # Example static mapping — replace with actual DB query
    patient_emails = {
        1000099: "patient99@example.com",
        1000048: "patient48@example.com",
        1000123: "patient123@example.com",
        1000036: "patient36@example.com",
        1000167: "patient167@example.com",
    }
    return patient_emails.get(id_number)


# ─── Public API ───────────────────────────────────────────────────────────────

def notify_booking(id_number: int, doctor_name: str, date_slot: str) -> str:
    """
    Send a booking-confirmation email to the patient.
    Returns a human-readable status string (used in agent responses).
    """
    email = _resolve_email(id_number)
    if not email:
        return f"(notification skipped — no email on file for ID {id_number})"

    subject = "MediAssist — Appointment Confirmed"
    body_text = (
        f"Dear Patient (ID: {id_number}),\n\n"
        f"Your appointment has been confirmed.\n"
        f"Doctor : {doctor_name.title()}\n"
        f"Date   : {date_slot}\n\n"
        "Please arrive 10 minutes early.\n\n"
        "— MediAssist Team"
    )
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
      <h2 style="color:#0077cc;">Appointment Confirmed ✅</h2>
      <p>Dear Patient <strong>(ID: {id_number})</strong>,</p>
      <table style="border-collapse:collapse;margin:12px 0;">
        <tr><td style="padding:4px 12px 4px 0;color:#666;">Doctor</td>
            <td style="padding:4px 0;"><strong>{doctor_name.title()}</strong></td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#666;">Date & Time</td>
            <td style="padding:4px 0;"><strong>{date_slot}</strong></td></tr>
      </table>
      <p>Please arrive <em>10 minutes early</em>.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
      <p style="color:#999;font-size:12px;">MediAssist AI · Doctor Appointment System</p>
    </body></html>
    """

    ok = _send_email(email, subject, body_html, body_text)
    if ok:
        return f"Confirmation email sent to {email}."
    return "(email notification failed — check SMTP settings)"


def notify_cancellation(id_number: int, doctor_name: str, date_slot: str) -> str:
    """
    Send a cancellation notification email to the patient.
    Returns a human-readable status string (used in agent responses).
    """
    email = _resolve_email(id_number)
    if not email:
        return f"(notification skipped — no email on file for ID {id_number})"

    subject = "MediAssist — Appointment Cancelled"
    body_text = (
        f"Dear Patient (ID: {id_number}),\n\n"
        f"Your appointment has been successfully cancelled.\n"
        f"Doctor : {doctor_name.title()}\n"
        f"Date   : {date_slot}\n\n"
        "If this was a mistake, please book a new appointment.\n\n"
        "— MediAssist Team"
    )
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
      <h2 style="color:#cc3300;">Appointment Cancelled ❌</h2>
      <p>Dear Patient <strong>(ID: {id_number})</strong>,</p>
      <table style="border-collapse:collapse;margin:12px 0;">
        <tr><td style="padding:4px 12px 4px 0;color:#666;">Doctor</td>
            <td style="padding:4px 0;"><strong>{doctor_name.title()}</strong></td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#666;">Date & Time</td>
            <td style="padding:4px 0;"><strong>{date_slot}</strong></td></tr>
      </table>
      <p>If this was a mistake, please <a href="#" style="color:#0077cc;">book a new appointment</a>.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
      <p style="color:#999;font-size:12px;">MediAssist AI · Doctor Appointment System</p>
    </body></html>
    """

    ok = _send_email(email, subject, body_html, body_text)
    if ok:
        return f"Cancellation email sent to {email}."
    return "(email notification failed — check SMTP settings)"