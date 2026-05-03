# 測驗 HTML 結構與更新方法

## hiragana-quiz.html 資料結構

### kanaCards 格式（五十音測驗）

```js
{
  char: 'あ',       // 平假名字元
  reading: 'a',    // 羅馬拼音
  source: '安',     // 漢字來源
  hint: '安（an）→ あ', // 記憶鉤提示文字
  round: 1         // 輪次（1–5）
}
```

輪次分組：
- R1：あ・ら行・ん
- R2：か・が・な行
- R3：さ・ざ・や・わ行
- R4：た・だ・ま行
- R5：は・ば・ぱ行＋拗音

### vocabCards 格式（單字測驗）

```js
{
  meaning: '媽媽',            // 純中文意思，不夾雜日文假名
  display: 'おかあさん',       // 測驗顯示的假名（也是 SRS key）
  reading: 'okaasan',        // 羅馬拼音
  kanji: 'お母さん',           // 漢字（可選；有標準漢字寫法時一定要加）
  topic: 'family',           // 分類標籤
  round: 5                   // 輪次（word_round = max(所有字符輪次)）
}
```

**kanji 欄位規則**：
- 有常見漢字寫法就必須加（例：一杯、何処、服、耳）
- 純口語表達／擬聲語／純假名詞可省略（例：ゆっくり、ぴったり、じゃあね）
- 片假名外來語不加（ポケット、ゲーム 等在 katakana-quiz.html）

**topic 標籤**：`greeting` / `food` / `family` / `time` / `color` / `number` / `nature` / `daily` / `question`

### alreadyKnown Set

```js
const alreadyKnown = new Set([
  'こんにちは', 'ありがとう', ...
]);
```

初始 SRS level 為 2（間隔 8 題），降低出現頻率。加入時用 `display` 欄位值。

### recentBatch 物件

```js
const recentBatch = {
  // 批次 4（2026-05-02 最新）
  'いっぱい': 4, 'そら': 4, ...
  // 批次 3（2026-05-01）
  'いっしょに': 3, ...
};
```

批次號越大 = 越近加入 = 優先出現。批次 N → `nextReview = -(N × 5)`。
目前最大批次號：**4**（下次新增用 **5**）。

---

## katakana-quiz.html 資料結構

### katakanaCards 格式

```js
{
  char: 'ア',
  hiragana: 'あ',   // 對應平假名
  kanji: '阿',      // 漢字來源
  hint: '阿（a）→ ア',
  round: 1
}
```

### vocabCards 格式（片假名單字）

```js
{
  word: 'コーヒー',   // 片假名（SRS key）
  reading: 'kōhī',   // 羅馬拼音
  meaning: '咖啡',    // 純中文意思
  hint: 'コーヒー（kōhī）', // 作答後提示文字
  topic: 'food',
  round: 2
}
```

---

## 更新方法

### 新增 vocabCard（平假名測驗）

1. 在 `vocabCards` 陣列末尾加入新物件
2. round 計算：`max(所有字符輪次)`，小假名ゃゅょ → R3，っ → R5
3. 在 `recentBatch` 最新批次加入 display 值
4. 若為「本來就會」的字：加入 `alreadyKnown`，**不加** `recentBatch`

**編碼注意**：含中文或日文字元時用 Python 處理，避免 bash heredoc 編碼問題：

```python
with open('hiragana-quiz.html', 'r', encoding='utf-8') as f:
    content = f.read()
# 修改 content
with open('hiragana-quiz.html', 'w', encoding='utf-8') as f:
    f.write(content)
```

### 同音異義詞處理

同一 `display` 對應多個意思（如 さけ＝鮭魚／酒），**兩張牌都保留**。
`checkVocabMultiple` 已實作：jp→zh 模式下收集所有相同 display 的 meaning，任一均可接受。

### 刪除 vocabCard

同時從以下兩處刪除：
1. `vocabCards` 陣列中的物件行
2. `recentBatch` 中的對應 key（若有）
