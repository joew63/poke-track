import os
import smtplib
from email.mime.text import MIMEText

from ..models import StockResult, StockStatus
from .base import Notifier

REQUIRED_VARS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "EMAIL_TO"]


class EmailNotifier(Notifier):
    def is_configured(self) -> bool:
        return all(os.environ.get(v) for v in REQUIRED_VARS)

    def send(self, result: StockResult) -> None:
        product = result.product
        if result.status == StockStatus.IN_STOCK:
            subject = f"In stock: {product.name}"
        else:
            subject = f"{product.name}: {result.status.value}"

        body = f"{product.name}\nStatus: {result.status.value}\n{product.url}\n"
        if result.price:
            body += f"Price: {result.price}\n"
        if result.detail:
            body += f"\nDetail: {result.detail}\n"

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.environ["SMTP_USER"]
        msg["To"] = os.environ["EMAIL_TO"]

        host = os.environ["SMTP_HOST"]
        port = int(os.environ["SMTP_PORT"])
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.sendmail(os.environ["SMTP_USER"], [os.environ["EMAIL_TO"]], msg.as_string())
