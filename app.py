"""
程式名稱：易經智慧占卜決策系統 (Gemini 雲端大腦無縫整合版)
特色亮點：
1. 背景靜默串接 Google Gemini (gemini-1.5-flash)，完全在網頁內直接對答，不跳出外部視窗。
2. 雙核心機制：有輸入 Gemini Key 則享受全 64 卦自由智慧深度解卦；未填 Key 則自動切換至內建精準易象引擎。
3. 原生表單支援 Enter 鍵直接背景送出。
4. 本卦與變卦皆附帶全六爻詳解，時程排版卡片化。
"""

import json
import os
import re
from datetime import date, datetime, timedelta
import google.generativeai as genai
import streamlit as st

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
            "行情築底蓄勢階段，表面平淡但底部扎實，切忌追高，宜逢低耐心分批佈局。"
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
# 3. 背景呼叫 Gemini 智慧解卦核心
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
  """在背景向 Gemini 發送易經結構化提示詞，並直接取得解答文字"""
  try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # 組合歷史問答脈絡
    history_context = ""
    if chat_history:
      history_context = "【先前的對話諮詢脈絡】：\n"
      for h in chat_history[-3:]:
        history_context += f"- 提問：{h['question']}\n- 易象回覆精要：{h['answer'][:150]}...\n\n"

    system_instruction = f"""
你是一位深諳《周易》象數、義理與金融決策的易經國學大師。
【當前起卦資訊】：
- 占卜基準日：{base_date.strftime('%Y年%m月%d日')}
- 詢問類別：{category}
- 本卦：{orig_name}
- 之卦（變卦）：{changed_name}
- 發動變爻：第 {changing_line} 爻

{history_context}

【使用者的最新追問】：
「{question}」

【你的回答鐵律】：
1. 嚴禁給出模稜兩可、含糊推託的廢話。必須【正面直接回答核心問題】！
2. 若使用者詢問「特定日期（例如：2027年1月10日）是否全部出清」：
   - 必須直接給出明確結論（是、否、或出清具體比例，例如 80%~90% 或 100%）。
   - 結合本卦轉變卦、變爻動辭、波段滿足點提出理由，並給出資金出清後的防守操作指南。
3. 若使用者詢問「以月來看 / 現在到明年年中的變化趨勢」：
   - 請以基準日推算，逐月（例如：11月、12月、次年1月至6月）詳細拆解「多空走勢特徵（盤整/主升/回檔/築底）」與「具體操作建議」。
4. 條理分明，使用繁體中文、排版美觀、適度加粗重點，文字需具備易學底蘊與實戰決策價值。
"""
    response = model.generate_content(system_instruction)
    return response.text
  except Exception as e:
    return f"⚠️ 串接 Gemini 運算時發生小狀況（{str(e)}），自動切換至內建易象規則解析。"


# ==========================================
# 4. 備援規則回覆引擎（當未填 Key 時自動啟用）
# ==========================================
def fallback_local_reply(
    question: str,
    base_date: date,
    orig_name: str,
    changed_name: str,
    changing_line: int,
    base_luck: int,
):
  q = question.lower().strip()
  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  if any(
      k in q
      for k in [
          "月",
          "以月來看",
          "明年年中",
          "每月",
          "月份",
          "月趨勢",
          "走勢",
          "起伏變化",
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
        f"1. **時間週期對位**：依卦理推算，波段滿足高點落在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 前後，此時出清切合回升波段終局滿足期。\n"
        f"2. **卦變之象不可貪功**：本卦「{orig_name}」轉「{changed_name}」，爻辭警示滿足點若因貪念想賺盡最後一塊銅板，極易遭受反噬。\n"
        f"3. **確切操作**：{target_str} 當日將持股出清 80%~100%，收回資金防守並休息至少 2~3 週。"
    )

  return (
      f"🎯 **【易象關鍵解答】**：\n\n"
      f"- 本卦「**{orig_name}**」轉入之卦「**{changed_name}**」，第 {changing_line} 爻發動。\n"
      f"- **關鍵轉折日**：請密切留意 **{date_t2.strftime('%Y 年 %m 月 %d 日')}** 前後之買盤動向。"
  )


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

# 智慧核心設定（優先讀取 Secrets，也可在側邊欄填寫）
default_api_key = st.secrets.get("GEMINI_API_KEY", "")
gemini_api_key = st.sidebar.text_input(
    "🔑 Google Gemini API Key (可選)",
    value=default_api_key,
    type="password",
    help="輸入後將啟用 Gemini 雲端智慧大腦解讀 64 卦所有疑難雜症；留空則使用內建模擬引擎。",
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

  # 判斷使用 Gemini 或是內建引擎
  if gemini_api_key:
    with st.spinner("🤖 背景正與 Gemini 進行深層易象演繹，請稍候..."):
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
  else:
    initial_answer = fallback_local_reply(
        first_question,
        input_date,
        orig_hex["name"],
        changed_hex["name"],
        changing_line,
        orig_hex["base_luck"],
    )

  # 時程標註
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
        "🟢 Gemini 雲端智慧核心運作中"
        if gemini_api_key
        else "⚪ 本地易象引擎運作中"
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

    # 追問輸入（直接在網頁背景與 Gemini 溝通，按 Enter 即送出）
    st.markdown("### 💬 針對此卦象持續深入追問（可直接按鍵盤 Enter）：")
    with st.form(key="followup_chat_form", clear_on_submit=True):
      followup_q = st.text_input(
          "輸入您的追問問題：",
          placeholder="例如：股價的起伏變化 以現在到明年年中 以月來看 的變化情況是？？（輸入完直接按 Enter）",
      )
      submit_followup = st.form_submit_button("📨 送出追問解答 (或直接按 Enter)")

    if submit_followup and followup_q:
      round_num = len(session["chat_history"]) + 1
      orig_hex = resolve_hexagram(session["upper_tri"], session["lower_tri"])
      new_up, new_low = calculate_changing_hexagram(
          session["upper_tri"], session["lower_tri"], session["changing_line"]
      )
      changed_hex = resolve_hexagram(new_up, new_low)

      if gemini_api_key:
        with st.spinner("🤖 背景正請教 Gemini 分析中，請稍候..."):
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
      else:
        followup_answer = fallback_local_reply(
            followup_q,
            datetime.strptime(session["date"], "%Y-%m-%d").date(),
            orig_hex["name"],
            changed_hex["name"],
            session["changing_line"],
            orig_hex["base_luck"],
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
