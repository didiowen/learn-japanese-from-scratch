# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

台灣學習者日文學習系統——假名記憶、單字管理、測驗工具維護。學習者母語台語、華語，略懂粵語，熟悉注音符號和漢字。平假名、片假名五十音（含濁音、半濁音）皆已完成，目前進入單字擴充與會話學習階段。

## 記憶鉤優先順序

每個假名必須附**漢字來源** ＋ **記憶鉤**（依以下優先順序選擇）：

1. **台語文言音**——子音母音都對才用
2. **台語白話音**——補充或替代
3. **華語**——台語子音不對時（例：奴 nú → ぬ、祢 nǐ → ね）
4. **粵語**——漢音層接近（例：知 zi → ち chi）
5. **注音字形**——形近但音不近時（例：へ 像 ㄟ）
6. **英文聯想**——以上都不近時
7. **純字形規則**——濁點、合讀等

台語子音不對就不用台語，改用其他工具。漢字來源是最優先的字形聯想。

## 發音規則（九條，片假名完全適用）

1. **濁點（゛）**——清音加兩點，子音變有聲（た→だ、か→が）
2. **半濁點（゜）**——は行專用，回到古代 p 音（は→ぱ）；は行古代念 p，演變成 h（清）/b（濁）/p（半濁）
3. **小字合讀（拗音）**——ょゅゃ 縮小跟前面合讀，母音被取代
4. **長音**——a/i/u 用同母音延長；e 行用い；o 行用う
5. **ん 特殊性**——打字要打 nn
6. **っ 促音**——停頓一拍再爆發，台語入聲音感接近
7. **助詞雙重發音**——は念 wa、を念 o
8. **母音無聲化**——i 和 u 在特定位置消音（です→des）
9. **清音弱化**——單字中間的清音自然有聲化

## 工具檔案

| 檔案 | 用途 |
|------|------|
| `hiragana-quiz.html` | 平假名互動測驗（五十音＋單字，SRS） |
| `katakana-quiz.html` | 片假名互動測驗（五十音＋單字，SRS） |
| `hiragana.md` | 平假名字表、發音規則、語法筆記 |
| `katakana.md` | 片假名字表、單字分類 |
| `vocabulary.md` | 所有單字，依主題分類（疑問詞、飲食、時間、顏色等） |
| `conversation.md` | 會話筆記（基本用語、購物、點餐等情境） |
| `language-notes.md` | 台語／粵語／注音記憶鉤對照表 |
| `already-known.md` | 已知單字片語，在測驗中減少出現頻率 |
| `kanji.md` | 漢字筆記（字表、發音規則、單字分類） |
| `grammar.md` | N5 語法筆記（G1–G12，句型、活用、例句） |
| `PRODUCT.md` | 設計策略文件（受眾、品牌個性、設計原則，impeccable skill 使用） |

參考文件（`.claude/skills/japanese-learning/references/` 目錄）：
- `quiz-structure.md` — 測驗 HTML 結構與更新方法
- `language-correspondences.md` — 台語／粵語音對應詳表
- `vocab-categories.md` — 單字分類與 topic 標籤說明

## 工作流程

### General workflow

1. **Explore first, plan, then code** — read relevant files and understand the current state before making changes.
2. **Smoke test before commit** — for scripts, a dry-run counts; for notes/edits, verify the output looks correct before staging.
3. **Check git status before starting work** — confirm the correct branch and no unexpected prior changes.
4. **Read an existing note before creating a new one** — match frontmatter format and conventions rather than guessing.
5. **One concern per commit** — keep commits focused; don't bundle unrelated changes.

### 學新假名
**每次只介紹 5–10 個**，確認記熟後再進下一批。不要一次把整行或整個五十音全部教完。

漢字來源 → 記憶鉤（依優先順序）→ 清濁音一起介紹 → 形近字提示 → 更新筆記和測驗

拆解格式：
| 假名 | 發音 | 新/舊 |
|------|------|-------|
| X | Y | ✅/🆕 |

有新字就單獨介紹，全部學過才說「全學過！」。

### 學新單字
1. 拆解每個假名（標明新/舊）
2. 說明漢字來源和台語連結（如有）
3. 同音異義詞提示
4. 更新測驗 vocabCards，格式：`{ meaning, display, reading, kanji?, topic, round }`
   - `meaning`：**純中文意思**，不能夾雜日文假名（填 `'哪裡'`，不是 `'どこ（哪裡）'`）
   - `kanji`：有常見漢字寫法就必須加（一杯、何処、服、耳等）；純口語／擬聲語／純假名詞可省略（ゆっくり、じゃあね）；片假名外來語不加
