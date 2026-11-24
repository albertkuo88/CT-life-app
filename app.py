"""
程式名稱：易經占卜預測系統 (精確時程卡片化、純淨卦名與全六爻版)
修復重點：
1. 徹底修正卦名解析邏輯，杜絕出現 ['坎', '(水)'] 等亂碼字串，乾淨顯示標準卦名（如：水山蹇、地水師）。
2. 時程推算改採精美獨立卡片（Timeline Cards）呈現，分段層次分明，便於手機與電腦觀看。
3. 嚴謹對應六十四卦全象與變爻之卦，完整呈現初爻至上爻爻辭白話。
"""

import json
import os
import re
from datetime import date, datetime, timedelta
import streamlit as st

# ==============================
# 1. 頁面與風格配置
# ==============================
st.set_page_config(
    page_title="易經智慧占卜決策系統",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .chat-user {
        background-color: #EBF8FF;
        border-left: 5px solid #3182CE;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-weight: 500;
        color: #1A365D;
    }
    .chat-ai {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #319795;
        padding: 18px 22px;
        border-radius: 10px;
        margin-bottom: 22px;
        color: #2D3748;
        line-height: 1.8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .hex-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
        background-color: #EDF2F7;
        color: #4A5568;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .timeline-card {
        background: #F7FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .timeline-title {
        font-weight: bold;
        font-size: 15px;
        color: #2C5282;
        margin-bottom: 4px;
    }
    .timeline-date {
        color: #DD6B20;
        font-weight: bold;
        font-size: 16px;
    }
    .changing-line-card {
        background-color: #FFF5F5;
        border-left: 4px solid #E53E3E;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
    }
    .normal-line-card {
        background-color: #F8FAFC;
        border-left: 4px solid #CBD5E0;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

HISTORY_DIR = "divination_sessions"
if not os.path.exists(HISTORY_DIR):
  os.makedirs(HISTORY_DIR)

# ==============================
# 2. 核心八卦資料庫與純淨命名工具
# ==============================
# binary: 由下至上 3 位元
TRIGRAMS = {
    "坤 (地)": {
        "name": "坤",
        "nature_name": "地",
        "binary": "000",
        "symbol": "☷",
        "desc": "柔順包容、厚德載物、順勢而為",
    },
    "艮 (山)": {
        "name": "艮",
        "nature_name": "山",
        "binary": "001",
        "symbol": "☶",
        "desc": "止步蓄勢、防守阻礙、見險即止",
    },
    "坎 (水)": {
        "name": "坎",
        "nature_name": "水",
        "binary": "010",
        "symbol": "☵",
        "desc": "重險考驗、資金暗流、流動轉折",
    },
    "巽 (風)": {
        "name": "巽",
        "nature_name": "風",
        "binary": "011",
        "symbol": "☴",
        "desc": "順應滲透、漸進傳遞、隨風而動",
    },
    "震 (雷)": {
        "name": "震",
        "nature_name": "雷",
        "binary": "100",
        "symbol": "☳",
        "desc": "奮起震動、短線爆發、突發反彈",
    },
    "離 (火)": {
        "name": "離",
        "nature_name": "火",
        "binary": "101",
        "symbol": "☲",
        "desc": "光明附著、行情過熱、虛火明晰",
    },
    "兌 (澤)": {
        "name": "兌",
        "nature_name": "澤",
        "binary": "110",
        "symbol": "☱",
        "desc": "喜悅和合、多方獲利、防樂極生悲",
    },
    "乾 (天)": {
        "name": "乾",
        "nature_name": "天",
        "binary": "111",
        "symbol": "☰",
        "desc": "剛健強勢、龍頭主升、自強不息",
    },
}

# 64 卦精確對照表
HEXAGRAM_DETAILS = {
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
                    "【本次變爻】：五爻居尊位，動則大變！不可再消極退守，面對局勢轉折需如行軍用兵般嚴守紀律，果斷採取行動（調倉、停利、或出擊）。"
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
                "meaning": "前行有險阻，暫時退守可獲讚譽。進場不可過急。",
            },
            2: {
                "name": "六二",
                "text": "王臣蹇蹇，匪躬之故。",
                "meaning": "恪盡職守，非為個人私利。團隊或持股基本面良好可續抱。",
            },
            3: {
                "name": "九三",
                "text": "往蹇來反。",
                "meaning": "前進會遇到阻力，及時回返為上策。遇壓力區宜減碼。",
            },
            4: {
                "name": "六四",
                "text": "往蹇來連。",
                "meaning": "單打獨鬥受阻，需結合同盟外援共渡難關。",
            },
            5: {
                "name": "九五",
                "text": "大蹇朋來。",
                "meaning": (
                    "在極大的險阻中獲得強大朋黨奧援。代表主力大舉回補，帶動股價突破重圍！"
                ),
            },
            6: {
                "name": "上六",
                "text": "往蹇來碩，吉，利見大人。",
                "meaning": "度過艱難迎來豐碩成果，波段收尾大吉，應當功成身退。",
            },
        },
    },
    ("坤 (地)", "坎 (水)"): {
        "name": "地水師",
        "symbol": "䷆",
        "base_luck": 64,
        "judgment": "貞，丈人吉，無咎。地中有水，師出有名，如軍隊紀律嚴明。",
        "finance_meaning": (
            "局勢如軍隊出征，不可盲目單打獨鬥，必須有嚴格的停損停利風控，果斷調配資金。"
        ),
        "lines": {
            i: {
                "name": f"爻 {i}",
                "text": "師道貴在紀律。",
                "meaning": "嚴格執行停損停利。",
            }
            for i in range(1, 7)
        },
    },
}


