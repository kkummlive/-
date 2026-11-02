"""조달청 나라장터 용역 입찰공고를 모아 docs/index.html 대시보드를 만든다."""
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import EXCLUDE_KEYWORDS, INCLUDE_KEYWORDS, LOOKBACK_DAYS  # noqa: E402

KST = timezone(timedelta(hours=9))
URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"
OUT = Path(__file__).resolve().parent.parent / "docs"


def fetch_all(key, start, end):
    items, page = [], 1
    while True:
        params = {
            "ServiceKey": key, "type": "json", "inqryDiv": "1",
            "inqryBgnDt": start.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end.strftime("%Y%m%d%H%M"),
            "numOfRows": 999, "pageNo": page,
        }
        r = requests.get(URL, params=params, timeout=60)
        r.raise_for_status()
        try:
            body = r.json()["response"]["body"]
        except (ValueError, KeyError):
            raise SystemExit(f"API 응답 오류: {r.text[:300]}")
        batch = body.get("items") or []
        if isinstance(batch, dict):
            batch = batch.get("item", [])
        if isinstance(batch, dict):
            batch = [batch]
        items += batch
        if len(items) >= int(body.get("totalCount", 0)) or not batch:
            return items
        page += 1


def parse_dt(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d%H%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=KST)
        except (TypeError, ValueError):
            pass
    return None


def won(v):
    try:
        n = int(float(v))
        return f"{n:,}원" if n else "-"
    except (TypeError, ValueError):
        return "-"


def main():
    key = os.environ.get("G2B_SERVICE_KEY")
    if not key:
        raise SystemExit("G2B_SERVICE_KEY(공공데이터포털 인증키)가 설정되지 않았습니다.")
    now = datetime.now(KST)
    raw = fetch_all(key, now - timedelta(days=LOOKBACK_DAYS), now)

    seen, rows = set(), []
    for it in raw:
        name = it.get("bidNtceNm", "")
        no = f'{it.get("bidNtceNo", "")}-{it.get("bidNtceOrd", "")}'
        if no in seen:
            continue
        seen.add(no)
        close = parse_dt(it.get("bidClseDt"))
        if close and close < now:
            continue  # 마감된 공고 제외
        if any(k in name for k in EXCLUDE_KEYWORDS):
            continue
        if not any(k.lower() in name.lower() for k in INCLUDE_KEYWORDS):
            continue
        rows.append({
            "no": no, "name": name,
            "org": it.get("dminsttNm") or it.get("ntceInsttNm", ""),
            "posted": it.get("bidNtceDt", "")[:16],
            "close": close.strftime("%Y-%m-%d %H:%M") if close else "-",
            "dday": (close.date() - now.date()).days if close else 999,
            "price": won(it.get("asignBdgtAmt") or it.get("presmptPrce")),
            "method": it.get("cntrctCnclsMthdNm", ""),
            "url": it.get("bidNtceDtlUrl", ""),
        })
    rows.sort(key=lambda r: r["dday"])

    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "index.html").write_text(render(rows, now), encoding="utf-8")
    print(f"전체 {len(raw)}건 중 하이코두 관련 {len(rows)}건")


def render(rows, now):
    cards = []
    for r in rows:
        d = r["dday"]
        badge = "마감일 미상" if d == 999 else ("오늘 마감" if d == 0 else f"D-{d}")
        hot = " hot" if d <= 3 else ""
        e = html.escape
        cards.append(f"""<a class="card" href="{e(r['url'])}" target="_blank" rel="noopener" data-q="{e((r['name']+r['org']).lower())}">
<div class="top"><span class="badge{hot}">{badge}</span><span class="price">{e(r['price'])}</span></div>
<div class="name">{e(r['name'])}</div>
<div class="meta">{e(r['org'])} · {e(r['method'])}</div>
<div class="meta">공고 {e(r['posted'])} · 마감 {e(r['close'])} · {e(r['no'])}</div></a>""")
    body = "\n".join(cards) or '<p class="empty">현재 조건에 맞는 공고가 없습니다.</p>'
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>하이코두 입찰 대시보드</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1b1f24;--sub:#5f6b7a;--line:#e3e7ec;--acc:#2457d6;--hot:#d63b24}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111418;--card:#1a1f25;--ink:#e8ecf1;--sub:#9aa6b4;--line:#2a313a;--acc:#7aa2ff;--hot:#ff7a66}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}}
main{{max-width:860px;margin:0 auto;padding:20px 16px 40px}}h1{{font-size:21px;margin:0 0 4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:14px}}
input{{width:100%;padding:11px 13px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font-size:15px;margin-bottom:14px}}
.card{{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:10px;color:inherit;text-decoration:none}}
.card:hover{{border-color:var(--acc)}}.top{{display:flex;justify-content:space-between;margin-bottom:6px}}
.badge{{font-size:12px;font-weight:700;color:var(--acc)}}.badge.hot{{color:var(--hot)}}.price{{font-size:13px;font-weight:600}}
.name{{font-weight:650;margin-bottom:4px;word-break:keep-all}}.meta{{color:var(--sub);font-size:13px}}.empty{{color:var(--sub)}}
</style></head><body><main>
<h1>하이코두 입찰 대시보드</h1>
<div class="sub">최종 갱신 {now.strftime('%Y-%m-%d %H:%M')} (한국시간) · 관련 공고 {len(rows)}건 · 마감 임박순</div>
<input id="q" placeholder="공고명·기관명 검색" oninput="f(this.value)">
{body}
</main><script>
function f(v){{v=v.toLowerCase();document.querySelectorAll('.card').forEach(c=>c.style.display=c.dataset.q.includes(v)?'':'none')}}
</script></body></html>"""


if __name__ == "__main__":
    main()
