import json
import re
import time
import html
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

TERMS = [
    '"不正アクセス"',
    '"情報漏洩" OR "情報流出"',
    '"サイバー攻撃" OR ランサムウェア',
    '"個人情報 漏えい"',
]


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_one(term):
    params = urlencode({
        "q": term,
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    })
    url = "https://news.google.com/rss/search?" + params
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 CyberNewsWatch/1.0"})
    with urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())

    results = []
    for item in root.findall("./channel/item"):
        source = item.find("source")
        results.append({
            "title": clean_text(item.findtext("title")) or "(タイトルなし)",
            "link": (item.findtext("link") or "").strip(),
            "date": (item.findtext("pubDate") or "").strip(),
            "source": clean_text(source.text if source is not None else "") or "Google ニュース",
            "description": clean_text(item.findtext("description")),
        })
    return results


def main():
    all_items = []
    for term in TERMS:
        try:
            all_items.extend(fetch_one(term))
            print("取得成功:", term)
        except Exception as error:
            print("取得失敗:", term, str(error))
        time.sleep(1)

    unique = []
    seen = set()
    for item in all_items:
        key = item["link"] or item["title"]
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    unique.sort(key=lambda item: item["date"], reverse=True)
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
