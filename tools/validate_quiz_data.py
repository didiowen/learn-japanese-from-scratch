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
8. vocab/ 課程頁是否與 vocab-lessons.md 同步（import build_vocab_pages 跑 --check）
9. hiragana-quiz.html 的 lessonBatch／lessonTitles 與 vocab/batches.json 一致
   （每批至少登錄一個字、字都存在於 vocabCards）

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


def check_vocab_quiz():
    """vocab-quiz.html（課程單字測驗）：批次登錄正確，且與平假名測驗頁的單字池互斥。"""
    import json
    issues = []
    src = (ROOT / 'vocab-quiz.html').read_text()
    registry = {int(k): v.split('：', 1)[1] for k, v in
                json.loads((ROOT / 'vocab' / 'batches.json').read_text()).items()}

    block = extract_array(src, 'vocabCards')
    cards = re.findall(r"\{[^}]*\}", block)
    if not cards:
        return ['[vocabCards] 找不到任何卡片']

    batches, seen = set(), {}
    for c in cards:
        def field(name):
            m = re.search(rf"{name}:\s*'([^']*)'", c)
            return m.group(1) if m else None
        disp, mean, read = field('display'), field('meaning'), field('reading')
        bm = re.search(r"batch:\s*(\d+)", c)
        if not (disp and mean and read and bm):
            issues.append(f'[欄位] 卡片缺 meaning／display／reading／batch：{c[:60]}')
            continue
        b = int(bm.group(1))
        batches.add(b)
        # batch 0 ＝ 預習（還沒教到的字），本來就不會在登錄表裡
        if b != 0 and b not in registry:
            issues.append(f'[batch] 「{disp}」的批次 {b} 不在 vocab/batches.json')
        key = (disp, field('kanji'))
        if key in seen:
            issues.append(f'[重複] 「{disp}」（kanji={key[1]}）出現兩次')
        seen[key] = c
    for b in registry:
        if b not in batches:
            issues.append(f'[batch] 批次 {b} 一張卡都沒有（該批教的新字要加進來）')

    tm = re.search(r'const lessonTitles = \{(.*?)\n\};', src, re.S)
    titles = ({int(n): v for n, v in re.findall(r"(\d+):\s*'([^']+)'", tm.group(1))}
              if tm else {})
    titles.pop(0, None)   # 預習不是課程批次，不參與比對
    if titles != registry:
        issues.append(f'[lessonTitles] 與 vocab/batches.json 不一致：'
                      f'頁內={sorted(titles)} json={sorted(registry)}')

    # 互斥不變量：課程字搬到本頁後，舊測驗頁不得再持有同一個字，否則同一字兩頁各排一次。
    # **必須用（假名, 漢字）成對比較**——同音異字是不同的字：批次28 的 橋/虫/鳥/一回 與舊頁的
    # 箸/蒸し/鶏/一階 假名相同、漢字不同，只比假名會把它們誤判成重複而讓當天的 pipeline 整天失敗。
    for other in ('hiragana-quiz.html', 'katakana-quiz.html'):
        osrc = (ROOT / other).read_text()
        oname = 'vocabCards' if other.startswith('hiragana') else 'katakanaCards'
        key = 'display' if other.startswith('hiragana') else 'word'
        others = set()
        for c in re.findall(r"\{[^}]*\}", extract_array(osrc, oname)):
            km = re.search(rf"{key}:\s*'([^']+)'", c)
            if km:
                kj = re.search(r"kanji:\s*'([^']*)'", c)
                others.add((km.group(1), kj.group(1) if kj else None))
        dup = sorted(set(seen) & others)
        if dup:
            issues.append(f'[互斥] 這些字（假名＋漢字都相同）同時在 {other}：'
                          + '、'.join(f'{d}（{k or "無漢字"}）' for d, k in dup))
    return issues


def check_pairings():
    """grammar/pairings.json：一課＝一個文法項＋一個單字批次。"""
    import json
    issues = []
    pf = ROOT / 'grammar' / 'pairings.json'
    if not pf.exists():
        return ['[配對] 找不到 grammar/pairings.json']
    raw = json.loads(pf.read_text())
    # 值可以是單一整數或整數陣列（一個文法項配多批單字），一律正規化成 list
    pair = {int(k): ([int(x) for x in v] if isinstance(v, list) else [int(v)])
            for k, v in raw.items()}

    def rows(name):
        src = (ROOT / name).read_text()
        return {int(m.group(1)) for m in
                re.finditer(r'^\| (\d+) \|[^|]+\|[^|]*\|\s*[✅⬜🟡]\s*\|', src, re.M)}
    gitems, vbatches = rows('grammar-daily-progress.md'), rows('vocab-daily-progress.md')

    for g, bs in sorted(pair.items()):
        if g not in gitems:
            issues.append(f'[配對] 文法項 {g} 不在 grammar-daily-progress.md')
        if not bs:
            issues.append(f'[配對] 文法項 {g} 的配對是空的——沒有要配就整筆刪掉')
        for v in bs:
            if v not in vbatches:
                issues.append(f'[配對] 單字批次 {v} 不在 vocab-daily-progress.md')
    used = [v for bs in pair.values() for v in bs]
    dup = sorted({v for v in used if used.count(v) > 1})
    if dup:
        issues.append(f'[配對] 這些單字批次被配給兩個以上的文法項：{dup}')
    unpaired = sorted(vbatches - set(used))
    if unpaired:
        issues.append(f'[配對] 這些單字批次沒有配對，永遠不會被教到：{unpaired}')
    return issues


def check_vocab_pages():
    """vocab/*.html 必須與 vocab-lessons.md 同步（產生器 check_only 模式）。"""
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        import build_vocab_pages
        stale = build_vocab_pages.build(check_only=True)
        return [f"[過期] {x}（跑 python3 tools/build_vocab_pages.py 重建）" for x in stale]
    except SystemExit as e:
        return [f"[建置] {e}"]


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
                         ('grammar/ 章節頁', check_grammar_pages()),
                         ('vocab/ 課程頁', check_vocab_pages()),
                         ('vocab-quiz.html 課程單字', check_vocab_quiz()),
                         ('文法↔單字配對', check_pairings())]:
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
