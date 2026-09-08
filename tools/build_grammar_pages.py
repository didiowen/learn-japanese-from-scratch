#!/usr/bin/env python3
"""文法章節頁產生器。

grammar.md 是唯一正本；本工具把 grammar/chapters.json 登錄的每一章渲染成
grammar/NN.html，並產生 grammar/index.html 章節總覽。✅ 狀態與完成日期一律
從 grammar-daily-progress.md 推導，不重複儲存。

只支援 grammar.md 實際使用的 markdown 子集：
  ###／#### 小標（降一級成 h2/h3，章 ## 變頁 h1）、段落、行尾兩空格換行、
  **粗體**、`行內程式碼`、GFM 表格、> 引言、``` 圍欄、單層 - / 1. 清單、---。
認不得的行直接 BuildError 帶行號——寧可建置失敗告警，不可默默出半頁。

用法：
    python3 tools/build_grammar_pages.py            # 寫出所有頁面
    python3 tools/build_grammar_pages.py --check    # 只比對，過期/缺頁 exit 1

validate_quiz_data.py 會 import 本模組呼叫 build(check_only=True)，
讓 precommit hook 免費強制「章節頁不過期」。
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_MD = ROOT / 'grammar.md'
PROGRESS_MD = ROOT / 'grammar-daily-progress.md'
CHAPTERS_JSON = ROOT / 'grammar' / 'chapters.json'
OUT_DIR = ROOT / 'grammar'
# 一課＝一個文法項＋配對的單字批次；配對表在 pairings.json（文法項編號 → 單字批次編號）
PAIRINGS_JSON = ROOT / 'grammar' / 'pairings.json'
VOCAB_LESSONS_MD = ROOT / 'vocab-lessons.md'
VOCAB_BATCHES_JSON = ROOT / 'vocab' / 'batches.json'

SITE = 'https://didiowen.github.io/nihongo'

ALLOWED_SUBSET = ('允許的 markdown：###/#### 小標、段落、行尾兩空格換行、**粗體**、'
                  '`行內程式碼`、GFM 表格、> 引言、``` 圍欄、單層 - 或 1. 清單、---')


class BuildError(SystemExit):
    def __init__(self, msg):
        super().__init__(f'build_grammar_pages: {msg}\n（{ALLOWED_SUBSET}）')


# ── 進度表 ──────────────────────────────────────────────

def parse_progress(path=None):
    """回傳 {項目編號: {'done': bool, 'date': str, 'title': str}} 與 ⬜ 數。

    path 預設 grammar 的進度表；build_vocab_pages.py 傳入單字進度表重用
    （兩張表的欄位順序相同：# ｜ 名稱 ｜ 來源/字數 ｜ 狀態 ｜ 完成日期 ｜ 備註）。
    """
    path = path or PROGRESS_MD
    rows, pending = {}, 0
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'\|\s*(\d+)\s*\|([^|]+)\|[^|]*\|\s*([✅⬜🟡])\s*\|([^|]*)\|', line)
        if not m:
            continue
        n = int(m.group(1))
        done = m.group(3) == '✅'
        rows[n] = {'done': done, 'date': m.group(4).strip(),
                   'title': m.group(2).strip()}
        if not done:
            pending += 1
    if not rows:
        raise BuildError(f'{path.name} 裡找不到任何進度列')
    return rows, pending


# ── grammar.md 分節 ──────────────────────────────────────

def split_sections(path=None):
    """回傳 {## 標題: (起始行號, [body 行])}。path 預設 grammar.md。"""
    path = path or GRAMMAR_MD
    lines = path.read_text(encoding='utf-8').split('\n')
    sections, cur, buf, start = {}, None, [], 0
    for i, line in enumerate(lines, 1):
        if line.startswith('## '):
            if cur is not None:
                if cur in sections:
                    raise BuildError(f'{path.name} 有兩個「## {cur}」（第 {sections[cur][0]} 與 {start} 行）')
                sections[cur] = (start, buf)
            cur, buf, start = line[3:].strip(), [], i
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        if cur in sections:
            raise BuildError(f'{path.name} 有兩個「## {cur}」')
        sections[cur] = (start, buf)
    return sections


# ── 受限 markdown → HTML ────────────────────────────────

_CODE_SPAN = re.compile(r'`([^`]+)`')
_BOLD = re.compile(r'\*\*([^*]+)\*\*')


def render_inline(text):
    """escape → `code`（內容保護不再處理）→ **bold**。"""
    parts = []
    last = 0
    for m in _CODE_SPAN.finditer(text):
        parts.append(('t', text[last:m.start()]))
        parts.append(('c', m.group(1)))
        last = m.end()
    parts.append(('t', text[last:]))
    out = []
    for kind, seg in parts:
        if kind == 't':
            for bad, why in (('~~', '刪除線'), ('](', '連結'), ('__', '底線強調'), ('[[', 'wikilink')):
                if bad in seg:
                    raise BuildError(f'不支援的語法（{why}）：「{seg.strip()[:40]}」')
        seg = html.escape(seg, quote=False)
        if kind == 'c':
            out.append(f'<code>{seg}</code>')
        else:
            out.append(_BOLD.sub(r'<strong>\1</strong>', seg))
    return ''.join(out)


def render_para_text(text):
    if '*' in text.replace('**', ''):
        # 單顆 * 不在子集內（避免斜體被默默吃掉）
        raise BuildError(f'段落含單顆 *（不支援斜體）：「{text[:40]}」')
    return render_inline(text)


TABLE_SEP = re.compile(r'^\|[\s:|-]+\|$')
LIST_UL = re.compile(r'^- (.*)$')
LIST_OL = re.compile(r'^\d+\. (.*)$')


def render_section(body_lines, base_lineno, demote=0, srcname='grammar.md'):
    """把一章的 body 轉成 HTML 片段。

    demote：標題再降幾級。嵌進文法頁的單字批次用 demote=1，讓它的 ### 條目
    落在注入的「這一課的單字」h2 底下，而不是與它平起平坐。
    srcname：錯誤訊息裡的來源檔名（單字正本傳 vocab-lessons.md）。
    """
    out = []
    i = 0
    n = len(body_lines)
    h_major, h_minor = 2 + demote, 3 + demote

    def err(msg, off):
        raise BuildError(f'{srcname} 第 {base_lineno + off + 1} 行：{msg}')

    while i < n:
        line = body_lines[i]
        stripped = line.strip()

        if stripped == '':
            i += 1
            continue
        if stripped == '---':
            i += 1
            continue
        # 圍欄
        if stripped.startswith('```'):
            j = i + 1
            block = []
            while j < n and not body_lines[j].strip().startswith('```'):
                block.append(body_lines[j])
                j += 1
            if j >= n:
                err('``` 圍欄沒有關閉', i)
            out.append('<pre><code>' + html.escape('\n'.join(block), quote=False)
                       + '</code></pre>')
            i = j + 1
            continue
        # 小標
        if stripped.startswith('#### '):
            out.append(f'<h{h_minor}>{render_inline(stripped[5:])}</h{h_minor}>')
            i += 1
            continue
        if stripped.startswith('### '):
            out.append(f'<h{h_major}>{render_inline(stripped[4:])}</h{h_major}>')
            i += 1
            continue
        if stripped.startswith('#'):
            err(f'不支援的標題層級「{stripped[:20]}」', i)
        # 表格
        if stripped.startswith('|'):
            if i + 1 >= n or not TABLE_SEP.match(body_lines[i + 1].strip()):
                err('表格第一列後面必須接 |---| 分隔列', i)
            header = [c.strip() for c in stripped.strip('|').split('|')]
            rows = []
            j = i + 2
            while j < n and body_lines[j].strip().startswith('|'):
                rows.append([c.strip() for c in body_lines[j].strip().strip('|').split('|')])
                j += 1
            thead = ''.join(f'<th>{render_inline(c)}</th>' for c in header)
            tbody = []
            for r in rows:
                if len(r) != len(header):
                    # 允許尾欄留空造成的欄數差
                    r = (r + [''] * len(header))[:len(header)]
                tbody.append('<tr>' + ''.join(f'<td>{render_inline(c)}</td>' for c in r) + '</tr>')
            out.append('<div class="table-wrap"><table><thead><tr>' + thead
                       + '</tr></thead><tbody>' + ''.join(tbody) + '</tbody></table></div>')
            i = j
            continue
        # 引言
        if stripped.startswith('>'):
            quote_lines = []
            j = i
            while j < n and body_lines[j].strip().startswith('>'):
                quote_lines.append(body_lines[j].strip()[1:].lstrip())
                j += 1
            paras, cur = [], []
            for q in quote_lines:
                if q == '':
                    if cur:
                        paras.append(cur)
                        cur = []
                else:
                    cur.append(q)
            if cur:
                paras.append(cur)
            inner = ''.join(
                '<p>' + '<br>'.join(render_para_text(x.rstrip()) for x in p) + '</p>'
                for p in paras)
            out.append(f'<blockquote>{inner}</blockquote>')
            i = j
            continue
        # 清單
        if LIST_UL.match(stripped) or LIST_OL.match(stripped):
            ordered = bool(LIST_OL.match(stripped))
            pat = LIST_OL if ordered else LIST_UL
            items = []
            j = i
            while j < n:
                m = pat.match(body_lines[j].strip())
                if not m:
                    break
                items.append(f'<li>{render_para_text(m.group(1))}</li>')
                j += 1
            tag = 'ol' if ordered else 'ul'
            out.append(f'<{tag}>{"".join(items)}</{tag}>')
            i = j
            continue
        # 段落（累積到空行或下一個 block 開頭）
        para = []
        j = i
        while j < n:
            s = body_lines[j].strip()
            if (s == '' or s == '---' or s.startswith('#') or s.startswith('|')
                    or s.startswith('>') or s.startswith('```')
                    or LIST_UL.match(s) or LIST_OL.match(s)):
                break
            seg = render_para_text(s)
            if body_lines[j].endswith('  '):
                seg += '<br>'
            para.append(seg)
            j += 1
        out.append('<p>' + '\n'.join(para) + '</p>')
        i = j

    return '\n'.join(out)


_TAG = re.compile(r'<[^>]+>')
_MARKUP = re.compile(r'[*`|>#\s\-—:：]|^\d+\.')


def assert_content_preserved(body_lines, rendered):
    """每行去 markup 的殘文必須出現在渲染結果的純文字裡，掉字即報錯。"""
    plain = html.unescape(_TAG.sub('', rendered))
    plain = re.sub(r'\s', '', plain)
    for idx, line in enumerate(body_lines):
        s = line.strip()
        # 圍欄標記、表格分隔列、--- 分隔線都是「渲染時會被吃掉」的純標記行
        if s.startswith('```') or TABLE_SEP.match(s) or s == '---':
            continue
        # 行首標記（#、>、-、1.）可能疊加，如 "> - item"；逐層剝掉。
        # **只在行首剝** —— 早期版本把 `-` 從整行剝掉，句中的連字號（台語羅馬字
        # 的 h-／k-）就會讓殘文與輸出對不上而誤報掉字（2026-09-05 單字課程實踩）。
        while True:
            m = re.match(r'^(#{1,6}\s*|>\s*|-\s+|\d+\.\s+)', s)
            if not m:
                break
            s = s[m.end():]
        residue = s
        for ch in '*`|':            # 行內標記：粗體、行內碼、表格分隔
            residue = residue.replace(ch, '')
        residue = re.sub(r'\s', '', residue)
        if residue and residue not in plain:
            raise BuildError(f'內容保全檢查失敗（第 {idx + 1} 行 of section）：「{s[:40]}」沒有完整出現在輸出裡')


# ── 頁面模板 ────────────────────────────────────────────

FONTS = ('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600'
         '&family=Noto+Sans+TC:wght@400;500&display=swap')

SPEAK_JS = """\
// 表格「日文／例句」欄自動附朗讀鍵（speakJa 與 quiz-common.js 同款、本地精簡版）
let _gen = 0;
function speakJa(text) {
  try {
    const t = text.replace(/[（(].*?[）)]/g, '').trim();
    if (!t) return;
    _gen += 1;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t);
    u.lang = 'ja-JP'; u.rate = 0.85;
    const v = speechSynthesis.getVoices().filter(v => v.lang.startsWith('ja'))[0];
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  } catch (e) { /* 無語音支援就靜默 */ }
}
document.addEventListener('DOMContentLoaded', () => {
  const SPEAK_COLS = ['日文', '例句', '例', '句型', '假名', '原形', '禮貌體'];
  document.querySelectorAll('.chapter-body table').forEach(tbl => {
    const ths = [...tbl.querySelectorAll('thead th')].map(th => th.textContent.trim());
    ths.forEach((h, col) => {
      if (!SPEAK_COLS.includes(h)) return;
      tbl.querySelectorAll('tbody tr').forEach(tr => {
        const td = tr.children[col];
        if (!td) return;
        const raw = td.textContent.trim();
        if (!raw || raw === '—' || /^[A-Za-z0-9\\s.…]+$/.test(raw)) return;
        const btn = document.createElement('button');
        btn.className = 'speak-btn'; btn.type = 'button';
        btn.title = '朗讀'; btn.textContent = '🔊';
        btn.addEventListener('click', () => speakJa(raw));
        td.appendChild(btn);
      });
    });
  });
});"""


def load_pairings():
    """回傳 {文法項編號: 單字批次編號}。檔案不存在＝還沒配對，回空 dict。"""
    if not PAIRINGS_JSON.exists():
        return {}
    return {int(k): int(v) for k, v in
            json.loads(PAIRINGS_JSON.read_text(encoding='utf-8')).items()}


def vocab_section_html(batch_n):
    """把配對的單字批次渲染成「這一課的單字」一節。

    該批還沒上架（batches.json 沒登錄）就回 None——當天先出純文法頁，
    等單字軌寫完正本、重跑產生器時才補上。這是刻意的：兩軌同一天執行，
    文法先跑，那時單字正本還沒有這一節。
    """
    if not VOCAB_BATCHES_JSON.exists():
        return None
    registry = {int(k): v for k, v in
                json.loads(VOCAB_BATCHES_JSON.read_text(encoding='utf-8')).items()}
    heading = registry.get(batch_n)
    if heading is None:
        return None
    sections = split_sections(VOCAB_LESSONS_MD)
    if heading not in sections:
        raise BuildError(f'配對的單字批次「{heading}」在 vocab-lessons.md 找不到'
                         f'（batches.json 與正本標題必須一字不差）')
    start, body = sections[heading]
    inner = render_section(body, start, demote=1, srcname='vocab-lessons.md')
    assert_content_preserved(body, inner)
    topic = heading.split('：', 1)[1] if '：' in heading else heading
    return ('<section class="lesson-vocab">\n'
            f'<h2>這一課的單字：{html.escape(topic, quote=False)}</h2>\n'
            f'{inner}\n</section>')


def chapter_page(n, title, date, body_html, prev_item, next_item, vocab_batch=None):
    nn = f'{n:02d}'
    eyebrow = f'第 {nn} 章' + (f' · {date} 學過' if date else '')
    prev_a = (f'<a class="prev" href="{prev_item[0]:02d}.html">← {html.escape(prev_item[1], quote=False)}</a>'
              if prev_item else '<span></span>')
    next_a = (f'<a class="next" href="{next_item[0]:02d}.html">{html.escape(next_item[1], quote=False)} →</a>'
              if next_item else '')
    t = html.escape(title, quote=False)
    vocab_cta = (f'<a href="../vocab-quiz.html?batch={vocab_batch}">練這一課的單字 →</a>'
                 if vocab_batch else '')
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{t} — 日文文法</title>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="chapter.css">
</head>
<body>
<nav class="crumb"><a href="../index.html">← 首頁</a><a href="index.html">文法章節</a><a href="../grammar-quiz.html">文法測驗</a></nav>
<article class="chapter">
  <header class="chapter-head">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{t}</h1>
  </header>
  <div class="chapter-body">
{body_html}
  </div>
</article>
<p class="chapter-cta"><a href="../grammar-quiz.html?ch={n}">練這一章的題目 →</a>{vocab_cta}</p>
<nav class="chapter-nav">{prev_a}{next_a}</nav>
<footer class="chapter-foot"><a href="index.html">全部章節</a> · <a href="../notes/#/grammar.md">完整文法筆記</a> · <a href="https://ko-fi.com/ines8964">☕ Ko-fi</a></footer>
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
    pending_p = (f'\n    <p class="pending">還有 {pending} 章依每日進度陸續開放。</p>'
                 if pending else '')
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>N5 文法章節 — 日文學習</title>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="chapter.css">
</head>
<body>
<nav class="crumb"><a href="../index.html">← 首頁</a><a href="../grammar-quiz.html">文法測驗</a></nav>
<main class="grammar-index">
  <header class="chapter-head">
    <p class="eyebrow">N5 文法</p>
    <h1>一天一章，讀完就練。</h1>
    <p class="lead">每天 17:30 開放一章。讀完按下面的測驗連結，題目會照間隔記憶排程自動安排複習。</p>
  </header>
  <ul class="entries">
{chr(10).join(lis)}
  </ul>{pending_p}
  <p class="chapter-cta"><a href="../grammar-quiz.html">開始文法測驗 →</a></p>
</main>
</body>
</html>
'''


# ── 主流程 ──────────────────────────────────────────────

def build(check_only=False):
    """渲染全部頁面。check_only=True 時不寫檔，回傳過期/缺少檔案清單。"""
    registry = json.loads(CHAPTERS_JSON.read_text(encoding='utf-8'))
    registry = {int(k): v for k, v in registry.items()}
    progress, pending = parse_progress()
    sections = split_sections()
    pairings = load_pairings()

    # 交叉檢查：✅ ↔ registry 一一對應
    done_nums = {n for n, r in progress.items() if r['done']}
    missing = sorted(done_nums - set(registry))
    extra = sorted(set(registry) - done_nums)
    if missing:
        raise BuildError(f'進度表已 ✅ 但 chapters.json 沒登錄：{missing}')
    if extra:
        raise BuildError(f'chapters.json 有登錄但進度表不是 ✅：{extra}')

    ordered = sorted(registry)
    pages = {}
    entries = []
    for idx, n in enumerate(ordered):
        heading = registry[n]
        if heading not in sections:
            raise BuildError(f'chapters.json 第 {n} 項的標題「{heading}」在 grammar.md 找不到'
                             f'（必須與 ## 後的文字一字不差）')
        start, body = sections[heading]
        body_html = render_section(body, start)
        assert_content_preserved(body, body_html)
        vocab_batch = pairings.get(n)
        if vocab_batch is not None:
            vs = vocab_section_html(vocab_batch)
            if vs is None:
                vocab_batch = None      # 該批還沒上架，CTA 也先不要出現
            else:
                body_html += '\n' + vs
        date = progress[n]['date']
        prev_item = (ordered[idx - 1], registry[ordered[idx - 1]]) if idx > 0 else None
        next_item = (ordered[idx + 1], registry[ordered[idx + 1]]) if idx + 1 < len(ordered) else None
        pages[f'{n:02d}.html'] = chapter_page(n, heading, date, body_html, prev_item,
                                              next_item, vocab_batch)
        entries.append((n, heading, date))

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


def main():
    check = '--check' in sys.argv[1:]
    result = build(check_only=check)
    if check:
        if result:
            print('章節頁與來源不同步（跑 python3 tools/build_grammar_pages.py 重建）：')
            for r in result:
                print('  ' + r)
            sys.exit(1)
        print('章節頁全部同步 ✓')
    else:
        for name in result:
            print(f'寫出 grammar/{name}')


if __name__ == '__main__':
    main()
