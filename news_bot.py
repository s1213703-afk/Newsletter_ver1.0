import feedparser
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import socket

socket.setdefaulttimeout(10)

GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECV_ADDRESS       = os.environ["RECV_ADDRESS"].split(",")

KEYWORDS = ["팩케이크", "커브얼라이브", "이현이", "두피", "탈모"]

GOOGLE_NEWS_RSS = {
    "색조":   "https://news.google.com/rss/search?q=색조화장품&hl=ko&gl=KR&ceid=KR:ko",
    "기초":   "https://news.google.com/rss/search?q=기초화장품&hl=ko&gl=KR&ceid=KR:ko",
    "건기식": "https://news.google.com/rss/search?q=건강기능식품+뷰티&hl=ko&gl=KR&ceid=KR:ko",
    "탈모":   "https://news.google.com/rss/search?q=탈모&hl=ko&gl=KR&ceid=KR:ko",
    "두피":   "https://news.google.com/rss/search?q=두피케어&hl=ko&gl=KR&ceid=KR:ko",
}

FALLBACK_RSS     = "https://news.google.com/rss/search?q=뷰티+화장품&hl=ko&gl=KR&ceid=KR:ko"
MAX_PER_CATEGORY = 2
FALLBACK_COUNT   = 5


def fetch_news():
    results = {}
    seen = set()

    for cat, url in GOOGLE_NEWS_RSS.items():
        results[cat] = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if len(results[cat]) >= MAX_PER_CATEGORY:
                    break
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                pub     = entry.get("published", "")
                if link in seen:
                    continue
                text = title + " " + summary
                if any(kw.lower() in text.lower() for kw in KEYWORDS):
                    results[cat].append({
                        "category": f"뷰티_{cat}",
                        "title":    title,
                        "link":     link,
                        "summary":  summary[:150] + "..." if len(summary) > 150 else summary,
                        "pub":      pub,
                    })
                    seen.add(link)
            print(f"  [구글뉴스_{cat}] {len(results[cat])}건 매칭")
        except Exception as e:
            print(f"  ❌ 오류 ({cat}): {e}")

    return results


def fetch_fallback():
    articles = []
    seen = set()
    try:
        feed = feedparser.parse(FALLBACK_RSS)
        for entry in feed.entries[:FALLBACK_COUNT]:
            link = entry.get("link", "").strip()
            if link in seen:
                continue
            articles.append({
                "category": "뷰티 추천",
                "title":    entry.get("title", "").strip(),
                "link":     link,
                "summary":  entry.get("summary", "")[:150],
                "pub":      entry.get("published", ""),
            })
            seen.add(link)
        print(f"  대체 기사 {len(articles)}건 사용")
    except Exception as e:
        print(f"  ❌ 대체 기사 오류: {e}")
    return articles


def build_html(category_results, fallback_articles):
    now   = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    total = sum(len(v) for v in category_results.values())

    keyword_rows = ""
    for cat, articles in category_results.items():
        if articles:
            for i, art in enumerate(articles):
                bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
                keyword_rows += f"""
                <tr style="background:{bg}">
                  <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{art['category']}</td>
                  <td style="padding:6px 10px">
                    <a href="{art['link']}" style="color:#1a73e8;text-decoration:none;font-weight:bold">{art['title']}</a>
                    <div style="color:#555;font-size:12px;margin-top:3px">{art['summary']}</div>
                  </td>
                  <td style="padding:6px 10px;color:#aaa;font-size:11px;white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
                </tr>"""
        else:
            keyword_rows += f"""
            <tr style="background:#fff8f0">
              <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">뷰티_{cat}</td>
              <td style="padding:6px 10px;color:#bbb;font-size:12px">0건 — 해당 키워드 기사 없음</td>
              <td></td>
            </tr>"""

    fallback_section = ""
    if fallback_articles:
        fallback_rows = ""
        for i, art in enumerate(fallback_articles):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            fallback_rows += f"""
            <tr style="background:{bg}">
              <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{art['category']}</td>
              <td style="padding:6px 10px">
                <a href="{art['link']}" style="color:#e8891a;text-decoration:none;font-weight:bold">{art['title']}</a>
                <div style="color:#555;font-size:12px;margin-top:3px">{art['summary']}</div>
              </td>
              <td style="padding:6px 10px;color:#aaa;font-size:11px;white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
            </tr>"""
        fallback_section = f"""
        <div style="margin-top:24px">
          <div style="background:#e8891a;color:white;padding:12px 20px;border-radius:8px 8px 0 0">
            <h3 style="margin:0;font-size:15px">📌 오늘의 뷰티 추천 뉴스</h3>
            <p style="margin:2px 0 0;font-size:12px;opacity:0.85">키워드 매칭 외 최신 뷰티 기사</p>
          </div>
          <table width="100%" cellspacing="0" cellpadding="0"
                 style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
            <tbody>{fallback_rows}</tbody>
          </table>
        </div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
      <div style="background:#1a73e8;color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">📰 뷰티 뉴스 알림</h2>
        <p style="margin:4px 0 0;font-size:13px;opacity:0.85">{now} 기준 · 키워드: {', '.join(KEYWORDS)} · 총 {total}건</p>
      </div>
      <table width="100%" cellspacing="0" cellpadding="0"
             style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
        <thead><tr style="background:#f1f3f4">
          <th style="padding:8px 10px;text-align:left;font-size:12px">카테고리</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">기사</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">시간</th>
        </tr></thead>
        <tbody>{keyword_rows}</tbody>
      </table>
      {fallback_section}
      <p style="color:#aaa;font-size:11px;text-align:center;margin-top:12px">
        GitHub Actions 뉴스봇
      </p>
    </body></html>"""


def send_email(category_results, fallback_articles):
    total   = sum(len(v) for v in category_results.values())
    now     = datetime.now().strftime("%m/%d %H:%M")
    subject = f"📰 뷰티 뉴스 알림 [{now}] 키워드 {total}건"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = GMAIL_ADDRESS            # 받는사람: 본인만 표시
    msg["Bcc"]     = ", ".join(RECV_ADDRESS)  # 나머지는 숨은참조

    msg.attach(MIMEText(build_html(category_results, fallback_articles), "html", "utf-8"))

    all_recipients = [GMAIL_ADDRESS] + RECV_ADDRESS  # 실제 전송 대상

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_ADDRESS, all_recipients, msg.as_string())
    print(f"✅ 메일 전송 완료: 키워드 {total}건 + 대체 {len(fallback_articles)}건")


if __name__ == "__main__":
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 시작")
    category_results  = fetch_news()
    fallback_articles = fetch_fallback()
    send_email(category_results, fallback_articles)
