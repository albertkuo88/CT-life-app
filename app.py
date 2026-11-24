"""
程式名稱：易經占卜預測系統 (多輪追問對話與獨立卦象建檔版)
功能特點：
1. 單卦多輪智慧對話框：可針對同一卦象持續深入提問並獲得具體推算。
2. 一卦一檔：每次起卦獨立生成專屬歷史檔案，完整收錄起卦數據與後續所有對話。
3. 具體日期推算與量化決策指標。
4. UI 視覺現代化與對話式互動排版。
"""

import json
import os
import re
from datetime import date, datetime, timedelta
import streamlit as st

# ==============================
# 1. 頁面配置與現代化樣式注入
# ==============================
st.set_page_config(
    page_title="易經智慧占卜諮詢系統",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .chat-user {
        background-color: #EBF3FB;
        border-left: 5px solid #2B6CB0;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-weight: 500;
        color: #1A365D;
    }
    .chat-ai {
        background-color: #F7FAFC;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #319795;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 16px;
        color: #2D3748;
        line-height: 1.6;
    }
    .hex-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
        background-color: #E2E8F0;
        color: #4A5568;
        margin-right: 6px;
    }
</style>
""",
    unsafe_allow_html=True,
)

HISTORY_DIR = "divination_sessions"
if not os.path.exists(HISTORY_DIR):
  os.makedirs(HISTORY_DIR)

# ==============================
# 2. 八卦與六十四卦核心庫
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

HEXAGRAM_MAPPING = {
    ("坤 (地)", "艮 (山)"): {
        "name": "地山謙",
        "symbol": "䷎",
        "base_luck": 82,
        "judgment": "亨，君子有終。地中有山，內高而外下，謙遜退讓吉。",
        "finance_meaning": (
            "行情處於築底蓄勢階段，表面平淡但底部扎實，切忌追高，宜逢低耐心分批佈局。"
        ),
    },
    ("坤 (地)", "坎 (水)"): {
        "name": "地水師",
        "symbol": "䷆",
        "base_luck": 64,
        "judgment": "貞，丈人吉，無咎。地中有水，師出有名，如軍隊紀律嚴明。",
        "finance_meaning": (
            "局勢如軍隊行軍作戰，不可單打獨鬥，必須有嚴格的風控與紀律，果斷調配資金。"
        ),
    },
    ("乾 (天)", "乾 (天)"): {
        "name": "乾為天",
        "symbol": "䷀",
        "base_luck": 88,
        "judgment": "元亨利貞。天行健，君子以自強不息。",
        "finance_meaning": "強勢多頭格局，大盤主升段，但須防上爻亢龍有悔。",
    },
    ("坤 (地)", "坤 (地)"): {
        "name": "坤為地",
        "symbol": "䷁",
        "base_luck": 70,
        "judgment": "元亨，利牝馬之貞。主靜守、包容承載。",
        "finance_meaning": "空頭或大盤盤整期，以守為攻，保留現金儲備。",
    },
    ("坎 (水)", "震 (雷)"): {
        "name": "水雷屯",
        "symbol": "䷂",
        "base_luck": 45,
        "judgment": "元亨利貞，勿用有攸往，利建侯。",
        "finance_meaning": "萌芽期震盪劇烈，築底洗盤，切勿急躁重押。",
    },
}


# ==============================
# 3. 核心運算與智慧推算引擎
# ==============================
def resolve_hexagram(upper_tri: str, lower_tri: str):
  if (upper_tri, lower_tri) in HEXAGRAM_MAPPING:
    return HEXAGRAM_MAPPING[(upper_tri, lower_tri)]
  up_name = upper_tri.split()
  low_name = lower_tri.split()
  return {
      "name": f"{up_name}{low_name}卦",
      "symbol": "䷍",
      "base_luck": 60,
      "judgment": (
          f"外卦為{upper_tri}，內卦為{lower_tri}。象徵以「{TRIGRAMS[lower_tri]['nature']}」為根基，外顯「{TRIGRAMS[upper_tri]['nature']}」。"
      ),
      "finance_meaning": "處於多空力量拉鋸期，應緊扣變爻動向動態調整策略。",
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


def generate_intelligent_reply(
    question: str,
    base_date: date,
    orig_name: str,
    changed_name: str,
    changing_line: int,
    base_luck: int,
    round_count: int,
):
  """智慧回答引擎：能識別追問內容並給予確切推算與日期"""
  q = question.lower()
  t1_days = changing_line * 2
  t2_days = changing_line * 5 + 3
  t3_days = changing_line * 8 + 7

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  line_mod = {1: -5, 2: +6, 3: -8, 4: +4, 5: +10, 6: -7}
  final_luck = max(20, min(96, base_luck + line_mod.get(changing_line, 0)))

  response_parts = []

  # 判斷是否為股市相關
  is_stock = any(
      k in q for k in ["股", "台股", "股票", "指數", "大盤", "美股", "標的"]
  )
  is_rebound = any(
      k in q for k in ["回升", "反彈", "解套", "上漲", "漲", "底", "回溫"]
  )
  is_sell = any(
      k in q
      for k in ["賣", "出清", "脫手", "砍", "停損", "停利", "換股", "走人"]
  )

  # 判斷是否為後續追問 (round_count > 1)
  if round_count > 1:
    response_parts.append(
        f"**【針對您第 {round_count} 次延伸追問的易象剖析】**："
    )

  if is_stock or is_rebound or is_sell:
    if is_rebound or "何時" in q:
      response_parts.append(
          f"📅 **【股價回升關鍵時程推算（具體公曆日期）】**：\n"
          f"- **短線止跌震盪打底期**：**{date_t1.strftime('%Y 年 %m 月 %d 日')}**（第"
          f" {t1_days} 天附近）。賣壓開始收斂，市場進入觀望縮量階段。\n"
          f"- **波段實質回升發動日**：**{date_t2.strftime('%Y 年 %m 月 %d 日')}**（第"
          f" {t2_days} 天前後）。卦氣由「{orig_name}」正式轉向「{changed_name}」，買盤動能湧現，為關鍵回升窗口。\n"
          f"- **波段高點/目標解套區**：**{date_t3.strftime('%Y 年 %m 月 %d 日')}**（第"
          f" {t3_days} 天）。波段滿足點，需防反彈力竭。"
      )

    if is_sell:
      if final_luck >= 65:
        response_parts.append(
            f"🛑 **【要不要最近賣掉出清？操作明確建議】**：\n"
            f"- **結論**：**切忌在近日恐慌性全數出清！**\n"
            f"- **理由**：當前卦象顯示處於洗盤磨底階段，此時出清極易賣在起漲前的相對低點。\n"
            f"- **執行配比**：\n"
            f"  1. **目前至 {date_t1.strftime('%m/%d')}**：持股按兵不動，保留 30%~40%"
            " 現金儲備。\n"
            f"  2. **回升啟動至 {date_t2.strftime('%m/%d')}~{date_t3.strftime('%m/%d')}**：採取「階梯式減碼」，反彈遇均線壓力先出清"
            " 30%，接近滿足日再出清 40%，剩餘 30% 設移動停利。"
        )
      else:
        response_parts.append(
            f"⚠️ **【要不要最近賣掉出清？操作明確建議】**：\n"
            f"- **結論**：**建議逢反彈果斷出清，嚴守紀律！**\n"
            f"- **執行配比**：未來 3~5 天內趁技術面反抽，迅速降低持股至 30% 以下。"
        )

  # 通用或哲理回覆
  if not response_parts:
    response_parts.append(
        f"🎯 **【卦象針對當前問題之啟示】**：\n"
        f"- 卦象由「{orig_name}」推移至「{changed_name}」，關鍵變爻在第"
        f" {changing_line} 爻。\n"
        f"- **關鍵轉化日**：約在 **{date_t2.strftime('%Y 年 %m 月 %d 日')}**"
        " 出現明確契機。\n"
        f"- **建議心態**：堅持核心原則，不為短期雜訊所動，事情突破信心指數為"
        f" {final_luck}%。"
    )

  if "謙" in orig_name and "師" in changed_name and changing_line == 5:
    response_parts.append(
        "💡 **【爻辭專論】**：地山謙卦第五爻動辭曰：『利用侵伐，無不利』。意味著面對此局勢，不可過度軟弱退縮，需像兵將征戰一樣嚴守紀律與策略，果斷做出配置調整！"
    )

  return "\n\n".join(response_parts), {
      "final_luck": final_luck,
      "date_t1": str(date_t1),
      "date_t2": str(date_t2),
      "date_t3": str(date_t3),
      "t2_days": t2_days,
  }


# ==============================
# 4. 「一卦一檔」獨立歷史存取模組
# ==============================
def save_session_file(session_data):
  """每次起卦存成獨立的 JSON 檔案"""
  session_id = session_data["session_id"]
  filename = os.path.join(HISTORY_DIR, f"{session_id}.json")
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(session_data, f, ensure_ascii=False, indent=2)


def load_all_sessions():
  """讀取所有獨立歷史檔案清單"""
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
# 5. Session 狀態初始化
# ==============================
if "active_session" not in st.session_state:
  st.session_state.active_session = None

# ==============================
# 6. 側邊欄：起卦與參數輸入
# ==============================
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
    "選擇變爻位階",
    [1, 2, 3, 4, 5, 6],
    index=4,  # 第 5 爻
    format_func=lambda x: f"第 {x} 爻 ({['初爻','二爻','三爻','四爻','五爻','上爻'][x-1]}) 變動",
)

btn_new_divination = st.sidebar.button(
    "🔮 開始全新占卜並建立獨立檔案", type="primary"
)

# 觸發起卦：建立獨立會話檔案
if btn_new_divination:
  orig_hex = resolve_hexagram(upper_tri, lower_tri)
  new_up, new_low = calculate_changing_hexagram(
      upper_tri, lower_tri, changing_line
  )
  changed_hex = resolve_hexagram(new_up, new_low)

  # 生成獨立 Session ID (格式：年月日_卦名_爻變_時間)
  session_id = f"{input_date.strftime('%Y%m%d')}_{orig_hex['name']}_爻{changing_line}_{datetime.now().strftime('%H%M%S')}"

  # 產生第一輪解答
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
# 7. 主畫面渲染
# ==============================
st.title("☯️ 易經智慧占卜諮詢系統")

tab_chat, tab_hex_view, tab_files = st.tabs(
    ["💬 卦象專屬諮詢對話框", "📖 當前卦象結構說明", "📁 一卦一檔・歷史檔案庫"]
)

# 頁籤 1：互動對話與持續追問
with tab_chat:
  session = st.session_state.active_session

  if not session:
    st.info("👈 請在左側設定卦象與問題，並點選「開始全新占卜並建立獨立檔案」。")
  else:
    # 頂部狀態列
    st.markdown(
        f"""
        <div style="background-color:#F8FAFC; padding:12px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:15px;">
            <span class="hex-badge">檔案編號：{session['session_id']}</span>
            <span class="hex-badge">類別：{session['category']}</span>
            <span class="hex-badge">本卦：{session['original_hexagram']}</span>
            <span class="hex-badge">之卦：{session['changed_hexagram']} (第 {session['changing_line']} 爻變)</span>
            <span class="hex-badge">吉凶指數：{session['metrics']['final_luck']}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 顯示核心量化指標卡片
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

    # 顯示對話歷史清單 (歷程)
    st.subheader("📜 本次卦象諮詢歷程")
    for chat in session["chat_history"]:
      st.markdown(
          f"<div class='chat-user'>🙋 <b>問題（第 {chat['round']} 輪提問）</b>"
          f" [{chat['time']}]：<br>{chat['question']}</div>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<div class='chat-ai'>☯️ <b>易象解答與建議</b>：<br>{chat['answer']}</div>",
          unsafe_allow_html=True,
      )

    # 針對此卦象的「持續追問輸入框」
    st.markdown("### 💬 針對此卦象持續提問：")
    followup_q = st.text_input(
        "有任何疑問都可以繼續追問（例如：要換哪種類型的股票？若跌破支撐怎麼辦？）：",
        key="followup_input",
        placeholder="請輸入您的追問內容，按下按鈕送出...",
    )
    btn_followup = st.button("📨 送出追問解答", type="secondary")

    if btn_followup and followup_q:
      round_num = len(session["chat_history"]) + 1
      orig_hex = resolve_hexagram(session["upper_tri"], session["lower_tri"])
      new_up, new_low = calculate_changing_hexagram(
          session["upper_tri"], session["lower_tri"], session["changing_line"]
      )
      changed_hex = resolve_hexagram(new_up, new_low)

      # 產生追問解答
      followup_answer, _ = generate_intelligent_reply(
          question=followup_q,
          base_date=datetime.strptime(session["date"], "%Y-%m-%d").date(),
          orig_name=orig_hex["name"],
          changed_name=changed_hex["name"],
          changing_line=session["changing_line"],
          base_luck=orig_hex["base_luck"],
          round_count=round_num,
      )

      # 更新 session 並自動回寫檔案
      session["chat_history"].append({
          "round": round_num,
          "question": followup_q,
          "answer": followup_answer,
          "time": datetime.now().strftime("%H:%M:%S"),
      })
      st.session_state.active_session = session
      save_session_file(session)
      st.rerun()  # 立即重新整理畫面展示最新對話

