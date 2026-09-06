#!/usr/bin/env python3
"""單字課程頁產生器。

與 build_grammar_pages.py 同一套機制，第二個消費者：vocab-lessons.md 是每日
單字教學的唯一正本，本工具把 vocab/batches.json 登錄的每一批渲染成
vocab/NN.html，並產生 vocab/index.html 總覽。✅ 狀態與完成日期從
vocab-daily-progress.md 推導，不重複儲存。

**渲染器、進度解析、朗讀鍵全部 import build_grammar_pages**——同一份實作，
不 fork；改版型或修 markdown 子集只要改那一支，兩邊同時生效。

vocabulary.md 不受影響：它是依主題分類的總表（docsify 筆記檢視），這裡是
「每日課程」檢視，兩者刻意並存，與 grammar.md／grammar/ 的關係相同。

用法：
    python3 tools/build_vocab_pages.py            # 寫出所有頁面
    python3 tools/build_vocab_pages.py --check    # 只比對，過期/缺頁 exit 1
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_grammar_pages import (  # noqa: E402  共用實作，勿另寫一份
    FONTS, SPEAK_JS, BuildError, assert_content_preserved, parse_progress,
    render_section, split_sections,
)

ROOT = Path(__file__).resolve().parent.parent
LESSONS_MD = ROOT / 'vocab-lessons.md'
PROGRESS_MD = ROOT / 'vocab-daily-progress.md'
BATCHES_JSON = ROOT / 'vocab' / 'batches.json'
OUT_DIR = ROOT / 'vocab'

# 樣式與文法章節頁共用（同一套設計，不另外維護一份）
CSS_HREF = '../grammar/chapter.css'


def batch_page(n, title, date, body_html, prev_item, next_item):
    nn = f'{n:02d}'
    eyebrow = f'第 {nn} 批' + (f' · {date} 學過' if date else '')
    prev_a = (f'<a class="prev" href="{prev_item[0]:02d}.html">← 批次{prev_item[0]}：{html.escape(prev_item[1], quote=False)}</a>'
              if prev_item else '<span></span>')
    next_a = (f'<a class="next" href="{next_item[0]:02d}.html">批次{next_item[0]}：{html.escape(next_item[1], quote=False)} →</a>'
              if next_item else '')
    t = html.escape(title, quote=False)
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>批次{n}：{t} — 日文單字</title>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{CSS_HREF}">
</head>
<body>
<nav class="crumb"><a href="../index.html">← 首頁</a><a href="index.html">單字課程</a><a href="../vocab-quiz.html?batch={n}">課程測驗</a></nav>
<article class="chapter">
  <header class="chapter-head">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{t}</h1>
  </header>
  <div class="chapter-body">
{body_html}
  </div>
</article>
<p class="chapter-cta"><a href="../vocab-quiz.html?batch={n}">到課程測驗練這批字 →</a></p>
<nav class="chapter-nav">{prev_a}{next_a}</nav>
<footer class="chapter-foot"><a href="index.html">全部批次</a> · <a href="../notes/#/vocabulary.md">完整單字表</a> · <a href="https://ko-fi.com/ines8964">☕ Ko-fi</a></footer>
<script>
{SPEAK_JS}
</script>
</body>
</html>
'''


def index_page(entries, pending):
    lis = []
    for n, title, date in entries:
        desc = f'{date} 學過' if date else '已上架'
        lis.append(f'''      <li class="entry"><a href="{n:02d}.html">
        <span class="num">{n:02d}</span>
        <span class="meta"><span class="label">{html.escape(title, quote=False)}</span>
        <span class="desc">{desc}</span></span></a></li>''')
    pending_p = (f'\n    <p class="pending">還有 {pending} 批依每日進度陸續開放。</p>'
                 if pending else '')
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>N5 單字課程 — 日文學習</title>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{CSS_HREF}">
</head>
<body>
<nav class="crumb"><a href="../index.html">← 首頁</a><a href="../vocab-quiz.html">課程測驗</a></nav>
<main class="grammar-index">
  <header class="chapter-head">
    <p class="eyebrow">N5 單字</p>
    <h1>一天一批，記憶鉤都在。</h1>
    <p class="lead">每天 17:30 開放一批。漢字來源、台語連結、音訓分流都留在頁面上，忘了隨時翻回來；練習照舊在單字測驗頁，走間隔記憶排程。</p>
  </header>
  <ul class="entries">
{chr(10).join(lis)}
  </ul>{pending_p}
  <p class="chapter-cta"><a href="../vocab-quiz.html">開始課程測驗 →</a></p>
</main>
</body>
</html>
'''


def build(check_only=False):
    """渲染全部頁面。check_only=True 時不寫檔，回傳過期/缺少檔案清單。"""
    registry = {int(k): v for k, v in
                json.loads(BATCHES_JSON.read_text(encoding='utf-8')).items()}
    progress, pending = parse_progress(PROGRESS_MD)
    sections = split_sections(LESSONS_MD)

    done_nums = {n for n, r in progress.items() if r['done']}
    missing = sorted(done_nums - set(registry))
    extra = sorted(set(registry) - done_nums)
    if missing:
        raise BuildError(f'進度表已 ✅ 但 batches.json 沒登錄：{missing}')
    if extra:
        raise BuildError(f'batches.json 有登錄但進度表不是 ✅：{extra}')

    ordered = sorted(registry)
    pages, entries = {}, []
    for idx, n in enumerate(ordered):
        heading = registry[n]
        if heading not in sections:
            raise BuildError(f'batches.json 第 {n} 批的標題「{heading}」在 vocab-lessons.md 找不到'
                             f'（必須與 ## 後的文字一字不差）')
        start, body = sections[heading]
        body_html = render_section(body, start)
        assert_content_preserved(body, body_html)
        # registry 的標題是「批次N：主題」，頁面標題只要主題那半
        display = _display(heading)
        date = progress[n]['date']
        prev_item = ((ordered[idx - 1], _display(registry[ordered[idx - 1]]))
                     if idx > 0 else None)
        next_item = ((ordered[idx + 1], _display(registry[ordered[idx + 1]]))
                     if idx + 1 < len(ordered) else None)
        pages[f'{n:02d}.html'] = batch_page(n, display, date, body_html, prev_item, next_item)
        entries.append((n, display, date))

    pages['index.html'] = index_page(entries, pending)

    stale = []
    for name, content in sorted(pages.items()):
        path = OUT_DIR / name
        if check_only:
            if not path.exists():
                stale.append(f'{name}（缺少）')
            elif path.read_text(encoding='utf-8') != content:
                stale.append(f'{name}（過期）')
        else:
            path.write_text(content, encoding='utf-8')
    return stale if check_only else sorted(pages)


def _display(heading):
    return heading.split('：', 1)[1] if '：' in heading else heading


def main():
    check = '--check' in sys.argv[1:]
    result = build(check_only=check)
    if check:
        if result:
            print('單字課程頁與來源不同步（跑 python3 tools/build_vocab_pages.py 重建）：')
            for r in result:
                print('  ' + r)
            sys.exit(1)
        print('單字課程頁全部同步 ✓')
    else:
        for name in result:
            print(f'寫出 vocab/{name}')


if __name__ == '__main__':
    main()
