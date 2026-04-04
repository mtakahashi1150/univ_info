#!/usr/bin/env python3
"""
差分検知時のメール通知スクリプト

環境変数または .env から以下を読み込む：
  - GMAIL_ADDRESS: 送信元 Gmail アドレス
  - GMAIL_APP_PASSWORD: Gmail appパスワード
  - NOTIFY_TO_EMAIL: 通知先メールアドレス
"""

import os
import sys
import json
import smtplib
import logging
from pathlib import Path
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# dotenv をサポート
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = REPO_ROOT / 'data' / 'snapshots'
ACCUMULATED_FILE = REPO_ROOT / 'data' / 'accumulated.md'


class GmailNotifier:
    """Gmail 経由でメール通知を送る"""

    def __init__(
        self,
        gmail_address: str,
        gmail_app_password: str,
        notify_to_email: str
    ):
        self.gmail_address = gmail_address
        self.gmail_app_password = gmail_app_password
        self.notify_to_email = notify_to_email

    def build_notification_body(self) -> tuple[str, str]:
        """
        通知メールの本文を構築
        
        Returns:
            (主要内容の要約, 詳細情報)
        """
        snapshots = sorted(
            SNAPSHOTS_DIR.glob('*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        summary_lines = [
            "【大学オープンキャンパス情報更新通知】",
            "",
            f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "更新情報:",
            ""
        ]

        # 最新スナップショットから更新内容をサマリー
        for snapshot_path in snapshots[:5]:  # 最新5件
            try:
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    snapshot = json.load(f)
                    university = snapshot.get('university', '不明')
                    events = snapshot.get('events', [])
                    if events:
                        event = events[0]
                        summary_lines.append(
                            f"  • {university}: {event.get('title', '不明')} "
                            f"({event.get('date', '-')})"
                        )
            except Exception as e:
                logger.error(f"Error reading snapshot {snapshot_path}: {e}")

        summary_lines.extend([
            "",
            "詳細は「累積情報」を参照してください。",
            ""
        ])

        # 累積情報をサマリー
        if ACCUMULATED_FILE.exists():
            with open(ACCUMULATED_FILE, 'r', encoding='utf-8') as f:
                accumulated = f.read()
                # 最初の 50 行のみを含める
                accumulated_preview = '\n'.join(
                    accumulated.split('\n')[:20]
                ) + "\n\n... (詳細は GitHub を参照)"
        else:
            accumulated_preview = "(累積情報ファイルがまだ生成されていません)"

        body = '\n'.join(summary_lines)
        detailed = accumulated_preview

        return body, detailed

    def send_email(self, subject: str, body: str, detailed: str = "") -> bool:
        """
        Gmail SMTP でメール送信
        
        Args:
            subject: メールの件名
            body: 本文（簡易版）
            detailed: 詳細情報（オプション）
        
        Returns:
            送信成功時は True
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.gmail_address
            msg['To'] = self.notify_to_email

            # プレーンテキスト版
            text_content = body + "\n\n---\n\n" + detailed
            part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part)

            # SMTP で送信
            logger.info(f"Connecting to smtp.gmail.com...")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
                server.login(self.gmail_address, self.gmail_app_password)
                server.sendmail(
                    self.gmail_address,
                    self.notify_to_email,
                    msg.as_string()
                )

            logger.info(f"✓ Email sent to {self.notify_to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("✗ Gmail authentication failed. Check credentials.")
            return False
        except Exception as e:
            logger.error(f"✗ Failed to send email: {e}")
            return False


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("大学オープンキャンパス情報 - メール通知")
    logger.info("=" * 60)

    # 環境変数から設定を読み込む
    gmail_address = os.getenv('GMAIL_ADDRESS')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    notify_to_email = os.getenv('NOTIFY_TO_EMAIL')

    # 必須チェック
    if not all([gmail_address, gmail_app_password, notify_to_email]):
        logger.error(
            "✗ Missing required environment variables:\n"
            "  Set GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_TO_EMAIL"
        )
        return 1

    # 通知を構築・送信
    notifier = GmailNotifier(gmail_address, gmail_app_password, notify_to_email)
    summary, detailed = notifier.build_notification_body()

    subject = "[大学情報] オープンキャンパス情報更新"
    success = notifier.send_email(subject, summary, detailed)

    logger.info("=" * 60)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
