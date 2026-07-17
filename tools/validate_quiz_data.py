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
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