# 頁籤 2：卦象細節
with tab_hex_view:
  if st.session_state.active_session:
    cur = st.session_state.active_session
    orig_info = resolve_hexagram(cur["upper_tri"], cur["lower_tri"])
    new_up, new_low = calculate_changing_hexagram(
        cur["upper_tri"], cur["lower_tri"], cur["changing_line"]
    )
    chg_info = resolve_hexagram(new_up, new_low)

    c_left, c_right = st.columns(2)
    with c_left:
      st.subheader(f"【本卦】{orig_info['symbol']} {orig_info['name']}")
      st.info(f"結構：上 {cur['upper_tri']} / 下 {cur['lower_tri']}")
      st.write(f"**大象義理**：{orig_info['judgment']}")
      st.write(f"**局勢象意**：{orig_info['finance_meaning']}")

    with c_right:
      st.subheader(
          f"【之卦（變卦）】{chg_info['symbol']} {chg_info['name']} (第"
          f" {cur['changing_line']} 爻變)"
      )
      st.info(f"結構：轉化為 上 {new_up} / 下 {new_low}")
      st.write(f"**大象義理**：{chg_info['judgment']}")
      st.write(f"**轉化象意**：{chg_info['finance_meaning']}")
  else:
    st.info("請先於側邊欄起卦以檢視卦象說明。")

