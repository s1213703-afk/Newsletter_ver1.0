import feedparser
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECV_ADDRESS       = os.environ["RECV_ADDRESS"].split(",")

KEYWORDS = ["팩케이크", "커브얼라이브", "이현이", "두피", "탈모"]

NAVER_RSS_FEEDS = {
    "정치":    "https://news.naver.com/main/rss/politics.nhn",
    "경제":    "https://news.naver.com/main/rss/economy.nhn",
    "사회":    "https://news.naver.com/main/rss/society.nhn",
    "생활문화": "https://news.naver.com/main/rss/life.nhn",
    "IT과학":  "https://news.naver.com/main/rss/it.nhn",
    "세계":    "https://news.naver.com/main/rss/world.nhn",
}

SELECTED_CATEGORIES = ["생활문화", "사회"]
FALLBACK_CATEGORY   = "생활문화"
FALLBACK_COUNT      = 5
MAX_ARTICLES_PER_MAIL = 20

sent_urls = set()

def fetch_news():
    matched = []
    for cat in SELECTED_CATEGORIES:
        if cat not in NAVER_RSS_FEEDS:
            continue
        try:
            feed = feedparser.parse(NAVER_RSS_FEEDS[cat])
            for entry in feed.entries:
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                pub     = entry.get("published", "")
                if link in sent_urls:
                    continue
                text = title + " " + summary
                if any(kw.lower() in text.lower() for kw in KEYWORDS):
                    matched.append({
                        "category": cat, "title": title,
                        "link": link, "pub": pub,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "is_fallback": False,
                    })
        except Exception as e:
            print(f"RSS 오류 ({cat}): {e}")
    return matched

def fetch_fallback():
    articles = []
    try:
        feed = feedparser.parse(NAVER_RSS_FEEDS[FALLBACK_CATEGORY])
        for entry in feed.entries[:FALLBACK_COUNT]:
            articles.append({
                "category": f"{FALLBACK_CATEGORY} (추천)",
                "title":    entry.get("title", "").strip(),
                "link":     entry.get("link", "").strip(),
                "summary":  entry.get("summary", "")[:150],
                "pub":      entry.get("published", ""),
                "is_fallback": True,
            })
        print(f"대체 기사 {len(articles)}건 사용")
    except Exception as e:
        print(f"대체 기사 수집 오류: {e}")
    return articles

def build_html(articles, is_fallback):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    header_color = "#e8891a" if is_fallback else "#1a73e8"
    header_text  = "오늘의 뷰티 추천 뉴스" if is_fallback else "뉴스 알림"
    sub_text     = f"키워드 매칭 없음 · {FALLBACK_CATEGORY} 최신 {FALLBACK_COUNT}건" if is_fallback else f"키워드: {', '.join(KEYWORDS)}"
    rows = ""
    for i, art in enumerate(articles, 1):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        rows += f"""
        <tr style="background:{bg}">
          <td style="padding:6px 10px; color:#888; font-size:12px; white-space:nowrap">{art['category']}</td>
          <td style="padding:6px 10px">
            <a href="{art['link']}" style="color:#1a73e8; text-decoration:none; font-weight:bold">{art['title']}</a>
            <div style="color:#555; font-size:12px; margin-top:3px">{art['summary']}</div>
          </td>
          <td style="padding:6px 10px; color:#aaa; font-size:11px; white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
        </tr>"""
    return f"""<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
      <div style="background:{header_color};color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">📰 {header_text}</h2>
        <p style="margin:4px 0 0;font-size:13px;opacity:0.85">{now} 기준 · {sub_text}</p>
      </div>
      <table width="100%" cellspacing="0" cellpadding="0"
             style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
        <thead><tr style="background:#f1f3f4">
          <th style="padding:8px 10px;text-align:left;font-size:12px">카테고리</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">기사</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">시간</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="color:#aaa;font-size:11px;text-align:center;margin-top:12px">
        총 {len(articles)}건 · GitHub Actions 뉴스봇
      </p>
    </body></html>"""

def send_email(articles, is_fallback):
    now = datetime.now().strftime("%m/%d %H:%M")
    subject = (f"📰 오늘의 뷰티 추천 [{now}] {len(articles)}건"
               if is_fallback else f"📰 뉴스 알림 [{now}] {len(articles)}건")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = ", ".join(RECV_ADDRESS)
    msg.attach(MIMEText(build_html(articles, is_fallback), "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_ADDRESS, RECV_ADDRESS, msg.as_string())
    print(f"✅ 메일 전송 완료: {len(articles)}건")

if __name__ == "__main__":
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 시작")
    articles = fetch_news()
    print(f"키워드 매칭: {len(articles)}건")
    if articles:
        send_email(articles, is_fallback=False)
    else:
        print("매칭 없음 → 대체 기사 수집")
        fallback = fetch_fallback()
        if fallback:
            send_email(fallback, is_fallback=True)
        else:
            print("대체 기사도 없음")