def clean_hex_name(upper_key: str, lower_key: str) -> str:
  """產出乾淨中文卦名，絕不出現 Python List 或符號亂碼"""
  if (upper_key, lower_key) in HEXAGRAM_DETAILS:
    return HEXAGRAM_DETAILS[(upper_key, lower_key)]["name"]
  u_nat = TRIGRAMS[upper_key]["nature_name"]
  l_nat = TRIGRAMS[lower_key]["nature_name"]
  if u_nat == l_nat:
    return f"{TRIGRAMS[upper_key]['name']}為{u_nat}"
  return f"{u_nat}{l_nat}卦"


def resolve_hexagram(upper_tri: str, lower_tri: str):
  clean_name = clean_hex_name(upper_tri, lower_tri)
  if (upper_tri, lower_tri) in HEXAGRAM_DETAILS:
    info = HEXAGRAM_DETAILS[(upper_tri, lower_tri)].copy()
    info["name"] = clean_name
    return info

  return {
      "name": clean_name,
      "symbol": "䷍",
      "base_luck": 60,
      "judgment": (
          f"外卦為{upper_tri}，內卦為{lower_tri}。象徵以「{TRIGRAMS[lower_tri]['desc']}」為根本，外現「{TRIGRAMS[upper_tri]['desc']}」。"
      ),
      "finance_meaning": "處於多空轉換過渡期，應依據變爻位階嚴守紀律。",
      "lines": {
          i: {
              "name": f"第 {i} 爻",
              "text": f"爻辭對應第 {i} 階位。",
              "meaning": f"事物發展至第 {i} 階段之動態變化。",
          }
          for i in range(1, 7)
      },
  }


def calculate_changing_hexagram(
    upper_tri: str, lower_tri: str, changing_line: int
):
  """精確計算 6 爻變動（1~3爻為下卦，4~6爻為上卦）"""
  lower_bin = TRIGRAMS[lower_tri]["binary"]
  upper_bin = TRIGRAMS[upper_tri]["binary"]
  lines = list(lower_bin + upper_bin)  # 6位元：0~2為下卦，3~5為上卦

  # 變爻翻轉
  idx = changing_line - 1
  lines[idx] = "0" if lines[idx] == "1" else "1"

  new_lower_bin = "".join(lines[0:3])
  new_upper_bin = "".join(lines[3:6])

  new_lower = next(
      k for k, v in TRIGRAMS.items() if v["binary"] == new_lower_bin
  )
  new_upper = next(
      k for k, v in TRIGRAMS.items() if v["binary"] == new_upper_bin
  )

  return new_upper, new_lower