5. 將單字加入 `recentBatch`（見下方說明）
6. 將單字加入對應筆記檔，並更新 frontmatter 的 `date > updated`：
   - 一般單字 → `vocabulary.md` 對應主題區塊
   - 會話句型／口語表達 → `conversation.md` 對應情境區塊
   - 片假名外來語 → `katakana.md` 對應單字區塊

**單字表格式**：漢字 ｜ 假名 ｜ 羅馬拼音 ｜ 意思

**topic 標籤**：`greeting` / `food` / `family` / `time` / `color` / `number` / `nature` / `daily` / `question`

### recentBatch 機制（新單字優先出現）

`hiragana-quiz.html` 和 `katakana-quiz.html` 各有一個 `recentBatch` 物件，控制未被 SRS 記錄的單字出現優先度：

```js
const recentBatch = {
  '單字': 批次號,  // 數字越大 = 越近加入 = 越優先
};
```

- 每次新增單字，加入 `recentBatch` 並使用**目前最大批次號 + 1**
- 目前最大批次號：**4**（2026-05-02），下次新增請用 **5**
- 批次號轉換為 `nextReview = -(批次號 × 5)`，確保新字在 `pickFromQueue` 排序中優先
- 已被 SRS 記錄過的字不受影響

### 「我本來就會」的單字

使用者說某個單字「本來就會」時，需同時更新兩處：
1. `already-known.md`：加入表格（漢字 ｜ 假名 ｜ 羅馬拼音 ｜ 意思）
2. 對應測驗的 `alreadyKnown` Set：加入假名（hiragana 用 `display`、katakana 用 `word`）

`alreadyKnown` 中的字初始 SRS 等級為 2（間隔 8 題），降低出現頻率。

### 更新學習日誌
每次修改任何 `.md` 筆記檔後，在 `log.md` 新增條目：
- 標題格式：`## YYYY-MM-DD HH:MM:SS`（GMT+8，精確到秒）
- 內容：更新了什麼（學了哪些假名／單字，或修正了什麼）

### 更新測驗 HTML
詳見 `.claude/skills/japanese-learning/references/quiz-structure.md`。更新時用 Python 處理中文字串避免編碼問題，覆寫前先確認。

**單字輪次（round）計算規則**（嚴格字符規則）：
- `word_round = max(所有字符的輪次)`
- 平假名輪次：R1（あ・ら行・ん）、R2（か・が・な行）、R3（さ・ざ・や・わ行）、R4（た・だ・ま行）、R5（は・ば・ぱ行）
- 小假名 ゃゅょ 及 っ 依所屬行計算（ゃゅょ → R3，っ → R5）
- 片假名輪次規則相同

### 設計維護（index.html）

`index.html` 採現代日式風格，設計原則詳見 `PRODUCT.md`。UI 設計任務使用 `/impeccable` skill。

- **配色**：OKLCH，禁用純 `#000`/`#fff`；底色微暖白、墨色深靛、強調磚紅
- **字型**：Noto Serif JP（標題）+ Noto Sans TC（內文）
- **無障礙**：最小字體 18px，WCAG AA，互動目標 ≥ 44×44px，尊重 prefers-reduced-motion
- **禁止**：gradient text、glassmorphism、等高卡片格、side-stripe border

### Push 後立即建 PR
每次 `git push` 後，若該分支**尚無開啟的 PR**，立即用 GitHub MCP 工具建立，不等使用者手動開。建立後**詢問使用者是否要立即合併**，如果是則馬上執行 merge。

PR 描述格式：
```
## 使用者指令
（使用者當時說了什麼）

## 修改摘要
（每個 commit 對應做了什麼改動）
```

- 同一次作業的多個 commit 合併在同一個 PR
- 建立後將 PR 網址回報給使用者
- **PR 建立後不需要主動檢查 CI 狀態或 review 意見**，等使用者通知再處理

## 互動風格

- 繁體中文回答
- 解釋新假名：漢字來源 ＋ 記憶鉤 ＋ 清濁音一起介紹
- 形近字主動提示
- 語法說明穿插在真實單字裡，不抽象解釋
- 台語連結是核心優勢，積極找對應

## 重要語言學背景

- 日語音読み和台語文言音同樣保留中古漢語，高度對應
- 台語日語借詞超過 1000 個（歐巴桑、便當、名刺、運將等）
- 平假名是漢字草書演變，片假名是漢字楷書演變
- 台語有文言音和白話音兩套，文言音更接近日語音読み
