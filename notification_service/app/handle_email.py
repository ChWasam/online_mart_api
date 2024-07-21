""" Helper functions for Notification Service """
import logging
import smtplib
from email.mime.text import MIMEText
from app import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def send_email(body: str, subject: str, user_email: str):
    try:
        sender_email = settings.FROM_EMAIL
        receiver_email = user_email
        password = settings.FROM_EMAIL_APP_PASSWORD
        subject = subject
        body = body

        # Create MIMEText object for message body
        message = MIMEText(body, "plain")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = receiver_email

        # Establish secure connection using SMTP_SSL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")