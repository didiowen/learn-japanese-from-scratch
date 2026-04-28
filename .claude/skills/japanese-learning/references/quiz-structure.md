\# hiragana-quiz.html 結構說明



\## 資料結構



\### kanaCards 格式



```json

{

&#x20; "kanaCards": \[

&#x20;   {

&#x20;     "kana": "あ",

&#x20;     "furigana": "a",

&#x20;     "source": "安",

&#x20;     "mnemonics": {

&#x20;       "hokkien\_literary": "an",

&#x20;       "hokkien\_colloquial": "a",

&#x20;       "cantonese": "a",

&#x20;       "zhuyin": "ㄚ",

&#x20;       "note": "安"

&#x20;     },

&#x20;     "status": "old"

&#x20;   }

&#x20; ]

}

```



\### vocabCards 格式



```json

{

&#x20; "vocabCards": \[

&#x20;   {

&#x20;     "kanji": "母",

&#x20;     "hiragana": "ははお",

&#x20;     "romaji": "haha-o",

&#x20;     "meaning": "母親",

&#x20;     "source": "母（は）＋お（敬語接尾辭）",

&#x20;     "mnemonic": "波婆（濁音變b）",

&#x20;     "topic": "family",

&#x20;     "status": "new"

&#x20;   }

&#x20; ]

}

```



\## topic 標籤



| topic | 說明 | 範例 |

|-------|------|------|

| greeting | 問候 | こんにちは（你好） |

| food | 食物 | 水、食べ物 |

| family | 家族 | 母、父 |

| time | 時間 | 時間、今 |

| color | 顏色 | 赤、青 |

| number | 數字 | 一、二 |

| nature | 自然 | 木、水、火 |

| daily | 日常 | 水、食べる |

| question | 疑問詞 | 何、誰 |



\## 更新工作流



\### 新增平假名



1\. 提供漢字來源 + 台語/粵語/注音記憶鉤

2\. 清濁音一起介紹

3\. 在 kanaCards 陣列中新增：



```json

{

&#x20; "kana": "ぬ",

&#x20; "furigana": "nu",

&#x20; "source": "奴",

&#x20; "mnemonics": {

&#x20;   "hokkien\_literary": "noo",

&#x20;   "hokkien\_colloquial": "noo",

&#x20;   "cantonese": "nou",

&#x20;   "zhuyin": "ㄋ",

&#x20;   "note": "奴"

&#x20; },

&#x20; "status": "new"

}

```



\### 新增單字



1\. 拆解每個假名，標明新/舊

2\. 說明漢字來源（如有台語連結更佳）

3\. 在 vocabCards 陣列中新增：



```json

{

&#x20; "kanji": "水",

&#x20; "hiragana": "みず",

&#x20; "romaji": "mizu",

&#x20; "meaning": "水",

&#x20; "source": "水（み）+ ず（音讀結合）",

&#x20; "mnemonic": "美（mi）+ 宙（zu）",

&#x20; "topic": "nature",

&#x20; "status": "new"

}

```



\## SRS 複習邏輯



\- `status: "new"` — 今日學習

\- `status: "old"` — 已掌握，進入複習週期



複習間隔（建議）：

\- 新單字：1 天後

\- 複習 1 次：3 天後

\- 複習 2 次：7 天後

\- 複習 3 次：14 天後

\- 複習 4 次：30 天後

