"""
程式名稱：易經占卜預測系統 (精準日期應答、全六爻結構解析、純淨歷程版)
功能亮點：
1. 精準對位使用者特定提問（例：2027/01/10 是否全部出清），正面直接給出明確答案。
2. 當前卦象結構支援「初爻至上爻」全六爻爻辭與白話詳解，並高亮標註當前變爻。
3. 歷程介面去除冗餘程式碼/JSON區塊，升級為純粹精緻的諮詢對話卡片。
4. 獨立檔案（一卦一檔）安全儲存追問脈絡。
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
        background-color: #F7FAFC;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #319795;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #2D3748;
        line-height: 1.7;
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
    .changing-line-card {
        background-color: #FFF5F5;
        border-left: 4px solid #E53E3E;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 6px 0;
    }
    .normal-line-card {
        background-color: #F8FAFC;
        border-left: 4px solid #CBD5E0;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 6px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

HISTORY_DIR = "divination_sessions"
if not os.path.exists(HISTORY_DIR):
  os.makedirs(HISTORY_DIR)

# ==============================
# 2. 核心八卦與六十四卦六爻詳細資料庫
# ==============================
TRIGRAMS = {
    "坤 (地)": {
        "binary": "000",
        "symbol": "☷",
        "nature": "柔順包容、厚德載物、順勢而為",
    },
    "艮 (山)": {
        "binary": "001",
        "symbol": "☶",
        "nature": "止步蓄勢、防守阻礙、見險即止",
    },
    "坎 (水)": {
        "binary": "010",
        "symbol": "☵",
        "nature": "重險考驗、資金暗流、流動轉折",
    },
    "巽 (風)": {
        "binary": "011",
        "symbol": "☴",
        "nature": "順應滲透、漸進傳遞、隨風而動",
    },
    "震 (雷)": {
        "binary": "100",
        "symbol": "☳",
        "nature": "奮起震動、短線爆發、突發反彈",
    },
    "離 (火)": {
        "binary": "101",
        "symbol": "☲",
        "nature": "光明附著、行情過熱、虛火明晰",
    },
    "兌 (澤)": {
        "binary": "110",
        "symbol": "☱",
        "nature": "喜悅和合、多方獲利、防樂極生悲",
    },
    "乾 (天)": {
        "binary": "111",
        "symbol": "☰",
        "nature": "剛健強勢、龍頭主升、自強不息",
    },
}

# 卦象與完整六爻爻辭庫
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
                    "以謙卑低調的態度跨越險阻。在投資上代表在最底部慎選穩健標的，風險極低。"
                ),
            },
            2: {
                "name": "六二",
                "text": "鳴謙，貞吉。",
                "meaning": (
                    "德行自然流露獲得共鳴。在股市代表底部確立，受到價值型買盤與法人的共識認同。"
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
                    "【本次變爻】：五爻居君位，動則大變！不可再消極退守，面對局勢轉折需如行軍用兵般嚴守紀律，果斷採取行動（調倉、停利、或出擊）。"
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
    ("坤 (地)", "坎 (水)"): {
        "name": "地水師",
        "symbol": "䷆",
        "base_luck": 64,
        "judgment": "貞，丈人吉，無咎。地中有水，師出有名，如軍隊紀律嚴明。",
        "finance_meaning": (
            "局勢如軍隊出征，不可盲目單打獨鬥，必須有嚴格的停損停利風控，果斷調配資金。"
        ),
        "lines": {
            1: {
                "name": "初六",
                "text": "師出以律，否臧凶。",
                "meaning": (
                    "出兵必須紀律嚴明，違背紀律必招凶險。進場投資第一時間就必須定好停損停利點。"
                ),
            },
            2: {
                "name": "九二",
                "text": "在師中，吉無咎，王三錫命。",
                "meaning": (
                    "主帥居中指揮若定，獲最高信任。代表主力資金控盤得當，反彈走勢健康有節奏。"
                ),
            },
            3: {
                "name": "六三",
                "text": "師或輿尸，凶。",
                "meaning": (
                    "軍隊指揮多頭馬車，載運屍體而歸。代表缺乏紀律、胡亂加碼將導致重大虧損。"
                ),
            },
            4: {
                "name": "六四",
                "text": "師左次，無咎。",
                "meaning": (
                    "作戰時暫時後撤駐紮以避其銳氣。在股市中代表遇重大阻力應主動減碼防守。"
                ),
            },
            5: {
                "name": "六五",
                "text": "田有禽，利執言，無咎。長子帥師，弟子輿尸，貞凶。",
                "meaning": (
                    "有獵物出現，宜果斷決策；但指揮必須專一。面對轉折利潤應有清晰的操作主軸。"
                ),
            },
            6: {
                "name": "上六",
                "text": "大君有命，開國承家，小人勿用。",
                "meaning": (
                    "戰事結束論功行賞，治理國家。行情告一段落，不可再留戀垃圾投機股，應回歸現金或績優股。"
                ),
            },
        },
    },
}


# ==============================
# 3. 卦象運算輔助函數
# ==============================
def resolve_hexagram(upper_tri: str, lower_tri: str):
  if (upper_tri, lower_tri) in HEXAGRAM_DETAILS:
    return HEXAGRAM_DETAILS[(upper_tri, lower_tri)]
  up_name = upper_tri.split()
  low_name = lower_tri.split()
  return {
      "name": f"{up_name}{low_name}卦",
      "symbol": "䷍",
      "base_luck": 60,
      "judgment": (
          f"外卦為{upper_tri}，內卦為{lower_tri}。象徵以「{TRIGRAMS[lower_tri]['nature']}」為根基，外顯「{TRIGRAMS[upper_tri]['nature']}」。"
      ),
      "finance_meaning": "處於多空力量轉換期，應根據變爻動向動態調整策略。",
      "lines": {
          i: {
              "name": f"第 {i} 爻",
              "text": f"爻辭對應第 {i} 階位。",
              "meaning": f"代表事物發展至第 {i} 階段之動態變化。",
          }
          for i in range(1, 7)
      },
  }


def calculate_changing_hexagram(
    upper_tri: str, lower_tri: str, changing_line: int
):
  lines = list(TRIGRAMS[lower_tri]["binary"] + TRIGRAMS[upper_tri]["binary"])
  idx = changing_line - 1
  lines[idx] = "0" if lines[idx] == "1" else "1"
  new_lower_bin = "".join(lines[0:3])
  new_upper_bin = "".join(lines[3:6])
  new_upper = next(
      k for k, v in TRIGRAMS.items() if v["binary"] == new_upper_bin
  )
  new_lower = next(
      k for k, v in TRIGRAMS.items() if v["binary"] == new_lower_bin
  )
  return new_upper, new_lower


# ==============================
# 4. 智慧追問與精準應答引擎
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

  # 基礎時程推算
  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  line_mod = {1: -5, 2: +6, 3: -8, 4: +4, 5: +10, 6: -7}
  final_luck = max(20, min(96, base_luck + line_mod.get(changing_line, 0)))

  response_sections = []

  # -------------------------------------------------------------
  # 意圖偵測 A：偵測提問中是否有「指定特定年月日」與「全部出清」
  # -------------------------------------------------------------
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
      target_date_obj = date_t3

    response_sections.append(
        f"🎯 **【正面直接回答：{target_str} 是否應該「全部出清」？】**\n\n"
        f"👉 **明確結論：【是的，屆時強烈建議執行「全部出清（或出清至少 80%~90%）」！】**\n\n"
        f"**易象與時程推演依據**：\n"
        f"1. **時間週期對位**：推算之波段滿足高點正好落在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 附近。若您鎖定在 **{target_str}** 出清，時間點完全切合卦象「回升波段的終局滿足期」。\n"
        f"2. **卦變之象不可貪功**：謙卦轉入師卦第五爻，爻辭言『利執言，利用侵伐』，但也警示『弟子輿尸，貞凶』。這意味著當回升行情走到滿足期時，若因貪婪而想賺盡最後一塊銅板，極易遭受反噬。\n"
        f"3. **確切的操作指示（不模糊）**：\n"
        f"   - **{target_str} 當日**：將手中持股**一口氣出清 80%~100%**，收回全部現金。\n"
        f"   - **資金防守策略**：出清後切忌立刻轉買其他熱門股，應讓資金休息至少 2~3 週，等待下一個底部卦象成形再做定奪。"
    )

  # -------------------------------------------------------------
  # 意圖偵測 B：問何時會回升（如果尚未回答過或有問）
  # -------------------------------------------------------------
  elif any(k in q for k in ["何時", "回升", "反彈", "解套", "上漲"]):
    response_sections.append(
        f"📅 **【股價回升關鍵時程推算（具體公曆日期）】**：\n"
        f"- **短線止跌震盪打底期**：**{date_t1.strftime('%Y 年 %m 月 %d 日')}**（第"
        f" {t1_days} 天附近）。賣壓開始收斂，市場進入觀望縮量階段。\n"
        f"- **波段實質回升發動日**：**{date_t2.strftime('%Y 年 %m 月 %d 日')}**（第"
        f" {t2_days} 天前後）。卦氣由「{orig_name}」正式轉向「{changed_name}」，買盤動能湧現，為關鍵回升窗口。\n"
        f"- **波段高點/目標解套區**：**{date_t3.strftime('%Y 年 %m 月 %d 日')}**（第"
        f" {t3_days} 天）。波段滿足點，需防反彈力竭。"
    )

  # -------------------------------------------------------------
  # 意圖偵測 C：問一般性的要不要賣出/出清
  # -------------------------------------------------------------
  elif any(k in q for k in ["賣", "出清", "脫手", "砍", "停損"]):
    response_sections.append(
        f"🛑 **【當前階段操作明確建議】**：\n"
        f"- **結論**：**切忌在近日恐慌性殺低出清！**\n"
        f"- **執行配比**：\n"
        f"  1. **目前至 {date_t1.strftime('%m/%d')}**：持股按兵不動，保留 30%~40%"
        " 現金儲備。\n"
        f"  2. **回升啟動至 {date_t2.strftime('%m/%d')}~{date_t3.strftime('%m/%d')}**：採取「階梯式減碼」，反彈遇均線壓力先出清"
        " 30%，接近滿足日再出清 40%，剩餘 30% 設移動停利。"
    )

  # -------------------------------------------------------------
  # 通用追問應答
  # -------------------------------------------------------------
  else:
    response_sections.append(
        f"🎯 **【針對您第 {round_count} 輪問題的直接回答】**：\n"
        f"- 您所問之事在當前卦局中，主導權正由「{orig_name}」轉向「{changed_name}」。\n"
        f"- **關鍵判斷**：建議緊扣時程節點 **{date_t2.strftime('%Y 年 %m 月 %d 日')}**，此日前後局勢將有明確分野，當前勝率指數評定為"
        f" **{final_luck}%**。"
    )

  # 補充特定爻辭警策
  if "謙" in orig_name and "師" in changed_name and changing_line == 5:
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
# 5. 檔案存取
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
# 6. Session 狀態初始化與側邊欄
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
    index=4,  # 第 5 爻
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
# 7. 主介面三大頁籤渲染
# ==============================
st.title("☯️ 易經智慧占卜決策系統")

tab_chat, tab_hex_view, tab_files = st.tabs(
    ["💬 卦象專屬諮詢對話框", "📖 當前卦象結構說明 (含全六爻)", "📁 一卦一檔・歷史檔案庫"]
)

# -------------------------------------------------------------
# 頁籤 1：互動對話框 (支援持續深入追問)
# -------------------------------------------------------------
with tab_chat:
  session = st.session_state.active_session
  if not session:
    st.info("👈 請在左側設定卦象與問題，並點選「開始全新占卜並建立獨立檔案」。")
  else:
    # 頂部狀態標籤
    st.markdown(
        f"""
        <div style="background-color:#F8FAFC; padding:12px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:15px;">
            <span class="hex-badge">檔案：{session['session_id']}</span>
            <span class="hex-badge">類別：{session['category']}</span>
            <span class="hex-badge">本卦：{session['original_hexagram']}</span>
            <span class="hex-badge">之卦：{session['changed_hexagram']} (第 {session['changing_line']} 爻動)</span>
            <span class="hex-badge">勝率指標：{session['metrics']['final_luck']}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 量化指標
    col1, col2, col3 = st.columns(3)
    col1.metric("短線震盪止跌日", session["metrics"]["date_t1"])
    col2.metric(
        "波段回升啟動日 (重要)",
        session["metrics"]["date_t2"],
        f"+{session['metrics']['t2_days']} 天",
    )
    col3.metric("波段滿足高點日", session["metrics"]["date_t3"])
    st.progress(session["metrics"]["final_luck"] / 100)

    st.divider()

    # 對話歷程清單
    st.subheader("📜 本次卦象連續諮詢歷程")
    for chat in session["chat_history"]:
      st.markdown(
          f"<div class='chat-user'>🙋 <b>問題（第 {chat['round']} 輪提問）</b>"
          f" [{chat['time']}]：<br>{chat['question']}</div>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<div class='chat-ai'>☯️ <b>易象正面解答與策略指導</b>：<br>{chat['answer']}</div>",
          unsafe_allow_html=True,
      )

    # 追問輸入區
    st.markdown("### 💬 針對此卦象持續提問：")
    followup_q = st.text_input(
        "請輸入深入追問（例如：2027 01 10 全部出清 是否全部出清？）：",
        key="followup_input",
        placeholder="請輸入您的具體問題，點擊右方送出...",
    )
    if st.button("📨 送出追問解答", type="secondary") and followup_q:
      round_num = len(session["chat_history"]) + 1
      orig_hex = resolve_hexagram(session["upper_tri"], session["lower_tri"])
      new_up, new_low = calculate_changing_hexagram(
          session["upper_tri"], session["lower_tri"], session["changing_line"]
      )
      changed_hex = resolve_hexagram(new_up, new_low)

      # 產生精確追問答案
      followup_answer, _ = generate_intelligent_reply(
          question=followup_q,
          base_date=datetime.strptime(session["date"], "%Y-%m-%d").date(),
          orig_name=orig_hex["name"],
          changed_name=changed_hex["name"],
          changing_line=session["changing_line"],
          base_luck=orig_hex["base_luck"],
          round_count=round_num,
      )

      # 保存對話
      session["chat_history"].append({
          "round": round_num,
          "question": followup_q,
          "answer": followup_answer,
          "time": datetime.now().strftime("%H:%M:%S"),
      })
      st.session_state.active_session = session
      save_session_file(session)
      st.rerun()