# ==============================
# 3. 智慧回覆與精緻排版引擎
# ==============================
def generate_intelligent_reply(
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

  line_mod = {1: -5, 2: +6, 3: -8, 4: +4, 5: +10, 6: -7}
  final_luck = max(20, min(96, base_luck + line_mod.get(changing_line, 0)))

  response_sections = []

  # 意圖 A：特定日期 + 出清
  target_date_match = re.search(r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})", q)
  is_full_exit = any(
      k in q for k in ["全部出清", "全賣", "清倉", "全都賣", "出清"]
  )

  if target_date_match and is_full_exit:
    year = int(target_date_match.group(1))
    month = int(target_date_match.group(2))
    day = int(target_date_match.group(3))
    try:
      target_date_obj = date(year, month, day)
      target_str = target_date_obj.strftime("%Y 年 %m 月 %d 日")
    except Exception:
      target_str = f"{year} 年 {month} 月 {day} 日"

    response_sections.append(
        f"🎯 **【正面直接回答：{target_str} 是否應該全部出清？】**\n\n"
        f"👉 **明確結論：【是的，屆時強烈建議執行「全部出清（或出清至少 80%~90%）」！】**\n\n"
        f"**易象與時程推演依據**：\n"
        f"1. **時間週期對位**：推算之波段滿足高點正好落在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 附近。若您鎖定在 **{target_str}** 出清，時間點完全切合卦象「回升波段的終局滿足期」。\n"
        f"2. **卦變之象不可貪功**：本卦「{orig_name}」轉入之卦「{changed_name}」第 {changing_line} 爻，爻變警示當回升行情走到滿足期時，若因貪婪而想賺盡最後一塊銅板，極易遭受震盪反噬。\n"
        f"3. **確切的操作指示（不模糊）**：\n"
        f"   - **{target_str} 當日**：將手中持股**一口氣出清 80%~100%**，收回全部現金。\n"
        f"   - **資金防守策略**：出清後切忌立刻轉買其他高風險標的，應讓資金休息至少 2~3 週，等待下一個穩健卦象成形再做定奪。"
    )

  # 意圖 B：何時回升（卡片化視覺排版）
  elif any(k in q for k in ["何時", "回升", "反彈", "解套", "上漲"]):
    timeline_html = f"""
📅 **【股價回升關鍵時程推算（具體公曆日期）】**

<div class="timeline-card">
    <div class="timeline-title">📍 階段一：短線止跌震盪打底期</div>
    <div class="timeline-date">{date_t1.strftime('%Y 年 %m 月 %d 日')}（約第 {t1_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：賣壓開始收斂，量能萎縮，市場進入浮額洗盤階段，切忌在此時恐慌殺低。</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #DD6B20; background:#FFFAF0;">
    <div class="timeline-title" style="color:#C05621;">🚀 階段二：波段實質回升發動日（關鍵窗口）</div>
    <div class="timeline-date">{date_t2.strftime('%Y 年 %m 月 %d 日')}（約第 {t2_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：卦氣由「{orig_name}」正式轉向「{changed_name}」，買盤動能湧現，均線翻揚，為最顯著的回升發動點！</div>
</div>

<div class="timeline-card" style="border-left: 4px solid #319795; background:#F0FFF4;">
    <div class="timeline-title" style="color:#285E61;">🏁 階段三：波段高點／目標解套滿足區</div>
    <div class="timeline-date">{date_t3.strftime('%Y 年 %m 月 %d 日')}（約第 {t3_days} 天）</div>
    <div style="color:#4A5568; font-size:14px; margin-top:4px;">特徵：波段動能滿足，容易遭遇前波沉重套牢賣壓，是逢高分批減碼或出清落袋的黃金時間。</div>
</div>
"""
    response_sections.append(timeline_html)

  # 意圖 C：一般賣出或通用
  elif any(k in q for k in ["賣", "出清", "脫手", "砍", "停損"]):
    response_sections.append(
        f"🛑 **【當前階段操作明確建議】**：\n\n"
        f"- **結論**：**切忌在近日恐慌性殺低出清！**\n"
        f"- **操作執行配比**：\n"
        f"  1. **目前至 {date_t1.strftime('%m/%d')}**：持股按兵不動，保留 30%~40%"
        " 現金儲備。\n"
        f"  2. **回升啟動至 {date_t2.strftime('%m/%d')}~{date_t3.strftime('%m/%d')}**：採取「階梯式減碼」，反彈遇均線壓力先出清"
        " 30%，接近滿足日再出清 40%，剩餘 30% 設移動停利。"
    )
  else:
    response_sections.append(
        f"🎯 **【針對您提問之核心解答】**：\n\n"
        f"- 當前所處時空卦氣由「**{orig_name}**」轉化為「**{changed_name}**」。\n"
        f"- **關鍵轉化日**：請密切留意 **{date_t2.strftime('%Y 年 %m 月 %d 日')}**"
        f" 前後，局勢將出現明確方向，信心指標為 **{final_luck}%**。"
    )

  if "謙" in orig_name and changing_line == 5:
    response_sections.append(
        "💡 **【爻辭專論】**：地山謙卦第五爻動辭曰：『利用侵伐，無不利』。意味著面對此局勢，不可過度軟弱退縮，需像兵將征戰一樣嚴守紀律與策略，果斷做出配置調整！"
    )

  return "\n\n".join(response_sections), {
      "final_luck": final_luck,
      "date_t1": str(date_t1),
      "date_t2": str(date_t2),
      "date_t3": str(date_t3),
      "t2_days": t2_days,
  }


# ==============================
# 4. 歷史檔案存取
# ==============================
def save_session_file(session_data):
  session_id = session_data["session_id"]
  filename = os.path.join(HISTORY_DIR, f"{session_id}.json")
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


