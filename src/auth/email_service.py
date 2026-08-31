"""QQ 邮箱 SMTP 发送验证码邮件。"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.util.config import SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER


def send_vcode_email(to_email: str, code: str):
    """发送 6 位验证码邮件（SSL 465）。"""
    subject = "帕姆小助手 - 登录验证码"
    body = (
        f"您好：\n\n"
        f"您的登录验证码是：{code}\n\n"
        f"验证码 5 分钟内有效，请勿泄露给他人。\n"
        f"如果不是您本人的操作，请忽略本邮件。\n\n"
        f"—— 帕姆小助手"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
