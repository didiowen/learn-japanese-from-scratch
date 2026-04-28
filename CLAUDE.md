# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

台灣學習者日文學習系統——假名記憶、單字管理、測驗工具維護。學習者母語台語、華語，略懂粵語，熟悉注音符號和漢字。

## 工具檔案

| 檔案 | 用途 |
|------|------|
| `hiragana-quiz.html` | 平假名互動測驗（五十音＋單字，SRS） |
| `katakana-quiz.html` | 片假名互動測驗（五十音＋單字，SRS） |
| `平假名.md` | 主筆記（字表、發音規則、單字分類、語法） |
| `片假名.md` | 片假名筆記（字表、單字分類） |
| `語言對照筆記.md` | 台語／粵語／注音記憶鉤對照表 |
| `本來就會的單字片語.md` | 已知單字片語，在測驗中減少出現頻率 |
| `會話.md` | 會話筆記（旅遊常用場景） |
| `漢字.md` | 漢字筆記（漢字字表、發音規則、單字分類） |

參考文件（`.claude/skills/japanese-learning/references/`）：
- `quiz-structure.md` — 測驗 HTML 結構與更新方法
- `language-correspondences.md` — 台語／粵語音對應詳表
- `vocab-categories.md` — 單字分類與 topic 標籤說明

## 更新測驗 HTML

詳見 `quiz-structure.md`。更新時用 Python 處理中文字串避免編碼問題，覆寫前先確認。

## 日文學習會話

假名教學、記憶鉤、發音規則、學習流程等教學細節，見 `.claude/skills/japanese-learning/SKILL.md`。
