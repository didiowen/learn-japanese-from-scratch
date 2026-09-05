#!/usr/bin/env python3
"""測驗資料一致性檢查。

檢查項目：
1. vocabCards 每個單字的 round 是否等於 max(所有字符輪次)
   （字符輪次以 HTML 內 cards / katakanaCards 為準；小假名 ゃゅょ/ャュョ→R3、
   っ/ッ→R5、小母音→R1、長音 ー 不計）
2. vocabCards 是否有重複條目（同 display/word 且同 kanji）
3. recentBatch 的 key 是否都存在於 vocabCards
4. alreadyKnown 與 recentBatch 是否有同一個字（優先度互相矛盾）
5. already-known.md 中存在於 vocabCards 的字，是否都進了 alreadyKnown Set
6. grammar-quiz.html 題庫完整性（id 格式/唯一、ch 對應 chapters.json、
   mc 的 answer∈choices、cloze 含 ___ 且 answer∈accepted、每章 ≥3 題、
   頁內 chapters 陣列與 grammar/chapters.json 一致）
7. grammar/ 章節頁是否與 grammar.md 同步（import build_grammar_pages 跑 --check）

用法：python3 tools/validate_quiz_data.py
發現問題時輸出清單並以非零狀態碼結束。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SMALL_KANA = {
    'ゃ': 3, 'ゅ': 3, 'ょ': 3, 'っ': 5,
    'ャ': 3, 'ュ': 3, 'ョ': 3, 'ッ': 5,
    'ぁ': 1, 'ぃ': 1, 'ぅ': 1, 'ぇ': 1, 'ぉ': 1,
    'ァ': 1, 'ィ': 1, 'ゥ': 1, 'ェ': 1, 'ォ': 1,
}
IGNORED = set('ー・ 　/／')


def extract_array(src, name):
    m = re.search(rf'const {name} = \[(.*?)\n\];', src, re.S)
    if not m:
        sys.exit(f'找不到 {name} 陣列')
    return m.group(1)


def parse_kana_rounds(src, array_name):
    body = extract_array(src, array_name)
    rounds = {}
    for m in re.finditer(r"char:\s*'([^']+)',\s*round:\s*(\d+)", body):
        rounds[m.group(1)] = int(m.group(2))
    # 多行格式（char 與 round 分行）
    for m in re.finditer(r"char:\s*'([^']+)',\n\s*round:\s*(\d+)", body):
        rounds[m.group(1)] = int(m.group(2))
    return rounds


def parse_vocab(src, key):
    body = extract_array(src, 'vocabCards')
    entries = []
    for lineno_offset, line in enumerate(body.split('\n')):
        m = re.search(rf"{key}:\s*'([^']+)'", line)
        r = re.search(r"round:\s*(\d)", line)
        k = re.search(r"kanji:\s*'([^']+)'", line)
        if m and r:
            entries.append({
                'word': m.group(1), 'round': int(r.group(1)),
                'kanji': k.group(1) if k else None, 'line': line.strip(),
            })
    return entries


def parse_set(src, name):
    m = re.search(rf'const {name} = new Set\(\[(.*?)\]\);', src, re.S)
    if not m:
        return set()
    return set(re.findall(r"'([^']+)'", m.group(1)))


def parse_batch(src):
    m = re.search(r'const recentBatch = \{(.*?)\n\};', src, re.S)
    if not m:
        return {}
    return {w: int(n) for w, n in re.findall(r"'([^']+)':\s*(\d+)", m.group(1))}


def word_round(word, kana_rounds):
    """word_round = max(所有字符輪次)；查不到的字符回報 None。"""
    rounds, unknown = [], []
    for ch in word:
        if ch in IGNORED:
            continue
        if ch in SMALL_KANA:
            rounds.append(SMALL_KANA[ch])
        elif ch in kana_rounds:
            rounds.append(kana_rounds[ch])
        else:
            unknown.append(ch)
    return (max(rounds) if rounds else None), unknown


def parse_known_md():
    words = set()
    for line in (ROOT / 'already-known.md').read_text().split('\n'):
        cols = [c.strip() for c in line.split('|')]
        if len(cols) >= 3 and cols[2] and not set(cols[2]) <= set('- ─'):
            for w in re.split('[／/]', cols[2]):
                w = w.strip()
                if w and re.fullmatch(r'[ぁ-ゖァ-ヺー]+', w):
                    words.add(w)
    return words


def check_file(path, kana_array, vocab_key, known_md=None):
    src = path.read_text()
    kana_rounds = parse_kana_rounds(src, kana_array)
    vocab = parse_vocab(src, vocab_key)
    known_set = parse_set(src, 'alreadyKnown')
    batch = parse_batch(src)
    issues = []

    # 1. round 檢查
    for v in vocab:
        expect, unknown = word_round(v['word'], kana_rounds)
        if unknown:
            issues.append(f"[round] {v['word']}：字符 {unknown} 不在字表")
        elif expect is not None and expect != v['round']:
            issues.append(f"[round] {v['word']}：round {v['round']} → 應為 {expect}")

    # 2. 重複條目（同字同漢字才算；さけ 酒/鮭 這類同形異義不算）
    seen = {}
    for v in vocab:
        key = (v['word'], v['kanji'])
        if key in seen:
            issues.append(f"[重複] {v['word']}（kanji={v['kanji']}）出現兩次")
        seen[key] = v

    words = {v['word'] for v in vocab}

    # 3. recentBatch key 必須存在
    for w in batch:
        if w not in words:
            issues.append(f"[batch] recentBatch 有「{w}」但 vocabCards 沒有")

    # 4. alreadyKnown 與 recentBatch 矛盾
    for w in sorted(known_set & set(batch)):
        issues.append(f"[矛盾] 「{w}」同時在 alreadyKnown 與 recentBatch")

    # 5. already-known.md 同步（僅平假名測驗）
    if known_md is not None:
        missing = sorted((known_md & words) - known_set)
        if missing:
            issues.append(f"[known] already-known.md 有但 alreadyKnown Set 缺（{len(missing)}）："
                          + '、'.join(missing))

    return issues


GRAMMAR_ID = re.compile(r"^c(\d{2})-q\d+$")


def check_grammar_quiz():
    """grammar-quiz.html 題庫完整性（一行一題的格式是本檢查的前提）。"""
    import json
    issues = []
    src = (ROOT / 'grammar-quiz.html').read_text()
    registry = {int(k): v for k, v in
                json.loads((ROOT / 'grammar' / 'chapters.json').read_text()).items()}

    # 頁內 chapters 陣列 == chapters.json
    ch_body = extract_array(src, 'chapters')
    page_ch = {int(m.group(1)): m.group(2) for m in
               re.finditer(r"n:\s*(\d+),\s*title:\s*'([^']+)'", ch_body)}
    if page_ch != registry:
        issues.append(f"[chapters] 頁內 chapters 陣列與 grammar/chapters.json 不一致："
                      f"頁內={sorted(page_ch)} json={sorted(registry)}"
                      + ''.join(f"；第{n}章標題不同" for n in set(page_ch) & set(registry)
                                if page_ch[n] != registry[n]))

    body = extract_array(src, 'grammarCards')
    seen_ids = set()
    per_ch = {}
    for line in body.split('\n'):
        line = line.strip()
        if not line.startswith('{'):
            continue
        gid = re.search(r"id:\s*'([^']+)'", line)
        ch = re.search(r"ch:\s*(\d+)", line)
        typ = re.search(r"type:\s*'([^']+)'", line)
        q = re.search(r"q:\s*'([^']*)'", line)
        ans = re.search(r"answer:\s*'([^']*)'", line)
        expl = re.search(r"explain:\s*'([^']*)'", line)
        batch = re.search(r"batch:\s*(\d+)", line)
        label = gid.group(1) if gid else line[:30]
        if not all([gid, ch, typ, q, ans, expl, batch]):
            issues.append(f"[欄位] {label}：缺必填欄位（id/ch/type/q/answer/explain/batch）")
            continue
        gid, ch, typ, q, ans = gid.group(1), int(ch.group(1)), typ.group(1), q.group(1), ans.group(1)
        m = GRAMMAR_ID.match(gid)
        if not m:
            issues.append(f"[id] {gid}：格式須為 cNN-qM")
        elif int(m.group(1)) != ch:
            issues.append(f"[id] {gid}：前綴 {m.group(1)} ≠ ch {ch}")
        if gid in seen_ids:
            issues.append(f"[重複] id {gid} 出現兩次")
        seen_ids.add(gid)
        if ch not in registry:
            issues.append(f"[ch] {gid}：第 {ch} 章不在 chapters.json")
        per_ch[ch] = per_ch.get(ch, 0) + 1
        if typ == 'mc':
            cm = re.search(r"choices:\s*\[([^\]]*)\]", line)
            choices = re.findall(r"'([^']*)'", cm.group(1)) if cm else []
            if len(choices) < 3:
                issues.append(f"[mc] {gid}：choices 少於 3 個")
            if ans not in choices:
                issues.append(f"[mc] {gid}：answer 不在 choices 裡")
        elif typ == 'cloze':
            if '___' not in q:
                issues.append(f"[cloze] {gid}：題目缺 ___ 空格")
            am = re.search(r"accepted:\s*\[([^\]]*)\]", line)
            accepted = re.findall(r"'([^']*)'", am.group(1)) if am else []
            if not accepted:
                issues.append(f"[cloze] {gid}：缺 accepted 陣列")
            elif ans not in accepted:
                issues.append(f"[cloze] {gid}：answer 不在 accepted 裡")
        else:
            issues.append(f"[type] {gid}：未知題型 {typ}")
    for ch in registry:
        if per_ch.get(ch, 0) < 3:
            issues.append(f"[題數] 第 {ch} 章只有 {per_ch.get(ch, 0)} 題（至少 3）")
    return issues


def check_grammar_pages():
    """grammar/*.html 必須與 grammar.md 同步（產生器 check_only 模式）。"""
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        import build_grammar_pages
        stale = build_grammar_pages.build(check_only=True)
        return [f"[過期] {x}（跑 python3 tools/build_grammar_pages.py 重建）" for x in stale]
    except SystemExit as e:
        return [f"[建置] {e}"]


def main():
    known_md = parse_known_md()
    ok = True
    for path, kana_array, vocab_key, md in [
        (ROOT / 'hiragana-quiz.html', 'cards', 'display', known_md),
        (ROOT / 'katakana-quiz.html', 'katakanaCards', 'word', None),
    ]:
        issues = check_file(path, kana_array, vocab_key, md)
        print(f'== {path.name} ==')
        if issues:
            ok = False
            for i in issues:
                print('  ' + i)
        else:
            print('  全部通過 ✓')
    for name, issues in [('grammar-quiz.html', check_grammar_quiz()),
                         ('grammar/ 章節頁', check_grammar_pages())]:
        print(f'== {name} ==')
        if issues:
            ok = False
            for i in issues:
                print('  ' + i)
        else:
            print('  全部通過 ✓')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
