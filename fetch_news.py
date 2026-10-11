
import json
import re
import time
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

TERMS = [
    '"不正アクセス"',
    '"情報漏洩" OR "情報流出"',
    '"サイバー攻撃" OR ランサムウェア',
    '"個人情報 漏えい"',
]

FEEDS = [
    {
        "name": "JPCERT/CC",
        "url": "https://www.jpcert.or.jp/rss/jpcert-all.rdf",
    },
    {
        "name": "IPA",
        "url": "https://www.ipa.go.jp/security/rss/alert.rdf",
    },
    {
        "name": "Security NEXT",
        "url": "https://www.security-next.com/feed",
    },
]


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def child_text(element, *names):
    for child in element:
        tag = child.tag.split("}")[-1].lower()
        if tag in [name.lower() for name in names]:
            return "".join(child.itertext()).strip()
    return ""


def fetch_xml(url):
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 CyberNewsWatch/1.0"}
    )
    with urlopen(request, timeout=30) as response:
        return ET.fromstring(response.read())


def fetch_google_news(term):
    params = urlencode({
        "q": term,
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    })
    url = "https://news.google.com/rss/search?" + params
    root = fetch_xml(url)
    results = []

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue

        title = child_text(item, "title")
        link = child_text(item, "link")
        date = child_text(item, "pubDate")
        source = child_text(item, "source")

        results.append({
            "title": clean_text(title) or "(タイトルなし)",
            "link": link,
            "date": date,
            "source": clean_text(source) or "Google ニュース",
            "description": clean_text(
                child_text(item, "description")
            ),
        })

    return results


def fetch_rss_feed(feed):
    root = fetch_xml(feed["url"])
    results = []

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue

        title = clean_text(child_text(item, "title"))
        link = child_text(item, "link")
        date = child_text(
            item, "pubDate", "date", "published", "updated"
        )
        description = clean_text(
            child_text(item, "description", "summary")
        )

        if not title:
            continue

        results.append({
            "title": title,
            "link": link,
            "date": date,
            "source": feed["name"],
            "description": description,
        })

    return results


def date_timestamp(value):
    if not value:
        return 0

    try:
        return parsedate_to_datetime(value).timestamp()
    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).timestamp()
    except Exception:
        return 0


def main():
    all_items = []

    for term in TERMS:
        try:
            items = fetch_google_news(term)
            all_items.extend(items)
            print("Google ニュース取得:", term, len(items), "件")
        except Exception as error:
            print("Google ニュース取得失敗:", term, str(error))
        time.sleep(1)

    for feed in FEEDS:
        try:
            items = fetch_rss_feed(feed)
            all_items.extend(items)
            print(feed["name"], "取得成功:", len(items), "件")
        except Exception as error:
            print(feed["name"], "取得失敗:", str(error))
        time.sleep(1)

    unique = []
    seen = set()

    for item in all_items:
        key = item["link"] or item["title"]
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    unique.sort(
        key=lambda item: date_timestamp(item["date"]),
        reverse=True
    )

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": unique,
    }

    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("保存完了:", len(unique), "件")

    if not unique:
        raise RuntimeError("ニュースを取得できませんでした")


if __name__ == "__main__":
    main()