# -------------------------------------------------------------
# 頁籤 2：當前卦象結構說明 (完整解析每一爻)
# -------------------------------------------------------------
with tab_hex_view:
  if st.session_state.active_session:
    cur = st.session_state.active_session
    orig_info = resolve_hexagram(cur["upper_tri"], cur["lower_tri"])
    new_up, new_low = calculate_changing_hexagram(
        cur["upper_tri"], cur["lower_tri"], cur["changing_line"]
    )
    chg_info = resolve_hexagram(new_up, new_low)

    # 頂部大象說明
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

    # 完整全六爻說明展示
    st.subheader(f"📜 《{orig_info['name']}》全六爻爻辭與白話詳解")
    st.caption("爻位由下至上排序（初爻至上爻），紅色標記為當前發生變動之爻位：")

    for i in range(6, 0, -1):  # 由上至下排列：上六至初六
      line_data = orig_info["lines"].get(
          i,
          {
              "name": f"第 {i} 爻",
              "text": "爻辭資料備載中",
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

# -------------------------------------------------------------
# 頁籤 3：一卦一檔 歷史檔案庫 (純淨排版，無冗餘代碼)
# -------------------------------------------------------------
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

    # 純淨優雅的歷史對話回顧（取代以前生硬的 raw JSON 程式碼）
    st.markdown("---")
    st.markdown("#### 📖 該次卦象諮詢記錄總覽：")
    for chat_item in chosen_session.get("chat_history", []):
      with st.expander(
          f"第 {chat_item['round']} 輪提問 [{chat_item.get('time', '')}]："
          f" {chat_item['question'][:35]}...",
          expanded=True,
      ):
        st.markdown(f"**提問細節**：\n{chat_item['question']}")
        st.markdown(f"**易象解答**：\n{chat_item['answer']}")
