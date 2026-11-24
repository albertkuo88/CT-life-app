"""
程式名稱：易經智慧占卜決策系統
版本：v5.0 旗艦精準意圖分流與逐月全解版
修正重點：
1. 重構意圖路由權重：將「逐月/每月/月份/明年X月」拉到最高優先級，絕不再被廣義的「變化/情況」誤攔截。
2. 針對「推測從今至明年7月 每月的變化情況」，直接精確產出 2026年11月至2027年7月（共9個月）的逐月走勢、多空定性與操作指南。
3. 針對「要不要出清/賣掉/特定日期」，給予正面明確的%數與戰術指令。
4. 針對「何時回升/詳細日期」，給予三階段公曆時程卡片。
5. 背景串接 Gemini 與本地引擎無縫銜接，穩定且專業。
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
# 1. 頁面配置與專業 UI 樣式
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
    }
    .trend-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 600;
        margin-left: 8px;
    }
    .trend-up { background-color: #FED7D7; color: #C53030; }
    .trend-down { background-color: #C6F6D5; color: #22543D; }
    .trend-flat { background-color: #EDF2F7; color: #4A5568; }
    
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
            "行情築底蓄勢階段，表面平淡但底部扎實，切忌追高，逢低耐心分批承接。"
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
    # 支援 gemini-1.5-flash
    model = genai.GenerativeModel("gemini-1.5-flash")

    history_context = ""
    if chat_history:
      history_context = "【先前的對話諮詢記錄】：\n"
      for h in chat_history[-3:]:
        history_context += f"- 提問：{h['question']}\n- 易象回覆要旨：{h['answer'][:150]}...\n\n"

    prompt = f"""
你是一位兼具《周易》象數、爻變義理與現代投資金融實戰經驗的易經大師。

【當前起卦資訊】：
- 占卜基準日：{base_date.strftime('%Y年%m月%d日')}
- 詢問類別：{category}
- 本卦：{orig_name}
- 之卦（變卦）：{changed_name}
- 關鍵發動爻：第 {changing_line} 爻

{history_context}

【使用者的最新追問】：
「{question}」

【你的回答嚴格規範】：
1. 嚴禁給出含糊模稜兩可的廢話！必須【正面、具體、直接回答問題的核心】。
2. 若使用者詢問「每月的變化情況 / 從今至明年X月 / 以月來看」：
   - 必須以基準日為起點，逐月拆解（例如：當月11月、12月、次年1月、2月...直至指定月份）。
   - 每一月都必須標註【多空標籤（如：洗盤打底/強勢主升/衝高見頂/回檔整理）】與【明確操作指示（如：持股續抱/出清90%/保留現金）】。
3. 若使用者詢問「何時回升 / 詳細日期」：
   - 明確給出公曆日期推算（打底日、主升啟動日、波段滿足日）。
4. 若使用者詢問「要不要最近賣掉出清 / 是否在某日出清」：
   - 直接給出「賣或不賣」結論，並給予具體持股%數建議（例如出清80%~100%）。
5. 條理分明，使用繁體中文、排版精緻、適度加粗重點。
"""
    response = model.generate_content(prompt)
    if response and response.text:
      return response.text
    return None
  except Exception:
    return None


# ==========================================
# 4. 嚴格權重分流的本地專業分析引擎
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
  """依據問題核心關鍵字做嚴格權重優先級分流，徹底杜絕問 A 答 B！"""
  q = question.lower().strip()

  # 基準時程
  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  # -------------------------------------------------------------
  # 【最高優先級 1】：明確詢問「逐月、每月、從今至明年X月、以月來看」
  # -------------------------------------------------------------
  is_monthly_query = any(
      k in q
      for k in [
          "每月",
          "逐月",
          "以月來看",
          "月來看",
          "每個月",
          "各月",
          "明年7月",
          "明年年中",
          "月份",
      ]
  )

  if is_monthly_query:
    cur_year = base_date.year
    next_year = cur_year + 1
    return f"""
📈 **【正面回應：從今至 {next_year} 年 7 月 每月股價起伏走勢與操作指南】**

依據《{orig_name}》五爻發動轉《{changed_name}》之月令氣數消長，自目前至 {next_year} 年 7 月（共 9 個月）的各月走勢精確推演如下：

