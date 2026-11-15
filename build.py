#!/usr/bin/env python3
"""
build.py — 把 wiki/ 轉成 docs/ 靜態網站，並執行 lint 檢查。
規則來源：CLAUDE.md。修改本檔前先讀 CLAUDE.md 第 5、6、8 節。

用法：
  python build.py               建置網站（依建置時間自動判斷是否隱藏民調）
  python build.py --lint        只檢查，不輸出
  python build.py --no-polls    強制隱藏民調
  python build.py --date 2026-11-20   以指定日期建置（測試封關邏輯）
"""
import argparse
import html
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
OUT = ROOT / "docs"
ASSETS = ROOT / "assets"

SITE_NAME = "2026 縣市首長選舉資料庫"
SITE_TAGLINE = "22 縣市候選人．政見．民調．歷屆結果　中立整理"
TW = timezone(timedelta(hours=8))
ELECTION_DAY = date(2026, 11, 28)
BLACKOUT_START = datetime(2026, 11, 18, 0, 0, tzinfo=TW)
BLACKOUT_END = datetime(2026, 11, 28, 16, 0, tzinfo=TW)

SIX = ["taipei", "new-taipei", "taoyuan", "taichung", "tainan", "kaohsiung"]
OTHERS = ["keelung", "hsinchu-city", "hsinchu-county", "miaoli", "changhua", "nantou",
          "yunlin", "chiayi-city", "chiayi-county", "pingtung", "yilan", "hualien",
          "taitung", "penghu", "kinmen", "lienchiang"]
ORDER = SIX + OTHERS

# 導覽列（CLAUDE.md 第 6 節：新增頂層頁面要同時改這裡）
NAV = [("首頁", "index.html"), ("全國總覽", "overview.html"), ("六都", "six.html"),
       ("民調", "polls.html"), ("議題比較", "syntheses.html"), ("來源", "sources.html"),
       ("關於本站", "about.html")]

CANDIDATE_SECTIONS = ["基本資料", "參選歷程", "主要政見", "第三方評比", "來源與待補"]

WARNINGS = []
INC_TAG = '　<span class="tag">現任</span>'


def warn(msg):
    WARNINGS.append(msg)


# ───────────────────────── 讀取 ─────────────────────────
def read_page(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    else:
        meta, body = {}, text
    meta["_path"] = path
    meta["_body"] = body.strip()
    return meta


def load_all():
    sources = {s["id"]: s for s in yaml.safe_load((RAW / "sources.yaml").read_text(encoding="utf-8"))}
    cities = {p.stem: read_page(p) for p in (WIKI / "cities").glob("*.md")}
    cands = {p.stem: read_page(p) for p in (WIKI / "candidates").glob("*.md")}
    polls = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in (WIKI / "polls").glob("*.yaml")}
    synth = {p.stem: read_page(p) for p in (WIKI / "syntheses").glob("*.md")}
    pages = {p.stem: read_page(p) for p in WIKI.glob("*.md")}
    return sources, cities, cands, polls, synth, pages


# ───────────────────────── 渲染工具 ─────────────────────────
def esc(s):
    return html.escape(str(s)) if s is not None else ""


def party(p):
    return f'<span class="party">{esc(p)}</span>' if p else ""


def fmt_date(d):
    return d.isoformat() if isinstance(d, (date, datetime)) else (str(d) if d else "—")


def src_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


class Ctx:
    """單一頁面的渲染狀態：根目錄相對路徑與本頁引用到的來源。"""

    def __init__(self, sources, root, page_key):
        self.sources, self.root, self.page_key = sources, root, page_key
        self.cited = []

    def cite(self, sid):
        if sid not in self.sources:
            warn(f"{self.page_key}: 引用了不存在的來源 {sid}")
            return f"[{sid}?]"
        if sid not in self.cited:
            self.cited.append(sid)
        s = self.sources[sid]
        title = esc(f"{s['outlet']}｜{s['title']}")
        return f'<sup class="cite"><a href="{self.root}sources.html#{sid}" title="{title}">{sid}</a></sup>'

    def cites(self, v):
        return "".join(self.cite(s) for s in src_list(v))


