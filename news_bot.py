import feedparser
import smtplib
import os
import socket
from urllib.parse import quote
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

socket.setdefaulttimeout(10)

GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECV_ADDRESS       = os.environ["RECV_ADDRESS"].split(",")

MAX_PER_CATEGORY = 2     # 카테고리별 최대 기사 수
FALLBACK_COUNT   = 5     # 추천 뉴스 수
WINDOW           = "3d"  # 최근 며칠 기사만 (예: 3d, 7d, 30d)


def gnews(query):
    q = quote(f"{query} when:{WINDOW}")
    return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"


# 카테고리: (검색어, 본문 필터 키워드)
SOURCES = {
    "넥스체인지": (
        "넥스체인지",
        ["넥스체인지"],
    ),
    "조각투자": (
        "조각투자 증권",
        ["조각투자", "토큰증권", "STO", "디지털증권", "투자계약증권", "수익증권"],
    ),
    "넥스트레이드": (
        "넥스트레이드",
        ["넥스트레이드", "NXT", "대체거래소"],
    ),
    "KDX": (
        "KDX 한국거래소 조각투자",
        ["KDX", "한국거래소", "KRX"],
    ),
    "장외거래소": (
        "장외거래소",
        ["장외거래소", "장외시장", "유통플랫폼", "장외거래"],
    ),
    "관련법안": (
        "조각투자 자본시장법 개정",
        ["자본시장법", "전자증권법", "조각투자", "토큰증권", "장외거래",
         "금융위원회", "증권선물위원회", "금융감독원", "법안", "개정안", "가이드라인"],
    ),
    "정유신 대표": (
        "정유신 대표",
        ["정유신"],
    ),
    "정중락 대표": (
        "정중락 대표",
        ["정중락"],
    ),
    "디지털자산": (
        "디지털자산",
        ["디지털자산", "디지털 자산", "가상자산", "스테이블코인"],
    ),
    "디지털자산 법안": (
        "디지털자산기본법 개정",
        ["디지털자산기본법", "가상자산이용자보호법", "디지털자산", "디지털 자산",
         "가상자산", "스테이블코인", "법안", "개정안", "금융위원회"],
    ),
}

FALLBACK_RSS = gnews("조각투자 장외거래소")


def fetch_news():
    results = {}
    seen = set()
    for cat, (query, kws) in SOURCES.items():
        results[cat] = []
        try:
            feed = feedparser.parse(gnews(query))
            for entry in feed.entries:
                if len(results[cat]) >= MAX_PER_CATEGORY:
                    break
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                pub     = entry.get("published", "")
                if link in seen:
                    continue
                text = (title + " " + summary).lower()
                if any(kw.lower() in text for kw in kws):
                    results[cat].append({
                        "category": cat,
                        "title":    title,
                        "link":     link,
                        "summary":  summary[:150] + "..." if len(summary) > 150 else summary,
                        "pub":      pub,
                    })
                    seen.add(link)
            print(f"  [{cat}] {len(results[cat])}건 매칭")
        except Exception as e:
            print(f"  ❌ 오류 ({cat}): {e}")
    return results


def fetch_fallback():
    articles = []
    try:
        feed = feedparser.parse(FALLBACK_RSS)
        for entry in feed.entries[:FALLBACK_COUNT]:
            articles.append({
                "category": "추천",
                "title":    entry.get("title", "").strip(),
                "link":     entry.get("link", "").strip(),
                "summary":  entry.get("summary", "")[:150],
                "pub":      entry.get("published", ""),
            })
        print(f"  추천 기사 {len(articles)}건")
    except Exception as e:
        print(f"  ❌ 추천 기사 오류: {e}")
    return articles


def build_html(category_results, fallback_articles):
    now   = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    total = sum(len(v) for v in category_results.values())

    rows = ""
    for cat, articles in category_results.items():
        if articles:
            for i, art in enumerate(articles):
                bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
                rows += f"""
                <tr style="background:{bg}">
                  <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{art['category']}</td>
                  <td style="padding:6px 10px">
                    <a href="{art['link']}" style="color:#1a73e8;text-decoration:none;font-weight:bold">{art['title']}</a>
                    <div style="color:#555;font-size:12px;margin-top:3px">{art['summary']}</div>
                  </td>
                  <td style="padding:6px 10px;color:#aaa;font-size:11px;white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
                </tr>"""
        else:
            rows += f"""
            <tr style="background:#fff8f0">
              <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{cat}</td>
              <td style="padding:6px 10px;color:#bbb;font-size:12px">0건 — 최근 {WINDOW} 내 해당 기사 없음</td>
              <td></td>
            </tr>"""

    fallback_section = ""
    if fallback_articles:
        frows = ""
        for i, art in enumerate(fallback_articles):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            frows += f"""
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
            <h3 style="margin:0;font-size:15px">📌 조각투자·장외거래소 추천 뉴스</h3>
          </div>
          <table width="100%" cellspacing="0" cellpadding="0"
                 style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
            <tbody>{frows}</tbody>
          </table>
        </div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
      <div style="background:#0f4c81;color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">📈 조각투자·장외거래소·디지털자산 뉴스 알림</h2>
        <p style="margin:4px 0 0;font-size:13px;opacity:0.85">{now} 기준 · 최근 {WINDOW} · 총 {total}건</p>
      </div>
      <table width="100%" cellspacing="0" cellpadding="0"
             style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
        <thead><tr style="background:#f1f3f4">
          <th style="padding:8px 10px;text-align:left;font-size:12px">구분</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">기사</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">시간</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
      {fallback_section}
      <p style="color:#aaa;font-size:11px;text-align:center;margin-top:12px">GitHub Actions 뉴스봇</p>
    </body></html>"""


def send_email(category_results, fallback_articles):
    total = sum(len(v) for v in category_results.values())
    now   = datetime.now().strftime("%m/%d %H:%M")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 조각투자·디지털자산 뉴스 [{now}] {total}건"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = GMAIL_ADDRESS
    msg["Bcc"]     = ", ".join(RECV_ADDRESS)
    msg.attach(MIMEText(build_html(category_results, fallback_articles), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_ADDRESS, [GMAIL_ADDRESS] + RECV_ADDRESS, msg.as_string())
    print(f"✅ 메일 전송 완료: {total}건")


if __name__ == "__main__":
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 시작")
    results  = fetch_news()
    fallback = fetch_fallback()
    send_email(results, fallback)