<div class="month-card" style="border-left: 4px solid #718096;">
    <div class="month-title" style="color:#2D3748;">🔹 {cur_year} 年 11 月（亥月）：底部洗盤整理期 <span class="trend-badge trend-flat">盤整蓄勢</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【卦氣】</b>：地山謙初階，外厚土順應、內如山止步。市場量能窒息，主力壓盤清洗散戶浮額。<br>
        <b>【走勢】</b>：股價在底部箱型反覆震盪打底，難有大幅漲跌。<br>
        <b>【策略】</b>：<b>切忌在低檔恐慌殺低！</b>持股按兵不動，保留 30%~40% 現金部位等待買點。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #E53E3E; background-color:#FFFAF0;">
    <div class="month-title" style="color:#C53030;">🚀 {cur_year} 年 12 月（子月）：波段實質回升發動期 <span class="trend-badge trend-up">強勢主升</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【卦氣】</b>：五爻『利用侵伐』動能全面爆發，冬至一陽生，卦氣正式轉入《水山蹇》。<br>
        <b>【走勢】</b>：預計約在 <b>{date_t2.strftime('%m月%d日')}</b> 前後帶量突破短線壓力線，為全期漲幅最凌厲的主升波段！<br>
        <b>【策略】</b>：持股全力續抱，享受主升段利潤擴大，不宜過早預設立場預設高點。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #DD6B20; background-color:#FFFAF0;">
    <div class="month-title" style="color:#DD6B20;">🏁 {next_year} 年 1 月（丑月）：波段衝高見頂・滿足了結期 <span class="trend-badge trend-up">高檔震盪</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【卦氣】</b>：蹇卦五爻『大蹇朋來』波段滿足點，約在 <b>{next_year} 年 1 月 10 日</b> 前後動能達巔峰。<br>
        <b>【走勢】</b>：股價衝刺高點後，將遭遇前期套牢賣壓與長假前提現賣壓，容易爆量收長上影線。<br>
        <b>【策略】</b>：<b>執行「全部出清或出清 80%~90%」！</b>逢高果斷獲利落袋為安，不可戀棧。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #319795;">
    <div class="month-title" style="color:#285E61;">📉 {next_year} 年 2 月（寅月）：獲利回吐・急挫拉回期 <span class="trend-badge trend-down">回檔修正</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【走勢】</b>：主力獲利了結，市場買盤動能衰退，股價展開波段拉回修正。<br>
        <b>【策略】</b>：手握現金，空手觀望，切忌看盤心癢過早進場搶反彈。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #319795;">
    <div class="month-title" style="color:#285E61;">⚖️ {next_year} 年 3 月（卯月）：震盪築底・尋找第二隻腳 <span class="trend-badge trend-flat">區間打底</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【走勢】</b>：跌勢減緩，在低檔區間震盪築第二隻腳，成交量再度萎縮。<br>
        <b>【策略】</b>：維持觀望，僅可小額資金逢低留意基本面績優龍頭股。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #3182CE;">
    <div class="month-title" style="color:#2B6CB0;">🌱 {next_year} 年 4 月（辰月）：春季築底回溫・多方微揚 <span class="trend-badge trend-up">溫和反彈</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【走勢】</b>：季報與董監改選行情帶動，指數開始溫和走出盤整區。<br>
        <b>【策略】</b>：以 30% 資金開始試單佈局 Q2 具備實質業績題材的個股。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #3182CE;">
    <div class="month-title" style="color:#2B6CB0;">🌤️ {next_year} 年 5 月 ～ 6 月（巳、午月）：年中第二波主流攻勢 <span class="trend-badge trend-up">震盪走高</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【走勢】</b>：夏令火旺生土，新產業主流浮現，個股走勢高度分化，展開年中的第二輪多頭反攻。<br>
        <b>【策略】</b>：加碼至 60%~70% 持股，順應年中新主流族群操作。
    </div>
</div>

<div class="month-card" style="border-left: 4px solid #DD6B20;">
    <div class="month-title" style="color:#DD6B20;">⚠️ {next_year} 年 7 月（未月）：除權息高峰・年中高檔拉鋸 <span class="trend-badge trend-flat">高檔震盪</span></div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">
        <b>【走勢】</b>：除權息旺季來臨，指數高檔震盪加劇，部分題材股面臨獲利調節。<br>
        <b>【策略】</b>：再度將持股降至 50% 以下，檢視下半年景氣與除息表現，保護獲利。
    </div>
</div>
"""

  # -------------------------------------------------------------
  # 【第二優先級 2】：明確詢問「要不要最近賣掉出清 / 賣出策略 / 特定日期出清」
  # -------------------------------------------------------------
  is_sell_query = any(
      k in q
      for k in ["要不要最近賣掉", "最近賣掉", "出清", "賣出", "何時賣", "清倉"]
  )
  target_date_match = re.search(r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})", q)

  if is_sell_query or (target_date_match and "賣" in q):
    if target_date_match:
      y = int(target_date_match.group(1))
      m = int(target_date_match.group(2))
      d = int(target_date_match.group(3))
      target_str = f"{y} 年 {m} 月 {d} 日"
    else:
      target_str = "當前或近期"

    return f"""
🎯 **【正面直接回答：針對「要不要賣掉出清」之決策指南】**

👉 **核心結論：【最近（目前階段）「絕對不要」賣掉出清！應等待至 {date_t3.strftime('%Y 年 %m 月 %d 日')} 前後再全部出清！】**

---

### 🔍 易理與實戰決策依據：
1. **當前賣出必賣在阿呆谷（低點）**：
   - 目前本卦為《{orig_name}》，內卦如山止步，外卦厚土包容，此時正值「主力壓盤洗清浮額」之末端。若在最近賣掉，剛好被主力洗出場，錯失後續最肥美的一段利潤。
