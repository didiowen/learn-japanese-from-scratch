#!/usr/bin/env python3
"""產生 A5 五十音寫字練習 PDF（平假名＋片假名各一頁，第一格純黑範例＋後面灰色淡字描摹）。"""

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
pdfmetrics.registerFont(TTFont("JP", FONT_PATH))

PAGE_W, PAGE_H = A5  # 148 x 210 mm in points

# ── 版面參數 ──
MARGIN = 8 * mm
CELL = 8 * mm            # 田字格邊長
PRACTICE = 3            # 每字練習空格數（描紅之外）
ROW_GAP = 1.2 * mm       # 同行內每列間距
GROUP_GAP = 2.2 * mm     # 行與行（あ行/か行）間距
COL_GAP = 4 * mm         # 三欄之間
ROMAJI_W = 6 * mm        # 羅馬拼音標籤寬
LABEL_GAP = 1.2 * mm     # 標籤與第一格間距

# 純黑白（灰階）配色，方便黑白印表機列印
INK = (0, 0, 0)                  # 標題、行標籤
SOFT = (0.35, 0.35, 0.35)        # 羅馬拼音
ACCENT = (0, 0, 0)               # 標題底線、行群標籤
GRID = (0.40, 0.40, 0.40)        # 格線
GUIDE = (0.80, 0.80, 0.80)       # 田字格虛線
MODEL = (0, 0, 0)                # 第一格示範字（純黑實心）
TRACE = (0.72, 0.72, 0.72)       # 練習格臨摹字（淡灰實心，單線描摹）

# 平假名 46 音（依行分組）
HIRAGANA = [
    ("あ行", [("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o")]),
    ("か行", [("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko")]),
    ("さ行", [("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so")]),
    ("た行", [("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to")]),
    ("な行", [("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no")]),
    ("は行", [("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho")]),
    ("ま行", [("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo")]),
    ("や行", [("や", "ya"), ("ゆ", "yu"), ("よ", "yo")]),
    ("ら行", [("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro")]),
    ("わ行", [("わ", "wa"), ("を", "wo")]),
    ("ん", [("ん", "n")]),
]

KATAKANA = [
    ("ア行", [("ア", "a"), ("イ", "i"), ("ウ", "u"), ("エ", "e"), ("オ", "o")]),
    ("カ行", [("カ", "ka"), ("キ", "ki"), ("ク", "ku"), ("ケ", "ke"), ("コ", "ko")]),
    ("サ行", [("サ", "sa"), ("シ", "shi"), ("ス", "su"), ("セ", "se"), ("ソ", "so")]),
    ("タ行", [("タ", "ta"), ("チ", "chi"), ("ツ", "tsu"), ("テ", "te"), ("ト", "to")]),
    ("ナ行", [("ナ", "na"), ("ニ", "ni"), ("ヌ", "nu"), ("ネ", "ne"), ("ノ", "no")]),
    ("ハ行", [("ハ", "ha"), ("ヒ", "hi"), ("フ", "fu"), ("ヘ", "he"), ("ホ", "ho")]),
    ("マ行", [("マ", "ma"), ("ミ", "mi"), ("ム", "mu"), ("メ", "me"), ("モ", "mo")]),
    ("ヤ行", [("ヤ", "ya"), ("ユ", "yu"), ("ヨ", "yo")]),
    ("ラ行", [("ラ", "ra"), ("リ", "ri"), ("ル", "ru"), ("レ", "re"), ("ロ", "ro")]),
    ("ワ行", [("ワ", "wa"), ("ヲ", "wo")]),
    ("ン", [("ン", "n")]),
]

# 三欄分配：保持行群完整
COLS = [(0, 3), (3, 6), (6, 11)]  # group index ranges per column


def draw_cell(c, x, y, char=None, mode=None):
    """在 (x, y) 左下角畫一個田字格。
    mode='model' → 純黑實心示範字；mode='trace' → 淡灰實心臨摹字。"""
    # 田字格外框
    c.setStrokeColorRGB(*GRID)
    c.setLineWidth(0.5)
    c.rect(x, y, CELL, CELL, stroke=1, fill=0)
    # 內部十字虛線輔助
    c.setStrokeColorRGB(*GUIDE)
    c.setLineWidth(0.3)
    c.setDash(1.2, 1.2)
    c.line(x + CELL / 2, y, x + CELL / 2, y + CELL)
    c.line(x, y + CELL / 2, x + CELL, y + CELL / 2)
    c.setDash()
    if not char:
        return
    fs = CELL * 0.74
    cx = x + CELL / 2
    by = y + CELL / 2 - fs * 0.36   # 垂直置中校正
    # 兩種都用實心填色（避免描邊產生雙線），只差顏色
    c.setFont("JP", fs)
    c.setFillColorRGB(*(MODEL if mode == "model" else TRACE))
    c.drawCentredString(cx, by, char)


def draw_row(c, x, y, char, romaji):
    """畫一列：羅馬拼音 + 純黑示範格 + 淡灰臨摹格。y 為該列底部。"""
    c.setFillColorRGB(*SOFT)
    c.setFont("Helvetica", 6.5)
    c.drawRightString(x + ROMAJI_W, y + CELL / 2 - 2.3, romaji)
    cx = x + ROMAJI_W + LABEL_GAP
    draw_cell(c, cx, y, char, mode="model")     # 第一格：純黑示範
    for i in range(PRACTICE):
        cx += CELL
        draw_cell(c, cx, y, char, mode="trace")  # 後面：淡灰臨摹


def draw_page(c, title, subtitle, groups):
    # 標題
    c.setFillColorRGB(*INK)
    c.setFont("JP", 15)
    c.drawString(MARGIN, PAGE_H - MARGIN - 12, title)
    c.setFillColorRGB(*SOFT)
    c.setFont("JP", 7.5)
    c.drawString(MARGIN, PAGE_H - MARGIN - 22, subtitle)
    # 標題底線
    c.setStrokeColorRGB(*ACCENT)
    c.setLineWidth(1)
    c.line(MARGIN, PAGE_H - MARGIN - 27, PAGE_W - MARGIN, PAGE_H - MARGIN - 27)

    usable_w = PAGE_W - 2 * MARGIN
    col_w = (usable_w - COL_GAP * 2) / 3
    top = PAGE_H - MARGIN - 36  # 內容起始 y（頂端）

    for ci, (gs, ge) in enumerate(COLS):
        x = MARGIN + ci * (col_w + COL_GAP)
        y = top
        for gi in range(gs, ge):
            gname, kanas = groups[gi]
            # 行群標籤
            c.setFillColorRGB(*ACCENT)
            c.setFont("JP", 7)
            c.drawString(x, y - 6, gname)
            y -= 8.5
            for (char, romaji) in kanas:
                y -= CELL
                draw_row(c, x, y, char, romaji)
                y -= ROW_GAP
            y -= GROUP_GAP


def main(out_path):
    c = canvas.Canvas(out_path, pagesize=A5)
    c.setTitle("五十音寫字練習")
    draw_page(
        c,
        "ひらがな　平假名 五十音 寫字練習",
        "第一格為純黑範例，後面各格描摹灰色淡字。",
        HIRAGANA,
    )
    c.showPage()
    draw_page(
        c,
        "カタカナ　片假名 五十音 寫字練習",
        "第一格為純黑範例，後面各格描摹灰色淡字。",
        KATAKANA,
    )
    c.showPage()
    c.save()
    print("wrote", out_path)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "kana-writing-practice.pdf")