def md_to_html(text, ctx):
    out = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    # callout：> [!note] 標題
    def callout(m):
        kind, title, rest = m.group(1).lower(), m.group(2).strip(), m.group(3)
        return (f'<aside class="callout {kind}"><p class="callout-title">{title}</p>'
                f'<p>{rest.strip()}</p></aside>')
    out = re.sub(r"<blockquote>\s*<p>\[!(\w+)\]\s*([^\n<]*)\n?(.*?)</p>\s*</blockquote>", callout, out, flags=re.S)
    # 站內 .md 連結 → .html
    out = re.sub(r'href="([^"#:]+)\.md(#[^"]*)?"', lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"', out)
    # 來源引用 [S012]
    out = re.sub(r"\[(S\d{3})\]", lambda m: ctx.cite(m.group(1)), out)
    return out


def page_html(title, body, ctx, updated=None, active=None):
    root = ctx.root
    on = ' class="on"'
    nav = "".join(
        f'<a href="{root}{href}"{on if href == active else ""}>{esc(label)}</a>' for label, href in NAV)
    today = BUILD_NOW.date()
    days = (ELECTION_DAY - today).days
    countdown = f"距投票日 {days} 天" if days > 0 else ("今日投票" if days == 0 else "已完成投票")
    cited = ""
    if ctx.cited:
        items = "".join(
            f'<li><a href="{root}sources.html#{sid}">{sid}</a>　{esc(ctx.sources[sid]["outlet"])}｜{esc(ctx.sources[sid]["title"])}</li>'
            for sid in ctx.cited)
        cited = f'<section class="page-sources"><h2>本頁來源</h2><ol>{items}</ol></section>'
    upd = f'<p class="updated">本頁更新：{fmt_date(updated)}</p>' if updated else ""
    return f"""<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}｜{SITE_NAME}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@600;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css">
</head>
<body>
<header class="masthead">
  <div class="dateline"><span>建置日期 {today.isoformat()}</span><span>投票日 2026-11-28（六）</span><span class="countdown">{countdown}</span></div>
  <a class="brand" href="{root}index.html">{SITE_NAME}</a>
  <p class="tagline">{SITE_TAGLINE}</p>
  <nav>{nav}</nav>
</header>
<main>
<h1 class="page-title">{esc(title)}</h1>
{upd}
{body}
{cited}
</main>
<footer>
  <p>資料截至各頁標示之更新日期；候選人名單、號次與開票結果以中央選舉委員會公告為準。本站不代表任何政黨或候選人。</p>
  <p><a href="{root}open-questions.html">待查清單</a>　<a href="{root}log.html">更新日誌</a>　<a href="{root}about.html">編輯原則</a></p>
</footer>
</body>
</html>
"""


# ───────────────────────── 元件 ─────────────────────────
def cand_link(c, root):
    if c.get("page"):
        return f'<a href="{root}candidates/{c["page"]}.html"><strong>{esc(c["name"])}</strong></a>'
    return esc(c["name"])


def candidates_table(city, ctx):
    rows = ""
    inc = city.get("incumbent") or {}
    for c in sorted(city.get("candidates", []), key=lambda x: x["ballot"]):
        mark = '<span class="tag">現任</span>' if inc and inc.get("name") == c["name"] else ""
        rows += (f'<tr><td class="num">{c["ballot"]}</td><td>{cand_link(c, ctx.root)} {mark}</td>'
                 f'<td>{party(c.get("party"))}</td><td>{esc(c.get("bio") or "—")}</td></tr>')
    return (f'<table class="cands"><thead><tr><th>號次</th><th>候選人</th><th>政黨</th><th>簡歷</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><p class="src">名單來源{ctx.cites(city.get("candidates_source"))}</p>')


def result_table(block, ctx, caption):
    if not block:
        return ""
    rows = ""
    for r in block.get("rows", []):
        win = '<span class="tag">當選</span>' if r.get("elected") else ""
        votes = f'{r["votes"]:,}' if r.get("votes") is not None else "—"
        pct = f'{r["pct"]:.2f}%' if r.get("pct") is not None else "—"
        rows += f'<tr><td>{esc(r["name"])} {win}</td><td>{party(r.get("party"))}</td><td class="num">{votes}</td><td class="num">{pct}</td></tr>'
    return (f'<table class="results"><caption>{esc(caption)}</caption><thead><tr><th>候選人</th><th>政黨</th>'
            f'<th>得票數</th><th>得票率</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="src">來源{ctx.cites(block.get("source"))}</p>')


def polls_hidden():
    return ARGS.no_polls or (BLACKOUT_START <= BUILD_NOW < BLACKOUT_END)


def blackout_notice():
    return ('<aside class="callout warning"><p class="callout-title">民調暫停顯示</p>'
            '<p>依公職人員選舉罷免法第 53 條，2026-11-18 00:00 起至 11-28 16:00 投票截止前，'
            '不得發布、報導、散布、評論或引述選舉民調。本站於此期間隱藏所有民調資料。</p></aside>')


def poll_table(city, pdata, ctx):
    if polls_hidden():
        return blackout_notice()
    if not pdata or not pdata.get("polls"):
        return '<p class="muted">本站尚未收錄此縣市的民調。</p>'
    order = [c["name"] for c in sorted(city["candidates"], key=lambda x: x["ballot"])]
    names = [n for n in order if any(n in (p.get("results") or {}) for p in pdata["polls"])]
    head = "".join(f"<th>{esc(n)}</th>" for n in names)
    rows = ""
    for p in pdata["polls"]:
        cells = ""
        for n in names:
            v = (p.get("results") or {}).get(n)
            if v is None:
                cells += '<td class="num muted">—</td>'
            else:
                cells += f'<td class="num"><span class="bar" style="--w:{min(float(v), 100)}%"></span>{v}</td>'
        und = p.get("undecided")
        n_ = f'{p["sample"]:,}' if p.get("sample") else "未載"
        moe = f'±{p["moe"]}' if p.get("moe") is not None else "未載"
        when = p.get("fieldwork") or f'{fmt_date(p.get("published"))} 公布'
        rows += (f'<tr><td>{esc(when)}</td>'
                 f'<td>{esc(p.get("pollster"))}<br><span class="muted">委託：{esc(p.get("sponsor"))}（{esc(p.get("sponsor_type"))}）</span></td>'
                 f'<td>{esc(p.get("method") or "未載")}</td><td class="num">{n_}<br><span class="muted">{moe}</span></td>'
                 f'{cells}<td class="num">{und if und is not None else "—"}</td>'
                 f'<td class="note">{esc(p.get("note") or "")}{ctx.cites(p.get("source"))}</td></tr>')
    return (f'<div class="scroll"><table class="polls"><thead><tr><th>調查期間</th><th>執行／委託</th><th>方法</th>'
            f'<th>樣本／誤差</th>{head}<th>未表態</th><th>備註</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="src">數字單位為百分比；欄位依號次排列。閱讀方式見<a href="{ctx.root}syntheses/how-to-read-polls.html">如何閱讀本站民調</a>。</p>')


def city_card(city, cands, root):
    names = " ／ ".join(
        (f'<a href="{root}candidates/{c["page"]}.html">{esc(c["name"])}</a>' if c.get("page") else esc(c["name"]))
        + f'<span class="muted">（{c["ballot"]}號）</span>'
        for c in sorted(city["candidates"], key=lambda x: x["ballot"]) if c.get("page"))
    return (f'<article class="card"><h3><a href="{root}cities/{city["id"]}.html">{esc(city["name"])}</a></h3>'
            f'<p>{names}</p><p class="muted">共 {len(city["candidates"])} 人參選</p></article>')


def all_cities_table(cities, root):
    rows = ""
    for cid in ORDER:
        c = cities[cid]
        res = c.get("result_2026")
        winners = {r["name"] for r in (res or {}).get("rows", []) if r.get("elected")}
        lst = "、".join(
            f'{x["ballot"]} ' + (f'<a href="{root}candidates/{x["page"]}.html"><strong>{esc(x["name"])}</strong></a>'
                                if x.get("page") else esc(x["name"]))
            + f'<span class="muted">（{esc(x["party"])}）</span>' + (' <span class="tag">當選</span>' if x["name"] in winners else "")
            for x in sorted(c["candidates"], key=lambda x: x["ballot"]))
        status = "完整" if c.get("status") == "full" else "簡版"
        rows += f'<tr><td><a href="{root}cities/{cid}.html">{esc(c["name"])}</a></td><td>{lst}</td><td>{status}</td></tr>'
    return f'<div class="scroll"><table class="overview"><thead><tr><th>縣市</th><th>候選人（號次）</th><th>本站</th></tr></thead><tbody>{rows}</tbody></table></div>'


# ───────────────────────── 頁面 ─────────────────────────
def build_city(city, cands, polls, sources):
    ctx = Ctx(sources, "../", f"cities/{city['id']}")
    parts = []
    if city.get("result_2026"):
        parts.append('<section class="result"><h2>2026 開票結果</h2>' +
                     result_table(city["result_2026"], ctx, "2026 首長選舉（中選會公告）") + "</section>")
    inc = city.get("incumbent")
    inc_txt = f'現任：{esc(inc["name"])}（{esc(inc["party"])}）{"，尋求連任" if inc.get("running") else "，本屆不參選"}' if inc else "現任：待補"
    badge = "完整版" if city.get("status") == "full" else "簡版"
    parts.append(f'<p class="meta"><span class="tag">{esc(city.get("tier"))}</span> <span class="tag">{badge}</span>　{inc_txt}</p>')
    parts.append("<h2>候選人</h2>" + candidates_table(city, ctx))
    body = md_to_html(city["_body"], ctx)
    body = body.replace("<p>{{polls}}</p>", poll_table(city, polls.get(city["id"]), ctx))
    parts.append(body)
    if city.get("history_2022"):
        parts.append("<h2>2022 年首長選舉</h2>" + result_table(city["history_2022"], ctx, "2022 首長選舉主要候選人"))
    return page_html(city["name"] + "長選舉", "\n".join(parts), ctx, city.get("updated"))


def build_candidate(c, cities, sources):
    ctx = Ctx(sources, "../", f"candidates/{c['id']}")
    city = cities[c["city"]]
    peers = [x for x in sorted(city["candidates"], key=lambda x: x["ballot"]) if x.get("page") and x["page"] != c["id"]]
    peer = "、".join(f'<a href="../candidates/{x["page"]}.html">{esc(x["name"])}</a>（{x["ballot"]}號）' for x in peers)
    head = (f'<div class="cand-head"><span class="ballot">{c["ballot"]}</span><div>'
            f'<p class="meta"><a href="../cities/{city["id"]}.html">{esc(city["name"])}長候選人</a>　{party(c["party"])}'
            f'{INC_TAG if c.get("incumbent") else ""}</p>'
            f'<p class="muted">{esc(c.get("current_role"))}</p></div></div>')
    body = md_to_html(c["_body"], ctx)
    foot = f'<p class="peers">同選區其他主要候選人：{peer or "—"}</p>'
    return page_html(c["name"], head + body + foot, ctx, c.get("updated"))


def build_generic(meta, sources, key, root, extra=None, active=None):
    ctx = Ctx(sources, root, key)
    body = md_to_html(meta["_body"], ctx)
    for k, v in (extra or {}).items():
        body = body.replace(f"<p>{{{{{k}}}}}</p>", v(ctx))
    return page_html(meta.get("title", key), body, ctx, meta.get("updated"), active)


def build_sources(sources, backlinks):
    ctx = Ctx(sources, "", "sources")
    rows = ""
    for sid, s in sources.items():
        used = "、".join(f'<a href="{href}">{esc(label)}</a>' for href, label in sorted(set(backlinks.get(sid, []))))
        rows += (f'<tr id="{sid}"><td class="num">{sid}</td><td>{esc(s["outlet"])}<br><span class="muted">{esc(s.get("kind"))}</span></td>'
                 f'<td><a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["title"])}</a>'
                 f'<br><span class="muted">{esc(s.get("summary"))}</span></td><td>{fmt_date(s.get("date"))}</td>'
                 f'<td class="note">{used or "—"}</td></tr>')
    body = ('<p>所有內容的原始出處。本站不轉載全文，摘要為自行改寫。日期為「—」者表示發布日未能確認。</p>'
            f'<div class="scroll"><table class="sources"><thead><tr><th>編號</th><th>媒體</th><th>標題與重點</th>'
            f'<th>日期</th><th>被引用於</th></tr></thead><tbody>{rows}</tbody></table></div>')
    return page_html("來源", body, ctx, None, "sources.html")


# ───────────────────────── Lint ─────────────────────────
def lint(sources, cities, cands, polls, synth, pages):
    for cid in ORDER:
        if cid not in cities:
            warn(f"缺少縣市頁 wiki/cities/{cid}.md")
    for cid, c in cities.items():
        for k in ["id", "name", "tier", "status", "updated", "candidates", "candidates_source"]:
            if k not in c:
                warn(f"cities/{cid}: 缺少欄位 {k}")
        balls = [x.get("ballot") for x in c.get("candidates", [])]
        if None in balls or len(set(balls)) != len(balls):
            warn(f"cities/{cid}: 號次缺漏或重複")
        mains = [x for x in c.get("candidates", []) if x.get("page")]
        for x in mains:
            if x["page"] not in cands:
                warn(f"cities/{cid}: page {x['page']} 不存在")
        counts = {}
        for x in mains:
            cp = cands.get(x["page"])
            if cp:
                sec = re.search(r"## 主要政見\n(.*?)(\n## |\Z)", cp["_body"], re.S)
                counts[x["name"]] = len(re.findall(r"^- ", sec.group(1), re.M)) if sec else 0
        if counts and max(counts.values()) - min(counts.values()) > 1:
            warn(f"cities/{cid}: 主要候選人政見條數不平衡 {counts}")
        if c.get("status") == "full" and "{{polls}}" not in c["_body"]:
            warn(f"cities/{cid}: 完整版缺少 {{{{polls}}}} 標記")
        pd = polls.get(cid)
        if pd:
            names = {x["name"] for x in c["candidates"]}
            for p in pd.get("polls", []):
                for n in (p.get("results") or {}):
                    if n not in names:
                        warn(f"polls/{cid}: 姓名 {n} 不在縣市候選人名單")
                for s in src_list(p.get("source")):
                    if s not in sources:
                        warn(f"polls/{cid}: 來源 {s} 不存在")
    for pid, c in cands.items():
        heads = re.findall(r"^## (.+)$", c["_body"], re.M)
        if heads != CANDIDATE_SECTIONS:
            warn(f"candidates/{pid}: 章節應為 {CANDIDATE_SECTIONS}，實際為 {heads}")
        if c.get("city") not in cities:
            warn(f"candidates/{pid}: city {c.get('city')} 不存在")
    # 內文不得出現民調數字
    for group, d in [("cities", cities), ("candidates", cands), ("syntheses", synth), ("", pages)]:
        for k, m in d.items():
            for line in m["_body"].splitlines():
                if "民調" in line and re.search(r"\d+(\.\d+)?\s*%", line):
                    warn(f"{group}/{k}: 內文疑似含民調數字（請移到 wiki/polls/）：{line.strip()[:40]}")
    # 引用檢查
    for group, d in [("cities", cities), ("candidates", cands), ("syntheses", synth), ("", pages)]:
        for k, m in d.items():
            for sid in re.findall(r"\[(S\d{3})\]", m["_body"]):
                if sid not in sources:
                    warn(f"{group}/{k}: 引用不存在的來源 {sid}")
            for link in re.findall(r"\]\(([^)#:]+\.md)", m["_body"]):
                target = (m["_path"].parent / link).resolve()
                if not target.exists():
                    warn(f"{group}/{k}: 連結 {link} 指向不存在的頁面")


# ───────────────────────── 主程式 ─────────────────────────
def main():
    sources, cities, cands, polls, synth, pages = load_all()
    lint(sources, cities, cands, polls, synth, pages)
    if ARGS.lint:
        report()
        return
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "cities").mkdir(parents=True)
    (OUT / "candidates").mkdir()
    (OUT / "syntheses").mkdir()
    (OUT / "assets").mkdir()
    shutil.copy(ASSETS / "style.css", OUT / "assets" / "style.css")
    (OUT / ".nojekyll").write_text("")

    backlinks = {}

    def track(html_text, href, label):
        for sid in set(re.findall(r'sources\.html#(S\d{3})"', html_text)):
            backlinks.setdefault(sid, []).append((href, label))
        return html_text

    for cid, c in cities.items():
        h = build_city(c, cands, polls, sources)
        (OUT / "cities" / f"{cid}.html").write_text(track(h, f"cities/{cid}.html", c["name"]), encoding="utf-8")
    for pid, c in cands.items():
        h = build_candidate(c, cities, sources)
        (OUT / "candidates" / f"{pid}.html").write_text(track(h, f"candidates/{pid}.html", c["name"]), encoding="utf-8")
    for sid, m in synth.items():
        h = build_generic(m, sources, f"syntheses/{sid}", "../", active="syntheses.html")
        (OUT / "syntheses" / f"{sid}.html").write_text(track(h, f"syntheses/{sid}.html", m["title"]), encoding="utf-8")

    six_cards = lambda ctx: '<section class="cards">' + "".join(city_card(cities[c], cands, ctx.root) for c in SIX) + "</section>"
    extras = {"six_cities": six_cards, "all_cities": lambda ctx: all_cities_table(cities, ctx.root)}
    for key, m in pages.items():
        if key == "log":
            m["title"] = "更新日誌"
        active = {"index": "index.html", "overview": "overview.html", "about": "about.html"}.get(key)
        h = build_generic(m, sources, key, "", extras, active)
        (OUT / f"{key}.html").write_text(track(h, f"{key}.html", m.get("title", key)), encoding="utf-8")

    # 六都頁
    ctx = Ctx(sources, "", "six")
    body = '<p>六個直轄市為本站完整版範圍，候選人依號次排列。</p>' + six_cards(ctx)
    (OUT / "six.html").write_text(page_html("六都", body, ctx, None, "six.html"), encoding="utf-8")

    # 民調總表
    ctx = Ctx(sources, "", "polls")
    if polls_hidden():
        body = blackout_notice()
    else:
        body = ('<p>六都市長選舉民調彙整，依縣市排列。收錄與排除標準見'
                '<a href="syntheses/how-to-read-polls.html">如何閱讀本站民調</a>。</p>')
        for cid in SIX:
            body += f'<h2><a href="cities/{cid}.html">{esc(cities[cid]["name"])}</a></h2>' + poll_table(cities[cid], polls.get(cid), ctx)
    (OUT / "polls.html").write_text(track(page_html("民調", body, ctx, None, "polls.html"), "polls.html", "民調"), encoding="utf-8")

    # 議題比較索引
    ctx = Ctx(sources, "", "syntheses")
    items = "".join(f'<li><a href="syntheses/{k}.html">{esc(m["title"])}</a>　<span class="muted">更新 {fmt_date(m.get("updated"))}</span></li>'
                    for k, m in sorted(synth.items()))
    (OUT / "syntheses.html").write_text(page_html("議題比較", f'<ul class="list">{items}</ul>', ctx, None, "syntheses.html"), encoding="utf-8")

    (OUT / "sources.html").write_text(build_sources(sources, backlinks), encoding="utf-8")
    report()
    print(f"已輸出 {sum(1 for _ in OUT.rglob('*.html'))} 個頁面到 docs/；民調{'已隱藏' if polls_hidden() else '顯示中'}。")


def report():
    if WARNINGS:
        print(f"Lint 警告 {len(WARNINGS)} 則：")
        for w in WARNINGS:
            print("  -", w)
    else:
        print("Lint：沒有問題。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--no-polls", action="store_true")
    ap.add_argument("--date", help="以指定日期（YYYY-MM-DD）建置")
    ARGS = ap.parse_args()
    BUILD_NOW = (datetime.fromisoformat(ARGS.date).replace(hour=12, tzinfo=TW) if ARGS.date else datetime.now(TW))
    main()
    sys.exit(0)