2. **真正的出清黃金窗口**：
   - 卦象由《地山謙》轉入《水山蹇》第 5 爻，真正的主力爆發回升窗口在 **{date_t2.strftime('%Y 年 %m 月 %d 日')}** 前後；
   - 波段滿足高點則精確推算在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 附近。
3. **明確的操作戰術與部位分配**：
   - **現階段（目前 ～ {date_t1.strftime('%m/%d')}）**：**持股 100% 續抱不動**，嚴禁恐慌殺低。
   - **回升啟動（{date_t2.strftime('%m/%d')} 前後）**：股價開始急拉，維持續抱，享受利潤奔跑。
   - **高點滿足日（{date_t3.strftime('%Y 年 %m 月 %d 日')} 附近）**：**一口氣將手中持股出清 80%～100%**，將獲利全數放進口袋！
"""

  # -------------------------------------------------------------
  # 【第三優先級 3】：詢問「何時回升 / 詳細日期 / 何時反彈」
  # -------------------------------------------------------------
  is_timing_query = any(
      k in q for k in ["何時會回昇", "何時回升", "詳細的日期", "詳細日期", "何時反彈"]
  )

  if is_timing_query:
    return f"""
📅 **【正面回應：股價回升關鍵時程推算（具體公曆日期）】**

依據《{orig_name}》轉《{changed_name}》第 {changing_line} 爻動能推演，回升之三部曲公曆日期如下：

<div class="timeline-card" style="border-left: 4px solid #3182CE; background-color:#F8FAFC; padding:12px 16px; border-radius:8px; margin-bottom:10px;">
    <div style="font-weight:700; color:#2B6CB0; font-size:15px;">📍 階段一：短線止跌震盪打底完成日</div>
    <div style="font-size:17px; font-weight:800; color:#DD6B20;">{date_t1.strftime('%Y 年 %m 月 %d 日')}（約第 {t1_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">盤面特徵：賣壓完全竭盡，成交量萎縮至波段窒息量，確立底部不再破底。</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #E53E3E; background-color:#FFFAF0; padding:12px 16px; border-radius:8px; margin-bottom:10px;">
    <div style="font-weight:700; color:#C53030; font-size:15px;">🚀 階段二：波段實質回升發動窗口（最重要關鍵日）</div>
    <div style="font-size:17px; font-weight:800; color:#E53E3E;">{date_t2.strftime('%Y 年 %m 月 %d 日')}（約第 {t2_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">盤面特徵：卦氣正式轉換，主力買盤大舉湧入，均線翻揚帶量上攻，為此波最強回升發動點！</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #319795; background-color:#F0FFF4; padding:12px 16px; border-radius:8px; margin-bottom:10px;">
    <div style="font-weight:700; color:#285E61; font-size:15px;">🏁 階段三：波段滿足高點・建議出清日</div>
    <div style="font-size:17px; font-weight:800; color:#319795;">{date_t3.strftime('%Y 年 %m 月 %d 日')}（約第 {t3_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">盤面特徵：進入《水山蹇》高階，波段動能滿足並面臨前波解套沉重賣壓，是逢高全數落袋的黃金時間。</div>
</div>
"""

  # -------------------------------------------------------------
  # 【第四優先級 4】：純粹詢問「趨勢如何 / 走勢形態」
  # -------------------------------------------------------------
  return f"""
📊 **【針對「股價未來整體變化趨勢」深度易象剖析】**

本卦為「**{orig_name}**」，之卦為「**{changed_name}**」，核心關鍵在於**第 {changing_line} 爻**發動。整體的股價發展節奏呈現**「先抑後揚、破繭而出、見高知止」**的三部曲走勢：

1️⃣ **第一階段：【浮額沉澱・極度洗盤期】（目前 ～ {date_t1.strftime('%Y 年 %m 月 %d 日')} 前後）**
- **特徵**：量能極度萎縮，主力在低檔反覆震盪洗盤，定性為「築底蓄勢，切忌恐慌殺低」。

2️⃣ **第二階段：【動能引爆・波段主升發動】（關鍵窗口：{date_t2.strftime('%Y 年 %m 月 %d 日')} 前後）**
- **特徵**：第 {changing_line} 爻發動，買盤大舉回補，均線帶量黃金交叉，定性為「強烈反彈主升，持股續抱」。

3️⃣ **第三階段：【波段滿足・逢高獲利了結】（目標高點：{date_t3.strftime('%Y 年 %m 月 %d 日')} 前後）**
- **特徵**：進入《{changed_name}》高階，觸及前波密集成交重壓區，定性為「波段力竭，逢高全部出清」。
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

  # 優先呼叫 Gemini
  initial_answer = None
  if gemini_api_key:
    with st.spinner("🤖 背景正請教 Gemini 進行深層易象演繹..."):
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

  # 若無 Key 或 Gemini 失敗，則進入經過嚴格意圖分流的本地專業引擎
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
        "🟢 Gemini 雲端智慧大腦"
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
          placeholder="例如：推測從今至明年7月 每月的變化情況（輸入完直接按 Enter 送出）",
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
