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
| `grammar.md` | N5 語法筆記（G1–G12，句型、活用、例句）——**文法內容的唯一正本**，章節頁由它生成 |
| `grammar/` | 文法章節 HTML（`NN.html`＋`index.html`，由 `tools/build_grammar_pages.py` 從 grammar.md 產生，**不要手改**；`chapters.json` 是「進度項編號→grammar.md 標題」登錄表、`chapter.css` 是手寫樣式） |
| `grammar-quiz.html` | 文法 SRS 測驗（填空輸入＋語感選擇；題庫 `grammarCards` 內嵌，SRS 走 quiz-common.js） |
| `tools/build_grammar_pages.py` | 章節頁產生器（`--check` 供驗證器比對是否過期） |
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

- **批次規則：同一天加入的算同一批**——當天若已有批次號就沿用，否則用目前最大批次號 + 1
- 目前最大批次號**以該測驗 HTML 內 recentBatch 的實際最大值為準**（新增前先查，不在此記死數字）
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

**每次更新 vocabCards／alreadyKnown／recentBatch 後，必須跑 `python3 tools/validate_quiz_data.py`**——它會重算所有 round、查重複條目、比對 already-known.md 與 alreadyKnown Set，全部通過才能 commit。

**單字輪次（round）計算規則**（嚴格字符規則）：
- `word_round = max(所有字符的輪次)`
- 平假名輪次：R1（あ・ら行・ん）、R2（か・が・な行）、R3（さ・ざ・や・わ行）、R4（た・だ・ま行）、R5（は・ば・ぱ行）
- 小假名 ゃゅょ 及 っ 依所屬行計算（ゃゅょ → R3，っ → R5）
- 片假名輪次規則相同

### 設計維護（index.html）

`index.html` 採現代日式風格，設計原則詳見 `PRODUCT.md`。UI 設計任務使用 `/impeccable` skill。

- **配色**：OKLCH，禁用純 `#000`/`#fff`；底色微暖白、墨色深靛、強調磚紅
- **字型**：Klee One（標題，與 index.html 一致）+ Noto Sans TC（內文）
- **無障礙**：最小字體 18px，WCAG AA，互動目標 ≥ 44×44px，尊重 prefers-reduced-motion
- **禁止**：gradient text、glassmorphism、等高卡片格、side-stripe border

### 文法章節頁與文法測驗

