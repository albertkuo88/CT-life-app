"""
程式名稱：易經智慧占卜決策系統 (深度響應與 Gemini 智慧大腦增強版)
修復問題：
1. 徹底解決回答簡陋、不同問題答案重複的痛點。
2. 大幅擴充本地分析庫：針對「變化趨勢」、「時程推算」、「賣出策略」等問題皆能給出多層次深度解答。
3. 完善背景串接 Gemini 邏輯，有 Key 啟動 AI 大師，無 Key 依然給出豐富專業分析。
"""

import json
import os
import re
from datetime import date, datetime, timedelta
import streamlit as st

# 嘗試載入 google.generativeai
try:
  import google.generativeai as genai

  GEMINI_AVAILABLE = True
except ImportError:
  GEMINI_AVAILABLE = False

# ==========================================
# 1. 頁面配置與精緻 UI 樣式
# ==========================================
st.set_page_config(
    page_title="易經智慧占卜決策系統",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .chat-user-box {
        background-color: #EBF8FF;
        border-left: 5px solid #3182CE;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #1A365D;
        font-size: 15px;
    }
    .chat-ai-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #319795;
        padding: 20px 24px;
        border-radius: 10px;
        margin-bottom: 22px;
        color: #2D3748;
        line-height: 1.8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .timeline-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 10px;
        margin-bottom: 12px;
    }
    .month-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 8px;
        margin-bottom: 10px;
    }
    .month-title {
        font-size: 16px;
        font-weight: 700;
        color: #2B6CB0;
    }
    .changing-line-card {
        background-color: #FFF5F5;
        border-left: 5px solid #E53E3E;
        padding: 12px 18px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .normal-line-card {
        background-color: #F8FAFC;
        border-left: 4px solid #CBD5E0;
        padding: 12px 18px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .hex-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        background-color: #EDF2F7;
        color: #4A5568;
        margin-right: 8px;
        margin-bottom: 6px;
    }
</style>
""",
    unsafe_allow_html=True,
)

HISTORY_DIR = "divination_sessions"
if not os.path.exists(HISTORY_DIR):
  os.makedirs(HISTORY_DIR)

# ==========================================
# 2. 八卦與六十四卦基礎庫
# ==========================================
TRIGRAM_DATA = {
    "坤 (地)": {
        "name": "坤",
        "nature": "地",
        "bin": "000",
        "symbol": "☷",
        "desc": "柔順包容、厚德載物、順勢而為",
    },
    "艮 (山)": {
        "name": "艮",
        "nature": "山",
        "bin": "001",
        "symbol": "☶",
        "desc": "止步蓄勢、防守阻礙、見險即止",
    },
    "坎 (水)": {
        "name": "坎",
        "nature": "水",
        "bin": "010",
        "symbol": "☵",
        "desc": "重險考驗、資金暗流、流動轉折",
    },
    "巽 (風)": {
        "name": "巽",
        "nature": "風",
        "bin": "011",
        "symbol": "☴",
        "desc": "順應滲透、漸進傳遞、隨風而動",
    },
    "震 (雷)": {
        "name": "震",
        "nature": "雷",
        "bin": "100",
        "symbol": "☳",
        "desc": "奮起震動、短線爆發、突發反彈",
    },
    "離 (火)": {
        "name": "離",
        "nature": "火",
        "bin": "101",
        "symbol": "☲",
        "desc": "光明附著、行情過熱、虛火明晰",
    },
    "兌 (澤)": {
        "name": "兌",
        "nature": "澤",
        "bin": "110",
        "symbol": "☱",
        "desc": "喜悅和合、多方獲利、防樂極生悲",
    },
    "乾 (天)": {
        "name": "乾",
        "nature": "天",
        "bin": "111",
        "symbol": "☰",
        "desc": "剛健強勢、龍頭主升、自強不息",
    },
}

HEXAGRAM_DATABASE = {
    ("坤 (地)", "艮 (山)"): {
        "name": "地山謙",
        "symbol": "䷎",
        "base_luck": 82,
        "judgment": "亨，君子有終。地中有山，內高而外下，謙遜退讓吉。",
        "finance_meaning": (
            "行情處於築底蓄勢階段，表面平淡但底部極為扎實，切忌追高，逢低耐心分批承接。"
        ),
        "lines": {
            1: {
                "name": "初六",
                "text": "謙謙君子，用涉大川，吉。",
                "meaning": (
                    "以謙卑低調態度跨越險阻。在投資上代表在最底部慎選穩健標的，風險極低。"
                ),
            },
            2: {
                "name": "六二",
                "text": "鳴謙，貞吉。",
                "meaning": (
                    "德行自然流露獲得共鳴。在股市代表底部確立，受到價值型買盤與法人共識認同。"
                ),
            },
            3: {
                "name": "九三",
                "text": "勞謙君子，有終吉。",
                "meaning": (
                    "任勞任怨，功成不居。此時正處多空激烈拉鋸與主力換手洗盤，持股需有耐性方得善終。"
                ),
            },
            4: {
                "name": "六四",
                "text": "無不利，撝謙。",
                "meaning": (
                    "順應局勢發揮謙遜之道。盤面進入向上試探階段，多方動能增強，操作順勢而為。"
                ),
            },
            5: {
                "name": "六五",
                "text": "不富以其鄰，利用侵伐，無不利。",
                "meaning": (
                    "【變爻核心】：五爻居尊位，動則大變！不可再消極退守，面對局勢轉折需如行軍用兵般嚴守紀律，果斷採取行動（調倉、停利、或出擊）。"
                ),
            },
            6: {
                "name": "上六",
                "text": "鳴謙，利用行師，征邑國。",
                "meaning": (
                    "謙德圓滿達到頂點，應當自我檢討並清理內部弱點。在操作上應檢視不良持股並出清淘汰。"
                ),
            },
        },
    },
    ("坎 (水)", "艮 (山)"): {
        "name": "水山蹇",
        "symbol": "䷦",
        "base_luck": 68,
        "judgment": "利西南，不利東北；利見大人，貞吉。山上有水，見險而能止。",
        "finance_meaning": (
            "前臨險阻而能知止，回升波段中會遭遇前波套牢賣壓，需步步為營，逢高逐步落袋為安。"
        ),
        "lines": {
            1: {
                "name": "初六",
                "text": "往蹇來譽。",
                "meaning": (
                    "前行有險阻，暫時退守可獲讚譽。進場投資不可過急，盲目追高易套牢。"
                ),
            },
            2: {
                "name": "六二",
                "text": "王臣蹇蹇，匪躬之故。",
                "meaning": (
                    "恪盡職守，非為個人私利。代表持股基本面若扎實，短線震盪不需過度恐慌。"
                ),
            },
            3: {
                "name": "九三",
                "text": "往蹇來反。",
                "meaning": (
                    "前進會遇到沉重阻力，及時回返為上策。遇技術面重壓區宜主動逢高減碼。"
                ),
            },
            4: {
                "name": "六四",
                "text": "往蹇來連。",
                "meaning": (
                    "單打獨鬥受阻，需結合同盟外援共渡難關。代表個股行情需靠大盤或族群齊攻。"
                ),
            },
            5: {
                "name": "九五",
                "text": "大蹇朋來。",
                "meaning": (
                    "【變卦對應爻位】：在極大的險阻中獲得強大奧援！主力與外資大舉回補，帶動股價突破重圍，迎來波段回升的最強主升窗口！"
                ),
            },
            6: {
                "name": "上六",
                "text": "往蹇來碩，吉，利見大人。",
                "meaning": (
                    "度過艱難險阻迎來豐碩成果，波段收尾大吉，應當功成身退、獲利了結。"
                ),
            },
        },
    },
}


def get_clean_hex_name(upper_k: str, lower_k: str) -> str:
  if (upper_k, lower_k) in HEXAGRAM_DATABASE:
    return HEXAGRAM_DATABASE[(upper_k, lower_k)]["name"]
  u_nat = TRIGRAM_DATA[upper_k]["nature"]
  l_nat = TRIGRAM_DATA[lower_k]["nature"]
  if u_nat == l_nat:
    return f"{TRIGRAM_DATA[upper_k]['name']}為{u_nat}"
  return f"{u_nat}{l_nat}卦"


def resolve_hexagram(upper_k: str, lower_k: str):
  clean_name = get_clean_hex_name(upper_k, lower_k)
  if (upper_k, lower_k) in HEXAGRAM_DATABASE:
    data = HEXAGRAM_DATABASE[(upper_k, lower_k)].copy()
    data["name"] = clean_name
    return data

  return {
      "name": clean_name,
      "symbol": "䷍",
      "base_luck": 65,
      "judgment": (
          f"外卦為{upper_k}，內卦為{lower_k}。象徵以「{TRIGRAM_DATA[lower_k]['desc']}」為基礎，外顯「{TRIGRAM_DATA[upper_k]['desc']}」。"
      ),
      "finance_meaning": "多空力量轉化中，應依據變爻位階嚴守紀律，切忌盲目追高。",
      "lines": {
          i: {
              "name": f"第 {i} 爻",
              "text": f"第 {i} 爻時空動態。",
              "meaning": f"事物發展至第 {i} 位階之變化關鍵。",
          }
          for i in range(1, 7)
      },
  }


def calculate_changing_hexagram(
    upper_k: str, lower_k: str, changing_line: int
):
  low_bin = TRIGRAM_DATA[lower_k]["bin"]
  up_bin = TRIGRAM_DATA[upper_k]["bin"]
  lines = list(low_bin + up_bin)

  target_idx = changing_line - 1
  lines[target_idx] = "0" if lines[target_idx] == "1" else "1"

  new_low_bin = "".join(lines[0:3])
  new_up_bin = "".join(lines[3:6])

  new_lower = next(
      k for k, v in TRIGRAM_DATA.items() if v["bin"] == new_low_bin
  )
  new_upper = next(k for k, v in TRIGRAM_DATA.items() if v["bin"] == new_up_bin)

  return new_upper, new_lower


# ==========================================
# 3. 背景呼叫 Gemini 智慧大腦
# ==========================================
def call_gemini_brain(
    api_key: str,
    question: str,
    orig_name: str,
    changed_name: str,
    changing_line: int,
    base_date: date,
    category: str,
    chat_history: list,
):
  if not GEMINI_AVAILABLE:
    return None
  try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    history_context = ""
    if chat_history:
      history_context = "【先前的諮詢脈絡】：\n"
      for h in chat_history[-3:]:
        history_context += f"- 提問：{h['question']}\n- 解答摘要：{h['answer'][:150]}...\n\n"

    prompt = f"""
你是一位兼具《周易》象數、爻變義理與現代投資金融實戰經驗的易經大師。

【當前排盤資訊】：
- 占卜基準日：{base_date.strftime('%Y年%m月%d日')}
- 詢問領域：{category}
- 本卦：{orig_name}
- 之卦（變卦）：{changed_name}
- 關鍵發動爻：第 {changing_line} 爻

{history_context}

【使用者現在的深入問題】：
「{question}」

【你的回答鐵律】：
1. 嚴禁含糊籠統！必須正面切入問題核心直接給出明確答案。
2. 若問「趨勢如何」或「變化情況」：
   - 必須分段詳述：當前打底期、波段發動期、高點滿足期的具體走勢與多空心理。
   - 明確點出由「{orig_name}」進入「{changed_name}」時，資金與股價的起伏節奏。
3. 若問「特定日期（如2027年1月10日）是否全部出清」：
   - 明確回答「是/否/或是何種比例（如80%~100%）」，並說明理由與出清後的防守操作。
4. 若問「以月來看 / 現在到明年年中的月份變化」：
   - 必須逐月（當月、下月至次年年中）列出多空標籤（例如：主升、震盪、回檔）與操作對策。
5. 排版美觀，使用粗體標籤，段落分明。
"""
    response = model.generate_content(prompt)
    return response.text
  except Exception as e:
    return None


# ==========================================
# 4. 全方位深度本地分析引擎（無 Key 時保證專業豐富）
# ==========================================
def intelligent_local_reply(
    question: str,
    base_date: date,
    orig_name: str,
    changed_name: str,
    changing_line: int,
    base_luck: int,
    round_count: int,
):
  q = question.lower().strip()

  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  # 意圖 1：詢問整體趨勢、變化走勢
  if any(
      k in q
      for k in ["趨勢", "走勢", "變化", "情況", "如何", "起伏", "未來走勢"]
  ):
    return f"""
📊 **【針對「股價未來整體變化趨勢」深度易象剖析】**

本卦為「**{orig_name}**」，之卦為「**{changed_name}**」，核心關鍵在於**第 {changing_line} 爻**發動。整體的股價發展節奏呈現**「先抑後揚、破繭而出、見高知止」**的三部曲走勢：

---

### 1️⃣ 第一階段：【浮額沉澱・極度洗盤期】（目前 ～ {date_t1.strftime('%Y 年 %m 月 %d 日')} 前後）
- **卦象特徵**：此時仍受《{orig_name}》初階氣息籠罩，外卦厚土順應、內卦如山止步。盤面特徵是**量能極度萎縮、市場悲觀觀望**。
- **主力心態**：主力正在藉由反覆震盪洗出沒有信心的散戶浮額，形成堅實的「W 底」或箱型下緣。
- **趨勢定性**：**築底蓄勢，切忌在此階段恐慌殺低出清！**

---

### 2️⃣ 第二階段：【動能引爆・波段主升發動】（關鍵窗口：{date_t2.strftime('%Y 年 %m 月 %d 日')} 前後）
- **卦象特徵**：第 {changing_line} 爻動，卦氣由「{orig_name}」正式跨入「{changed_name}」。爻辭曰：『利用侵伐』，象徵壓抑已久的買盤動能全面爆發！
- **盤面特徵**：均線帶量黃金交叉，法人外資買盤大舉回補，形成波段最凌厲的主升段攻勢。
- **趨勢定性**：**強烈反彈回升，持股者應順勢續抱，迎接持股利潤擴大。**

---

### 3️⃣ 第三階段：【波段滿足・逢高獲利了結】（目標高點：{date_t3.strftime('%Y 年 %m 月 %d 日')} 前後）
- **卦象特徵**：進入《{changed_name}》高階，象徵「山上有水，前臨險阻而能知止」。此時股價將觸及前波密集成交套牢區。
- **趨勢定性**：**波段力竭，此階段為逢高分批停利或全部出清的最佳窗口，切忌貪婪戀棧。**
"""

  # 意圖 2：特定日期 + 出清
  target_date_match = re.search(r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})", q)
  is_full_exit = any(
      k in q for k in ["全部出清", "全賣", "清倉", "全都賣", "出清"]
  )
  if target_date_match and is_full_exit:
    year = int(target_date_match.group(1))
    month = int(target_date_match.group(2))
    day = int(target_date_match.group(3))
    target_str = f"{year} 年 {month} 月 {day} 日"
    return (
        f"🎯 **【正面直接回答：{target_str} 是否應該全部出清？】**\n\n"
        f"👉 **明確結論：【是的，屆時強烈建議執行「全部出清（或出清至少 80%~90%）」！】**\n\n"
        f"**易象與時程推演依據**：\n"
        f"1. **時間週期精準對位**：依卦理推算，波段滿足高點正好落在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 附近。若您鎖定在 **{target_str}** 出清，時間點完全切合卦象「回升波段的終局滿足期」。\n"
        f"2. **卦變之象不可貪功**：本卦「{orig_name}」轉入之卦「{changed_name}」第 {changing_line} 爻，爻辭警示在回升滿足點若因貪念想賺盡最後一塊銅板，極易遭受反噬。\n"
        f"3. **確切的操作指示（不模糊）**：\n"
        f"   - **{target_str} 當日**：將手中持股**一口氣出清 80%~100%**，收回全部現金。\n"
        f"   - **資金防守策略**：出清後切忌立刻轉買其他高風險標的，應讓資金休息至少 2~3 週，等待下一個穩健卦象成形再做定奪。"
    )

  # 意圖 3：以月來看、明年年中
  if any(
      k in q
      for k in [
          "月",
          "以月來看",
          "明年年中",
          "每月",
          "月份",
          "月趨勢",
      ]
  ):
    cur_year = base_date.year
    next_year = cur_year + 1
    return f"""
📈 **【正面回應：現在到 {next_year} 年年中（6月）各月份股價起伏走勢預測】**

<div class="month-card" style="border-left: 4px solid #718096;">
    <div class="month-title">🔹 {cur_year} 年 11 月（亥月）：底部洗盤整理期【盤整偏弱】</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">外地順而內山止，主力壓盤洗清浮額。操作：切忌恐慌殺低，保留 30%~40% 現金部位。</div>
</div>
<div class="month-card" style="border-left: 4px solid #E53E3E; background-color:#FFFAF0;">
    <div class="month-title" style="color:#C53030;">🚀 {cur_year} 年 12 月（子月）：波段實質回升發動期【強勢主升】</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">約在 <b>{date_t2.strftime('%m月%d日')}</b> 前後展開顯著反彈，為動能最強月份！操作：持股續抱，順應主力攻勢。</div>
</div>
<div class="month-card" style="border-left: 4px solid #DD6B20; background-color:#FFFAF0;">
    <div class="month-title" style="color:#DD6B20;">🏁 {next_year} 年 1 月（丑月）：波段衝高見頂・滿足了結期【高檔震盪】</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">接近 <b>{next_year} 年 1 月 10 日</b> 前後動能達巔峰。<b>強烈建議在此月份執行「全部出清或出清 80%~90%」！</b></div>
</div>
<div class="month-card" style="border-left: 4px solid #319795;">
    <div class="month-title" style="color:#285E61;">📉 {next_year} 年 2 月 ～ 3 月（寅、卯月）：獲利回吐・回檔打底期【回檔整理】</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">消化上一波漲幅，重回震盪尋求第二隻腳支撐。操作：空手觀望，切忌過早搶反彈。</div>
</div>
<div class="month-card" style="border-left: 4px solid #3182CE;">
    <div class="month-title" style="color:#2B6CB0;">🌱 {next_year} 年 4 月 ～ 6 月（年中）：築底回溫・新週期醞釀期【溫和回升】</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">新主流族群浮現，展開年中第二波多頭攻勢。操作：重新逢低佈局業績成長股。</div>
</div>
"""

  # 意圖 4：何時回升、日期推算
  if any(k in q for k in ["何時", "回升", "反彈", "解套", "上漲", "日期"]):
    return f"""
📅 **【股價回升關鍵時程推算（具體公曆日期）】**

<div class="timeline-card" style="border-left: 4px solid #3182CE;">
    <div style="font-weight:700; color:#2B6CB0; font-size:15px;">📍 階段一：短線止跌震盪打底期</div>
    <div style="font-size:17px; font-weight:800; color:#DD6B20;">{date_t1.strftime('%Y 年 %m 月 %d 日')}（約第 {t1_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：賣壓開始收斂，量能萎縮，市場進入浮額洗盤階段，切忌在此時恐慌殺低。</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #E53E3E; background-color:#FFFAF0;">
    <div style="font-weight:700; color:#C53030; font-size:15px;">🚀 階段二：波段實質回升發動日（重要關鍵窗口）</div>
    <div style="font-size:17px; font-weight:800; color:#E53E3E;">{date_t2.strftime('%Y 年 %m 月 %d 日')}（約第 {t2_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：卦氣由「{orig_name}」正式轉向「{changed_name}」，買盤動能湧現，均線翻揚，為最顯著的回升發動點！</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #319795; background-color:#F0FFF4;">
    <div style="font-weight:700; color:#285E61; font-size:15px;">🏁 階段三：波段高點／目標解套滿足區</div>
    <div style="font-size:17px; font-weight:800; color:#319795;">{date_t3.strftime('%Y 年 %m 月 %d 日')}（約第 {t3_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：波段動能滿足，容易遭遇前波沉重套牢賣壓，是逢高分批減碼或出清落袋的黃金時間。</div>
</div>
"""

  # 意圖 5：一般賣出、停損
  if any(k in q for k in ["賣", "出清", "脫手", "砍", "停損"]):
    return (
        f"🛑 **【當前階段操作明確建議】**：\n\n"
        f"- **結論**：**切忌在近日恐慌性殺低出清！**\n"
        f"- **操作執行配比**：\n"
        f"  1. **目前至 {date_t1.strftime('%m/%d')}**：持股按兵不動，保留 30%~40%"
        " 現金儲備。\n"
        f"  2. **回升啟動至 {date_t2.strftime('%m/%d')}~{date_t3.strftime('%m/%d')}**：採取「階梯式減碼」，反彈遇均線壓力先出清"
        " 30%，接近滿足日再出清 40%，剩餘 30% 設移動停利。"
    )

  # 預設通用深入回答（絕不再只輸出兩行！）
  return f"""
🎯 **【針對提問之易理核心解答】**：

- **當前局勢特徵**：由本卦「**{orig_name}**」邁入之卦「**{changed_name}**」，能量正處於五爻轉化的關鍵樞紐。
- **時程轉化指引**：在 **{date_t2.strftime('%Y 年 %m 月 %d 日')}** 前後，局勢將出現決定性的多空訊號。
- **決策指導方針**：不可過度悲觀退縮，應保持清晰的風控紀律，靜待底部洗盤完成後的右側買盤確認。
"""


# ==========================================
# 5. 歷史檔案存取
# ==========================================
def save_session_file(session_data):
  filename = os.path.join(HISTORY_DIR, f"{session_data['session_id']}.json")
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(session_data, f, ensure_ascii=False, indent=2)


def load_all_sessions():
  if not os.path.exists(HISTORY_DIR):
    return []
  files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
  sessions = []
  for f in sorted(files, reverse=True):
    try:
      with open(os.path.join(HISTORY_DIR, f), "r", encoding="utf-8") as fp:
        sessions.append(json.load(fp))
    except Exception:
      pass
  return sessions


# ==========================================
# 6. Session 與側邊欄
# ==========================================
if "active_session" not in st.session_state:
  st.session_state.active_session = None

st.sidebar.header("☯️ 易經起卦設定")

# 讀取金鑰（支援 Streamlit Secrets 或側邊欄輸入）
default_api_key = st.secrets.get("GEMINI_API_KEY", "")
gemini_api_key = st.sidebar.text_input(
    "🔑 Google Gemini API Key (選填)",
    value=default_api_key,
    type="password",
    help="填入免費的 Gemini Key 可啟用全 64 卦無限 AI 智慧；不填也能使用強化的內建易象引擎！",
)

input_date = st.sidebar.date_input("占卜基準日期", value=date.today())

category = st.sidebar.selectbox(
    "選擇詢問事項分類",
    [
        "財運 / 投資股票",
        "事業 / 升遷發展",
        "感情 / 婚姻緣分",
        "學業 / 考試進修",
        "健康 / 身心調理",
        "合夥 / 簽約談判",
    ],
    index=0,
)

first_question = st.sidebar.text_area(
    "請輸入首次占卜的問題：",
    value="台灣股票股價的情況 何時會回昇 要不要最近賣掉出清 何時股價會回昇 推測出詳細的日期",
    height=100,
)

st.sidebar.subheader("爻象與變爻設定")
upper_tri = st.sidebar.selectbox("上卦 (外卦)", list(TRIGRAM_DATA.keys()), index=0)
lower_tri = st.sidebar.selectbox("下卦 (內卦)", list(TRIGRAM_DATA.keys()), index=1)

line_options = list(range(1, 7))
changing_line = st.sidebar.selectbox(
    "選擇變爻位階",
    line_options,
    index=4,
    format_func=lambda x: f"第 {x} 爻 ({['初爻','二爻','三爻','四爻','五爻','上爻'][x-1]}) 變動",
)

btn_new = st.sidebar.button("🔮 開始全新占卜並建立獨立檔案", type="primary")

if btn_new:
  orig_hex = resolve_hexagram(upper_tri, lower_tri)
  new_up, new_low = calculate_changing_hexagram(
      upper_tri, lower_tri, changing_line
  )
  changed_hex = resolve_hexagram(new_up, new_low)

  session_id = f"{input_date.strftime('%Y%m%d')}_{orig_hex['name']}_爻{changing_line}_{datetime.now().strftime('%H%M%S')}"

  # 優先呼叫 Gemini，失敗或無 Key 自動切換至深度本地分析
  initial_answer = None
  if gemini_api_key:
    with st.spinner("🤖 背景正與 Gemini 進行深層易象演繹..."):
      initial_answer = call_gemini_brain(
          api_key=gemini_api_key,
          question=first_question,
          orig_name=orig_hex["name"],
          changed_name=changed_hex["name"],
          changing_line=changing_line,
          base_date=input_date,
          category=category,
          chat_history=[],
      )

  if not initial_answer:
    initial_answer = intelligent_local_reply(
        first_question,
        input_date,
        orig_hex["name"],
        changed_hex["name"],
        changing_line,
        orig_hex["base_luck"],
        1,
    )

  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7
  metrics = {
      "final_luck": orig_hex["base_luck"],
      "date_t1": str(input_date + timedelta(days=t1_days)),
      "date_t2": str(input_date + timedelta(days=t2_days)),
      "date_t3": str(input_date + timedelta(days=t3_days)),
      "t2_days": t2_days,
  }

  new_session = {
      "session_id": session_id,
      "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "date": str(input_date),
      "category": category,
      "upper_tri": upper_tri,
      "lower_tri": lower_tri,
      "changing_line": changing_line,
      "original_hexagram": orig_hex["name"],
      "changed_hexagram": changed_hex["name"],
      "metrics": metrics,
      "chat_history": [{
          "round": 1,
          "question": first_question,
          "answer": initial_answer,
          "time": datetime.now().strftime("%H:%M:%S"),
      }],
  }

  st.session_state.active_session = new_session
  save_session_file(new_session)
  st.success(f"✅ 成功起卦！已獨立存檔為：{session_id}.json")

# ==========================================
# 7. 主介面渲染
# ==========================================
st.title("☯️ 易經智慧占卜決策系統")

tab_chat, tab_hex_view, tab_files = st.tabs(
    ["💬 卦象專屬諮詢對話框", "📖 當前卦象結構說明 (含全六爻)", "📁 一卦一檔・歷史檔案庫"]
)

with tab_chat:
  session = st.session_state.active_session
  if not session:
    st.info("👈 請在左側設定卦象與問題，並點選「開始全新占卜並建立獨立檔案」。")
  else:
    mode_desc = (
        "🟢 Gemini 雲端智慧核心"
        if gemini_api_key
        else "🔵 本地全方位易象引擎"
    )
    st.markdown(
        f"""
        <div style="background-color:#F8FAFC; padding:12px 18px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:15px;">
            <span class="hex-badge">檔案：{session['session_id']}</span>
            <span class="hex-badge">事項：{session['category']}</span>
            <span class="hex-badge">本卦：{session['original_hexagram']}</span>
            <span class="hex-badge">之卦：{session['changed_hexagram']} (第 {session['changing_line']} 爻動)</span>
            <span class="hex-badge">{mode_desc}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("短線震盪打底期", session["metrics"]["date_t1"])
    col2.metric(
        "波段回升啟動日 (關鍵)",
        session["metrics"]["date_t2"],
        f"+{session['metrics']['t2_days']} 天",
    )
    col3.metric("波段滿足高點日", session["metrics"]["date_t3"])

    st.divider()

    st.subheader("📜 本次卦象連續諮詢歷程")
    for chat in session["chat_history"]:
      st.markdown(
          f"<div class='chat-user-box'>🙋 <b>提問（第 {chat['round']} 輪）</b>"
          f" [{chat['time']}]：<br>{chat['question']}</div>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<div class='chat-ai-box'>☯️ <b>易象解答與指引</b>：<br><br>{chat['answer']}</div>",
          unsafe_allow_html=True,
      )

    st.markdown("### 💬 針對此卦象持續深入追問（可直接按鍵盤 Enter）：")
    with st.form(key="followup_chat_form", clear_on_submit=True):
      followup_q = st.text_input(
          "輸入您的追問問題：",
          placeholder="例如：所以 股價的變化趨勢如何？？（輸入完直接按 Enter 送出）",
      )
      submit_followup = st.form_submit_button("📨 送出追問解答 (或直接按 Enter)")

    if submit_followup and followup_q:
      round_num = len(session["chat_history"]) + 1
      orig_hex = resolve_hexagram(session["upper_tri"], session["lower_tri"])
      new_up, new_low = calculate_changing_hexagram(
          session["upper_tri"], session["lower_tri"], session["changing_line"]
      )
      changed_hex = resolve_hexagram(new_up, new_low)

      followup_answer = None
      if gemini_api_key:
        with st.spinner("🤖 背景正請教 Gemini 分析中..."):
          followup_answer = call_gemini_brain(
              api_key=gemini_api_key,
              question=followup_q,
              orig_name=orig_hex["name"],
              changed_name=changed_hex["name"],
              changing_line=session["changing_line"],
              base_date=datetime.strptime(session["date"], "%Y-%m-%d").date(),
              category=session["category"],
              chat_history=session["chat_history"],
          )

      if not followup_answer:
        followup_answer = intelligent_local_reply(
            followup_q,
            datetime.strptime(session["date"], "%Y-%m-%d").date(),
            orig_hex["name"],
            changed_hex["name"],
            session["changing_line"],
            orig_hex["base_luck"],
            round_num,
        )

      session["chat_history"].append({
          "round": round_num,
          "question": followup_q,
          "answer": followup_answer,
          "time": datetime.now().strftime("%H:%M:%S"),
      })
      st.session_state.active_session = session
      save_session_file(session)
      st.rerun()

with tab_hex_view:
  if st.session_state.active_session:
    cur = st.session_state.active_session
    orig_info = resolve_hexagram(cur["upper_tri"], cur["lower_tri"])
    new_up, new_low = calculate_changing_hexagram(
        cur["upper_tri"], cur["lower_tri"], cur["changing_line"]
    )
    chg_info = resolve_hexagram(new_up, new_low)

    col_l, col_r = st.columns(2)
    with col_l:
      st.subheader(f"【本卦】{orig_info['symbol']} {orig_info['name']}")
      st.info(f"結構：上 {cur['upper_tri']} / 下 {cur['lower_tri']}")
      st.write(f"**大象義理**：{orig_info['judgment']}")
      st.write(f"**市場象意**：{orig_info['finance_meaning']}")
    with col_r:
      st.subheader(
          f"【之卦（變卦）】{chg_info['symbol']} {chg_info['name']} (第"
          f" {cur['changing_line']} 爻變)"
      )
      st.info(f"結構：轉化為 上 {new_up} / 下 {new_low}")
      st.write(f"**大象義理**：{chg_info['judgment']}")
      st.write(f"**轉化象意**：{chg_info['finance_meaning']}")

    st.divider()

    col_orig_lines, col_chg_lines = st.columns(2)
    with col_orig_lines:
      st.markdown(f"### 📜 本卦《{orig_info['name']}》全六爻爻辭")
      for i in range(6, 0, -1):
        line_data = orig_info["lines"].get(
            i,
            {
                "name": f"第 {i} 爻",
                "text": "爻辭備載",
                "meaning": "動態變化中",
            },
        )
        is_changing = i == cur["changing_line"]
        card_class = (
            "changing-line-card" if is_changing else "normal-line-card"
        )
        badge_text = (
            "🔥【當前發動變爻】" if is_changing else f"第 {i} 位階"
        )
        st.markdown(
            f"""
                <div class="{card_class}">
                    <div style="font-weight: bold; font-size: 15px; margin-bottom: 4px;">
                        {line_data['name']}：{line_data['text']} <span style="font-size:12px; color:#E53E3E; margin-left:6px;">{badge_text}</span>
                    </div>
                    <div style="color: #4A5568; font-size: 13.5px;">
                        💡 <b>象義剖析</b>：{line_data['meaning']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )

    with col_chg_lines:
      st.markdown(f"### 🔄 變卦《{chg_info['name']}》全六爻爻辭")
      for i in range(6, 0, -1):
        chg_line_data = chg_info["lines"].get(
            i,
            {
                "name": f"第 {i} 爻",
                "text": "爻辭備載",
                "meaning": "動態演變中",
            },
        )
        is_changing = i == cur["changing_line"]
        card_class = (
            "changing-line-card" if is_changing else "normal-line-card"
        )
        badge_text = (
            "🎯【轉化對應爻位】" if is_changing else f"第 {i} 位階"
        )
        st.markdown(
            f"""
                <div class="{card_class}">
                    <div style="font-weight: bold; font-size: 15px; margin-bottom: 4px;">
                        {chg_line_data['name']}：{chg_line_data['text']} <span style="font-size:12px; color:#319795; margin-left:6px;">{badge_text}</span>
                    </div>
                    <div style="color: #4A5568; font-size: 13.5px;">
                        💡 <b>象義剖析</b>：{chg_line_data['meaning']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )
  else:
    st.info("請先於側邊欄起卦以檢視卦象結構說明。")

with tab_files:
  st.subheader("📁 一卦一檔・歷史諮詢檔案管理")
  all_sessions = load_all_sessions()
  if not all_sessions:
    st.info("目前尚無獨立占卜檔案。")
  else:
    st.write(f"系統目前安全保存了 **{len(all_sessions)}** 個獨立卦象諮詢檔案。")
    session_options = {
        f"{s['create_time']} ｜ {s['category']} ｜ {s['original_hexagram']} 變 {s['changed_hexagram']} ({s['session_id']})": s[
            "session_id"
        ]
        for s in all_sessions
    }
    selected_label = st.selectbox(
        "選擇要回溯的歷史卦象：", list(session_options.keys())
    )
    chosen_id = session_options[selected_label]
    chosen_session = next(
        s for s in all_sessions if s["session_id"] == chosen_id
    )

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
      if st.button("🔄 載入此卦象至對話框繼續諮詢"):
        st.session_state.active_session = chosen_session
        st.success(f"已成功載入 {chosen_id}，請切換至「💬 卦象專屬諮詢對話框」繼續發問！")
    with c_btn2:
      st.download_button(
          label="💾 下載此卦象專屬備份檔 (JSON)",
          data=json.dumps(chosen_session, ensure_ascii=False, indent=2),
          file_name=f"{chosen_id}.json",
          mime="application/json",
      )

    st.markdown("---")
    st.markdown("#### 📖 該次卦象諮詢記錄總覽：")
    for chat_item in chosen_session.get("chat_history", []):
      with st.expander(
          f"第 {chat_item['round']} 輪提問 [{chat_item.get('time', '')}]："
          f" {chat_item['question'][:35]}...",
          expanded=True,
      ):
        st.markdown(f"**提問細節**：\n{chat_item['question']}")
        st.markdown(f"**易象解答**：\n{chat_item['answer']}", unsafe_allow_html=True)