# 頁籤 3：一卦一檔 歷史檔案庫
with tab_files:
  st.subheader("📁 獨立卦象檔案歷程管理（一卦一檔）")
  all_sessions = load_all_sessions()

  if not all_sessions:
    st.info("目前尚無獨立占卜檔案。")
  else:
    st.write(f"目前共儲存了 **{len(all_sessions)}** 個獨立卦象檔案：")

    # 歷史檔案下拉選擇器（可切換回溯任一次占卜）
    session_options = {
        f"{s['create_time']} ｜ {s['category']} ｜ {s['original_hexagram']} 變 {s['changed_hexagram']} ({s['session_id']})": s[
            "session_id"
        ]
        for s in all_sessions
    }
    selected_label = st.selectbox(
        "選擇要回溯查閱的卦象檔案：", list(session_options.keys())
    )
    chosen_id = session_options[selected_label]

    chosen_session = next(
        s for s in all_sessions if s["session_id"] == chosen_id
    )

    # 載入按鈕
    col_load, col_download = st.columns(2)
    with col_load:
      if st.button("🔄 載入此卦象至諮詢視窗繼續對話"):
        st.session_state.active_session = chosen_session
        st.success(f"已載入 {chosen_id}，請切換至「💬 卦象專屬諮詢對話框」查看！")

    with col_download:
      st.download_button(
          label="💾 下載此卦象專屬 JSON 檔案",
          data=json.dumps(chosen_session, ensure_ascii=False, indent=2),
          file_name=f"{chosen_id}.json",
          mime="application/json",
      )

    # 展示檔案內部 JSON 結構預覽
    st.markdown("#### 📄 檔案內容詳情檢視：")
    st.json(chosen_session)