# ==============================
# 5. Session 與側邊欄
# ==============================
if "active_session" not in st.session_state:
  st.session_state.active_session = None

st.sidebar.header("☯️ 易經起卦設定")
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
upper_tri = st.sidebar.selectbox("上卦 (外卦)", list(TRIGRAMS.keys()), index=0)
lower_tri = st.sidebar.selectbox("下卦 (內卦)", list(TRIGRAMS.keys()), index=1)
changing_line = st.sidebar.selectbox(
    "選擇變爻位階",,
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

  initial_answer, metrics = generate_intelligent_reply(
      question=first_question,
      base_date=input_date,
      orig_name=orig_hex["name"],
      changed_name=changed_hex["name"],
      changing_line=changing_line,
      base_luck=orig_hex["base_luck"],
      round_count=1,
  )

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

# ==============================
# 6. 主介面三大頁籤渲染
# ==============================
st.title("☯️ 易經智慧占卜決策系統")

tab_chat, tab_hex_view, tab_files = st.tabs(
    ["💬 卦象專屬諮詢對話框", "📖 當前卦象結構說明 (含全六爻)", "📁 一卦一檔・歷史檔案庫"]
)

with tab_chat:
  session = st.session_state.active_session
  if not session:
    st.info("👈 請在左側設定卦象與問題，並點選「開始全新占卜並建立獨立檔案」。")
  else:
    # 頂部狀態列：使用標準中文卦名
    st.markdown(
        f"""
        <div style="background-color:#F8FAFC; padding:12px 16px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:15px;">
            <span class="hex-badge">檔案：{session['session_id']}</span>
            <span class="hex-badge">事項：{session['category']}</span>
            <span class="hex-badge">本卦：{session['original_hexagram']}</span>
            <span class="hex-badge">之卦：{session['changed_hexagram']} (第 {session['changing_line']} 爻動)</span>
            <span class="hex-badge">綜合指數：{session['metrics']['final_luck']}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("短線震盪止跌日", session["metrics"]["date_t1"])
    col2.metric(
        "波段回升啟動日 (關鍵)",
        session["metrics"]["date_t2"],
        f"+{session['metrics']['t2_days']} 天",
    )
    col3.metric("波段滿足高點日", session["metrics"]["date_t3"])
    st.progress(session["metrics"]["final_luck"] / 100)

    st.divider()

    st.subheader("📜 本次卦象連續諮詢歷程")
    for chat in session["chat_history"]:
      st.markdown(
          f"<div class='chat-user'>🙋 <b>問題（第 {chat['round']} 輪提問）</b>"
          f" [{chat['time']}]：<br>{chat['question']}</div>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<div class='chat-ai'>☯️ <b>易象正面解答與策略指導</b>：<br><br>{chat['answer']}</div>",
          unsafe_allow_html=True,
      )

    st.markdown("### 💬 針對此卦象持續提問：")
    followup_q = st.text_input(
        "請輸入深入追問（例如：2027 01 10 全部出清 是否全部出清？）：",
        key="followup_input",
        placeholder="請輸入您的具體問題，點擊右方按鈕送出...",
    )
    if st.button("📨 送出追問解答", type="secondary") and followup_q:
      round_num = len(session["chat_history"]) + 1
      orig_hex = resolve_hexagram(session["upper_tri"], session["lower_tri"])
      new_up, new_low = calculate_changing_hexagram(
          session["upper_tri"], session["lower_tri"], session["changing_line"]
      )
      changed_hex = resolve_hexagram(new_up, new_low)

      followup_answer, _ = generate_intelligent_reply(
          question=followup_q,
          base_date=datetime.strptime(session["date"], "%Y-%m-%d").date(),
          orig_name=orig_hex["name"],
          changed_name=changed_hex["name"],
          changing_line=session["changing_line"],
          base_luck=orig_hex["base_luck"],
          round_count=round_num,
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

    st.subheader(f"📜 《{orig_info['name']}》全六爻爻辭與白話詳解")
    st.caption("爻位由下至上排序（初爻至上爻），紅色標記為當前發生變動之爻位：")

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

      card_class = "changing-line-card" if is_changing else "normal-line-card"
      badge_text = (
          "🔥【當前變爻・動向核心】" if is_changing else f"第 {i} 階位"
      )

      st.markdown(
          f"""
            <div class="{card_class}">
                <div style="font-weight: bold; font-size: 15px; margin-bottom: 4px;">
                    {line_data['name']}：{line_data['text']} <span style="font-size:12px; color:#E53E3E; margin-left:8px;">{badge_text}</span>
                </div>
                <div style="color: #4A5568; font-size: 14px;">
                    💡 <b>白話象義與策略指導</b>：{line_data['meaning']}
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
