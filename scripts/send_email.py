from __future__ import annotations

import os
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DOCX_ATTACHMENT_PATH = PROJECT_ROOT / "output" / "daily_lesson.docx"
DOCX_ATTACHMENT_DISPLAY_PATH = Path("output") / "daily_lesson.docx"
MAX_SEND_ATTEMPTS = 5
SEND_RETRY_SECONDS = 30


def load_simple_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    config: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid config line {line_number}: {raw_line}")
        key, value = line.split(":", 1)
        config[key.strip()] = value.strip().strip("'\"")
    return config


def require_config(config: dict[str, str], key: str) -> str:
    value = config.get(key, "").strip()
    if not value:
        raise ValueError(f"config.yaml is missing {key}")
    return value


def validate_email(value: str, field_name: str) -> None:
    if value == "your_gmail@gmail.com" or "@" not in value:
        raise ValueError(f"Please set {field_name} in config.yaml to your real Gmail address.")


def build_message(sender_email: str, receiver_email: str, attachment_path: Path) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "DELE B2 每日学习"
    message["Message-ID"] = make_msgid(domain="dele-b2-auto-study.local")
    message.set_content("今日 DELE B2 学习内容见附件。")
    message.add_attachment(
        attachment_path.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=attachment_path.name,
    )
    return message


def send_email(config: dict[str, str]) -> None:
    sender_email = require_config(config, "sender_email")
    receiver_email = require_config(config, "receiver_email")
    smtp_server = require_config(config, "smtp_server")
    smtp_port = int(require_config(config, "smtp_port"))
    require_config(config, "output_path")

    validate_email(sender_email, "sender_email")
    validate_email(receiver_email, "receiver_email")

    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_app_password:
        raise RuntimeError("GMAIL_APP_PASSWORD environment variable is not set.")

    if not DOCX_ATTACHMENT_PATH.exists():
        raise FileNotFoundError(f"缺少 {DOCX_ATTACHMENT_DISPLAY_PATH}，请先运行 python3 scripts/generate_word.py")

    message = build_message(sender_email, receiver_email, DOCX_ATTACHMENT_PATH)

    context = ssl.create_default_context()
    last_error: Exception | None = None
    for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(sender_email, gmail_app_password)
                server.send_message(message)
            return
        except OSError as exc:
            last_error = exc
            if attempt == MAX_SEND_ATTEMPTS:
                break
            print(f"邮件发送第 {attempt} 次失败，{SEND_RETRY_SECONDS} 秒后重试：{exc}", file=sys.stderr)
            time.sleep(SEND_RETRY_SECONDS)
    raise RuntimeError(f"邮件发送失败，已重试 {MAX_SEND_ATTEMPTS} 次：{last_error}")


def main() -> int:
    try:
        config = load_simple_yaml(CONFIG_PATH)
        send_email(config)
    except Exception as exc:
        print(f"邮件发送失败：{exc}", file=sys.stderr)
        return 1

    print(f"邮件发送成功，附件：{DOCX_ATTACHMENT_DISPLAY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
