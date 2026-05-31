from __future__ import annotations

import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import DAILY_OUTPUT_DIR, display_path, env


def build_message(sender: str, recipient: str, subject: str, text_body: str, html_body: str | None) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def send_gmail(message: EmailMessage, password: str, host: str = "smtp.gmail.com", port: int = 465) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(str(message["From"]), password)
        server.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send latest Spanish B1 consolidation and B2 bridge lesson via Gmail.")
    parser.add_argument("--lesson", type=Path, default=DAILY_OUTPUT_DIR / "latest_lesson.md")
    parser.add_argument("--html", type=Path, default=DAILY_OUTPUT_DIR / "latest_lesson.html")
    parser.add_argument("--subject-file", type=Path, default=DAILY_OUTPUT_DIR / "latest_subject.txt")
    parser.add_argument("--dry-run", action="store_true", help="只检查配置和邮件内容，不真正发送")
    args = parser.parse_args()

    sender = env("GMAIL_ADDRESS") or env("GMAIL_USER")
    recipient = env("GMAIL_RECIPIENT") or sender
    password = env("GMAIL_APP_PASSWORD")
    host = env("SMTP_HOST", "smtp.gmail.com")
    port = int(env("SMTP_PORT", "465") or "465")

    if not args.lesson.exists():
        raise SystemExit(f"缺少课程文件：{display_path(args.lesson)}")
    if not sender:
        raise SystemExit("缺少环境变量 GMAIL_ADDRESS（或 GMAIL_USER）。")
    if not recipient:
        raise SystemExit("缺少环境变量 GMAIL_RECIPIENT。")
    if not password and not args.dry_run:
        raise SystemExit("缺少环境变量 GMAIL_APP_PASSWORD。")

    text_body = args.lesson.read_text(encoding="utf-8")
    html_body = args.html.read_text(encoding="utf-8") if args.html.exists() else None
    subject = (
        args.subject_file.read_text(encoding="utf-8").strip()
        if args.subject_file.exists()
        else "西语 B1 巩固与 B2 过渡每日学习"
    )
    message = build_message(sender, recipient, subject, text_body, html_body)

    if args.dry_run:
        print(f"邮件检查通过：From={sender}, To={recipient}, Subject={subject}, Bytes={len(text_body.encode('utf-8'))}")
        return 0

    send_gmail(message, password, host=host or "smtp.gmail.com", port=port)
    print(f"已发送：{subject} -> {recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