- **grammar.md 是文法內容的唯一正本**；`grammar/NN.html` 與 `grammar/index.html` 是 `tools/build_grammar_pages.py` 的建置產物，**絕對不要手改**（改了下次重建就沒了，驗證器也會報「過期」）。`_sidebar.md` 與 `notes/`（docsify）照舊渲染 grammar.md 當完整筆記檢視，兩者並存是刻意的，不要「修掉」。
- grammar.md **只能用這個 markdown 子集**：`###`/`####` 小標、段落、行尾兩空格換行、`**粗體**`、`` `行內程式碼` ``、GFM 表格、`>` 引言、``` 圍欄、單層 `-`/`1.` 清單、`---`。產生器認不得的語法會直接建置失敗。
- 改了 grammar.md（已上架章節的部分）→ 必跑 `python3 tools/build_grammar_pages.py` 重建，再跑 `python3 tools/validate_quiz_data.py`；precommit hook 會擋住過期頁面的 commit。
- `grammar-quiz.html` 的題庫 `grammarCards` 一行一題：`id`（`cNN-qM`，NN=進度項編號）是 SRS key——**修錯字保留 id、改題意換新 id 並刪舊行**；`batch` 同天同批、越大越新（未做過的題 `nextReview = -(batch×5)` 優先出現）；cloze 題目必含 `___` 且 `accepted` 含 `answer`；mc `choices` ≥3 且含 `answer`；每題必有 `explain`。頁內 `chapters` 陣列必須與 `grammar/chapters.json` 一致（驗證器會比對）。

### 每日教學排程（17:30，文法＋單字兩軌）

每天 17:30，vault 的 `com.didiowen.nihongo-grammar-daily` 排程（`~/LFCxBVB/X/scripts/nihongo-grammar-notify.sh`）為文法與單字各起一個獨立的 headless session：

- **文法軌（2026-09-05 起改版）**：依 `grammar-daily-progress.md` 的規則推進一章——（新增類先寫進 grammar.md）→ 登錄 `grammar/chapters.json` 與 `grammar-quiz.html` 的 `chapters`、追加 3–5 題進 `grammarCards` → 跑產生器＋驗證器 → Telegram **只發短通知＋連結**（章節頁＋測驗頁），教學內容在網頁、複習交給測驗頁的 SRS。`grammar-daily-latest.md` 只是 10 行紀錄（日期／編號／連結／新題 id）。
- **單字軌（不變）**：教一批單字＋出 3–5 題發到群裡，完成收錄（`vocabulary.md`／`kanji.md`／quiz HTML）並跑 `tools/validate_quiz_data.py`；訊息開頭仍有「上次複習」。

**批改規則（2026-09-05 起）**：**文法不再在 Telegram 批改**——文法題目都在 `grammar-quiz.html`，答對答錯由測驗頁自己記 SRS，進度表備註欄改記概念性的觀察（哪類文法點反覆卡住），不再逐題記分。**單字照舊**：使用者回覆單字題答案時，先讀 `vocab-daily-latest.md` 對題再批改，批改完在 `log.md` 記一筆、錯處補進 `vocab-daily-progress.md` 備註欄；狀態 ✅ 排程已標好，不要重複標。

### commit／push 節奏

**每完成一次更動就 commit ＋ push，不要累積在工作區。** 未 commit 的改動是最脆弱的狀態——並行的 session、排程、或下一輪操作都可能把它掃掉。

- **push 一律推 `claude-playground`，不要推 `main`。** `main` 有分支保護（Changes must be made through a pull request），直推只是靠管理者權限 bypass 掉自己設的規則；本機的 branch guard 也會擋下在 `main` 上的 commit。工作樹平常就停在 `claude-playground`
- 一次更動＝一個 concern：新增一批假名／單字、修一個筆記錯誤、更新一次測驗資料，各自成一個 commit，不要把不相關的改動綁在一起
- 照原有流程做完再提交：檔案修改（`vocabulary.md`／`kanji.md`／`hiragana-quiz.html`／`katakana-quiz.html`／`log.md`）、`validate_quiz_data.py` 驗證、frontmatter 的 `updated` 更新，全部通過才 commit
- commit ＋ push **不必先問使用者**，那是預設動作；要問的是下面的 PR

### PR／merge 節奏

**不要每次 push 都開 PR。** 讓 commit 在分支上累積，等到一段工作告一段落、或使用者開口時，再一次開 PR 並合併。GitHub Actions 額度是共用且有限的，一個小改動開一個 PR 純粹浪費。

- PR 一律 `claude-playground` → `main`
- **每日 23:30 會自動開 PR 並合併**（vault 排程 `com.didiowen.nihongo-daily-merge` → `~/LFCxBVB/X/scripts/nihongo-daily-merge.sh`）：`claude-playground` 有領先 `main` 的 commit 就開 PR、合併、把分支快轉回 main；沒有就靜默結束。所以**平常不需要手動開 PR**，push 完就交給它
- **GitHub Pages 從 `main` 根目錄發佈**，所以測驗網站（`hiragana-quiz.html` 等）的更新要等合併後才上線——正常情況就是當晚 23:30。使用者若急著看到某個改動，才需要立刻手動開 PR
- 手動 merge 之後記得把 `claude-playground` 快轉回 `main`（`git fetch origin && git push origin origin/main:claude-playground`），否則它會越拖越舊，下次 PR 開始出現無謂的衝突；23:30 那支排程自己會做這一步
- 使用者明確說「開 PR」「merge」「cpprm」時直接照做，不需再問
- 一段工作結束時可以主動問一句「要開 PR 嗎」，但不要停在那裡等——commit ＋ push 該做的照做
- 同一批的多個 commit 合併在同一個 PR；建立後把 PR 網址回報給使用者
- smoke test 通過即視為可合併；**PR 建立後不需要主動檢查 CI 狀態或 review 意見**，等使用者通知再處理

PR 描述格式：
```
## 使用者指令
（根據上下文完整理解語意而不是單純逐字）

## 修改摘要
（每個 commit 對應做了什麼改動）
```

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
