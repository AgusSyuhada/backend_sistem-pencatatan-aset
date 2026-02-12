import os
import logging
from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)


def send_email_acs(
    to_email: str, subject: str, html_content: str = None, plain_content: str = None
) -> tuple[bool, str]:
    """
    Mengirim email menggunakan Azure Communication Services.
    Mengembalikan tuple (status_keberhasilan, pesan_detail).

    Args:
        to_email: Email tujuan
        subject: Subject email
        html_content: Konten HTML email (opsional)
        plain_content: Konten plain text email (opsional)
    """
    connection_string = os.getenv("ACS_CONNECTION_STRING")
    sender_address = os.getenv("ACS_SENDER_ADDRESS")

    if not connection_string:
        msg = "ACS_CONNECTION_STRING tidak di-set. Email tidak dikirim."
        logger.warning(msg)
        return False, msg

    if not sender_address:
        msg = "ACS_SENDER_ADDRESS tidak di-set. Email tidak dikirim."
        logger.warning(msg)
        return False, msg

    try:
        email_client = EmailClient.from_connection_string(connection_string)
        email_content = {"subject": subject}

        if plain_content:
            email_content["plainText"] = plain_content

        if html_content:
            email_content["html"] = html_content

        if not plain_content and not html_content:
            email_content["plainText"] = "Silakan lihat subject email."

        message_payload = {
            "senderAddress": sender_address,
            "recipients": {"to": [{"address": to_email}]},
            "content": email_content,
        }

        poller = email_client.begin_send(message_payload)
        result = poller.result()

        msg = f"Email terkirim ke {to_email}. Message ID: {result.get('messageId')}"
        logger.info(msg)
        return True, msg

    except Exception as e:
        msg = f"Gagal mengirim email ke {to_email}: {str(e)}"
        logger.error(msg, exc_info=True)
        return False, msg