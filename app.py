import json
import os
import re
from datetime import date, datetime, timedelta
import streamlit as st

# ==============================
# 1. 頁面配置
# ==============================
st.set_page_config(
    page_title="易經智慧占卜決策系統",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)

HISTORY_FILE = "iching_divination_history.json"

# ==============================
# 2. 八卦與六十四卦核心庫 (含完整象意)
# ==============================
TRIGRAMS = {
    "坤 (地)": {
        "binary": "000",
        "symbol": "☷",
        "nature": "柔順包容、厚德載物、順勢而為",
        "element": "土",
    },
    "艮 (山)": {
        "binary": "001",
        "symbol": "☶",
        "nature": "止步蓄勢、防守阻礙、見險即止",
        "element": "土",
    },
    "坎 (水)": {
        "binary": "010",
        "symbol": "☵",
        "nature": "重險考驗、資金暗流、流動轉折",
        "element": "水",
    },
    "巽 (風)": {
        "binary": "011",
        "symbol": "☴",
        "nature": "順應滲透、漸進傳遞、隨風而動",
        "element": "木",
    },
    "震 (雷)": {
        "binary": "100",
        "symbol": "☳",
        "nature": "奮起震動、短線爆發、突發反彈",
        "element": "木",
    },
    "離 (火)": {
        "binary": "101",
        "symbol": "☲",
        "nature": "光明附著、行情過熱、虛火明晰",
        "element": "火",
    },
    "兌 (澤)": {
        "binary": "110",
        "symbol": "☱",
        "nature": "喜悅和合、多方獲利、樂極生悲",
        "element": "金",
    },
    "乾 (天)": {
        "binary": "111",
        "symbol": "☰",
        "nature": "剛健強勢、龍頭主升、自強不息",
        "element": "金",
    },
}

# 64卦名與吉凶象意庫
HEXAGRAM_MAPPING = {
    ("坤 (地)", "艮 (山)"): {
        "name": "地山謙",
        "symbol": "䷎",
        "base_luck": 80,
        "judgment": "亨，君子有終。地中有山，內高而外下，謙遜退讓吉。",
        "finance_meaning": (
            "行情築底蓄勢階段，表面平淡但底部扎實，切忌追高，宜逢低分批佈局。"
        ),
    },
    ("坤 (地)", "坎 (水)"): {
        "name": "地水師",
        "symbol": "䷆",
        "base_luck": 62,
        "judgment": "貞，丈人吉，無咎。地中有水，師出有名，如軍隊紀律嚴明。",
        "finance_meaning": (
            "局勢如行軍作戰，不可盲目單打獨鬥，須有嚴格停損停利機制，重視資金調度與風控。"
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
# 3. 智慧化問題意圖識別與推算引擎
# ==============================
def resolve_hexagram(upper_tri: str, lower_tri: str):
  """取得卦名與內涵"""
  if (upper_tri, lower_tri) in HEXAGRAM_MAPPING:
    return HEXAGRAM_MAPPING[(upper_tri, lower_tri)]

  up_name = upper_tri.split()[0]
  low_name = lower_tri.split()[0]
  return {
      "name": f"{up_name}{low_name}卦",
      "symbol": "䷍",
      "base_luck": 60,
      "judgment": (
          f"外卦為{upper_tri}，內卦為{lower_tri}。象徵內在以「{TRIGRAMS[lower_tri]['nature']}」為主，外在顯現「{TRIGRAMS[upper_tri]['nature']}」。"
      ),
      "finance_meaning": (
          "處於內外力量拉鋸的轉折期，需依據變爻強弱動態決定進退。"
      ),
  }


def calculate_changing_hexagram(
    upper_tri: str, lower_tri: str, changing_line: int
):
  """計算變卦（之卦）"""
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


def analyze_intelligent_response(
    query_text: str,
    base_date: date,
    orig_name: str,
    changed_name: str,
    changing_line: int,
    base_luck: int,
):
  """核心智慧大腦：剖析使用者輸入問題、計算確切西元日期、給予明確操作策略"""
  query_lower = query_text.lower()

  # 1. 計算具體時程節點（公曆年月日）
  # 爻位時間法則：初爻近、上爻遠；每爻對應特定數理週期
  t1_days = changing_line * 2  # 第一變動反應期
  t2_days = changing_line * 5 + 3  # 回升波段啟動日
  t3_days = changing_line * 8 + 7  # 波段高點或終結日

  date_t1 = base_date + timedelta(days=t1_days)
  date_t2 = base_date + timedelta(days=t2_days)
  date_t3 = base_date + timedelta(days=t3_days)

  # 2. 爻變吉凶補正 (以五爻為例，五爻為尊位，動則大變)
  line_weights = {1: -5, 2: +6, 3: -8, 4: +4, 5: +10, 6: -7}
  final_luck = max(20, min(96, base_luck + line_weights.get(changing_line, 0)))

  # 3. 意圖檢測：股票、回升、賣出/出清
  is_stock_query = any(
      k in query_lower for k in ["股", "台股", "股票", "指數", "大盤", "標的"]
  )
  is_rebound_query = any(
      k in query_lower for k in ["回升", "反彈", "解套", "上漲", "漲", "底"]
  )
  is_sell_query = any(
      k in query_lower
      for k in ["賣", "出清", "脫手", "砍", "停損", "停利", "逃"]
  )

  # 針對「地山謙 變 地水師 (第5爻變)」專屬易理邏輯
  # 謙卦五爻：「不富以其鄰，利用侵伐，無不利。」
  special_line_insight = ""
  if (
      "謙" in orig_name
      and "師" in changed_name
      and changing_line == 5
  ):
    special_line_insight = (
        "【爻辭特論】：占得地山謙卦第五爻變為地水師。五爻居尊位，爻辭曰『利用侵伐，無不利』。"
        "這表示面對當前持股，不可消極被動死守！在市場中必須像將帥統軍一樣，採取果斷行軍之法，嚴格執行資金控管。"
    )

  # 4. 生成明確答覆與量化操作
  direct_answers = []

  # 問題回覆 A：何時會回升？（明確日期）
  if is_rebound_query or is_stock_query:
    direct_answers.append(
        f"🎯 **【關於何時回升】**：\n"
        f"- **短線止跌震盪打底期**：約在 **{date_t1.strftime('%Y 年 %m 月 %d 日')}** 前後出現訊號，此時量能萎縮但賣壓減輕。\n"
        f"- **波段實質回升啟動日**：推測在 **{date_t2.strftime('%Y 年 %m 月 %d 日')}**（第 {t2_days} 天附近）。卦象轉入「師卦」主動出擊之象，此時法人或主力籌碼容易回補，帶動股價展開顯著反彈。\n"
        f"- **反彈波段頂部目標區**：預計落在 **{date_t3.strftime('%Y 年 %m 月 %d 日')}** 左右，此為波段滿足點。"
    )

  # 問題回覆 B：要不要最近賣掉出清？
  if is_sell_query or is_stock_query:
    if final_luck >= 70:
      sell_advice = (
          f"🛑 **【要不要最近賣掉出清？】—— 不建議此時全數賤賣出清！**\n"
          f"- **核心策略**：謙卦下為山（止）、變師卦水流動。目前是**「底部震盪、洗盤過濾籌碼」**階段，若現在恐慌殺低出清，容易賣在相對低檔阿呆谷。\n"
          f"- **明確行動建議**：\n"
          f"  1. **當前持有策略**：維持現有持股，忍受短期 {t1_days} 天內的微幅震盪。\n"
          f"  2. **分批出場時機**：等到 **{date_t2.strftime('%m 月 %d 日')}** 回升波發動後，於股價衝向 **{date_t3.strftime('%m 月 %d 日')}** 區間時，採「階梯式減碼」賣出：\n"
          f"     - 反彈至第一壓力區：出清 **30%** 弱勢股。\n"
          f"     - 反彈至主要均線區：出清 **40%** 鎖定資金。\n"
          f"     - 保留 **30%** 基本持股觀望後續攻勢。"
      )
    else:
      sell_advice = (
          f"⚠️ **【要不要最近賣掉出清？】—— 建議分批出清，不可留戀！**\n"
          f"- **核心策略**：盤勢動能衰退，建議於未來 3~5 天內趁小反彈出清至少 60% 部位，換取現金防守。"
      )
    direct_answers.append(sell_advice)

  # 若非特定股市關鍵字，走全方位通用智慧推論
  if not direct_answers:
    direct_answers.append(
        f"🎯 **【針對您的提問核心研判】**：\n"
        f"- 根據您詢問的內容，當前所處局勢正由「{orig_name}」過渡轉化為「{changed_name}」。\n"
        f"- **關鍵轉折時機點**：預計在 **{date_t2.strftime('%Y 年 %m 月 %d 日')}** 會迎來事情的關鍵轉變。\n"
        f"- 執行力道應維持 {final_luck}% 之信心指數，依據時程節點有序推進。"
    )

  return {
      "direct_answers": "\n\n".join(direct_answers),
      "special_line_insight": special_line_insight,
      "date_t1": date_t1.strftime("%Y-%m-%d"),
      "date_t2": date_t2.strftime("%Y-%m-%d"),
      "date_t3": date_t3.strftime("%Y-%m-%d"),
      "final_luck": final_luck,
      "t2_days": t2_days,
  }


# ==============================
# 4. 歷史紀錄存取模組
# ==============================
def load_history():
  if os.path.exists(HISTORY_FILE):
    try:
      with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_history(record):
  history = load_history()
  history.insert(0, record)
  try:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
      json.dump(history, f, ensure_ascii=False, indent=2)
  except Exception:
    pass


# ==============================
# 5. 主介面渲染
# ==============================
st.title("☯️ 易經智慧占卜預測系統 (精確回答版)")
st.caption(
    "已整合自然語意意圖解析・直接推算公曆具體轉折日期・提供明確量化操作指引"
)

# 側邊欄：使用者輸入
st.sidebar.header("📝 占卜參數與問題輸入")
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

# 自由輸入問題（智慧回答的核心）
question_input = st.sidebar.text_area(
    "👉 請詳細輸入您想問的事情：",
    value="台灣股票股價的情況 何時會回昇 要不要最近賣掉出清 何時股價會回昇 推測出詳細的日期",
    height=110,
    help="系統會自動辨識您問的標的、是否該賣出、何時回升等核心問題並具體解答！",
)

st.sidebar.subheader("爻象輸入")
upper_tri = st.sidebar.selectbox(
    "選擇上卦 (外卦)",
    list(TRIGRAMS.keys()),
    index=0,  # 預設 坤(地)
)
lower_tri = st.sidebar.selectbox(
    "選擇下卦 (內卦)",
    list(TRIGRAMS.keys()),
    index=1,  # 預設 艮(山) -> 地山謙
)
changing_line = st.sidebar.selectbox(
    "選擇變爻位階",,
    index=4,  # 預設第 5 爻
    format_func=lambda x: f"第 {x} 爻 ({['初爻','二爻','三爻','四爻','五爻','上爻'][x-1]}) 變動",
)

btn_submit = st.sidebar.button("🔮 進行智慧推算與精準解答", type="primary")

# 運算主體
orig_hex = resolve_hexagram(upper_tri, lower_tri)
new_up, new_low = calculate_changing_hexagram(upper_tri, lower_tri, changing_line)
changed_hex = resolve_hexagram(new_up, new_low)

intelligence = analyze_intelligent_response(
    query_text=question_input,
    base_date=input_date,
    orig_name=orig_hex["name"],
    changed_name=changed_hex["name"],
    changing_line=changing_line,
    base_luck=orig_hex["base_luck"],
)

# 儲存至歷程
if btn_submit:
  save_history({
      "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "date": str(input_date),
      "category": category,
      "question": question_input,
      "original_hexagram": f"{orig_hex['name']} ({upper_tri} / {lower_tri})",
      "changing_line": f"第 {changing_line} 爻",
      "changed_hexagram": f"{changed_hex['name']} ({new_up} / {new_low})",
      "luck_score": f"{intelligence['final_luck']}%",
      "key_turning_date": intelligence["date_t2"],
  })
  st.success("✅ 已針對問題生成具體日期解答，並自動歸檔至專屬歷程！")

# 頁籤排版
tab_direct_ans, tab_hex_detail, tab_history = st.tabs(
    ["💡 問題直接解答 (含具體日期)", "📖 卦象卦義與爻辭剖析", "📜 歷史詢問歷程庫"]
)

with tab_direct_ans:
  # 最核心：正面回答使用者的問題
  st.subheader("📌 針對您所詢問問題的精確回覆與量化決策")
  st.markdown(
      f"**詢問事項**：`{category}` ｜ **占卜基準日**：`{input_date.strftime('%Y-%m-%d')}`"
  )
  st.info(f"**您的具體問題**：{question_input}")

  # 顯示直接回答內容
  st.markdown(intelligence["direct_answers"])

  if intelligence["special_line_insight"]:
    st.warning(intelligence["special_line_insight"])

  st.divider()

  # 具體量化儀表板
  st.subheader("📅 關鍵時程與操作量化指標")
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("綜合勝率 / 轉機指數", f"{intelligence['final_luck']} %")
  c2.metric("短期止跌信號日", intelligence["date_t1"])
  c3.metric(
      "波段回升啟動日 (重要)",
      intelligence["date_t2"],
      f"+{intelligence['t2_days']} 天",
  )
  c4.metric("波段滿足高點日", intelligence["date_t3"])

  st.progress(intelligence["final_luck"] / 100)

with tab_hex_detail:
  st.subheader("☯️ 本卦與之卦（變卦）易象解析")
  col_orig, col_chg = st.columns(2)

  with col_orig:
    st.markdown(f"### 本卦：{orig_hex['symbol']} {orig_hex['name']}")
    st.write(f"**組成**：上卦 {upper_tri} / 下卦 {lower_tri}")
    st.write(f"**大象義理**：{orig_hex['judgment']}")
    st.write(f"**市場象意**：{orig_hex['finance_meaning']}")

  with col_chg:
    st.markdown(
        f"### 之卦（第 {changing_line} 爻變）：{changed_hex['symbol']} {changed_hex['name']}"
    )
    st.write(f"**組成**：轉化為 上卦 {new_up} / 下卦 {new_low}")
    st.write(f"**大象義理**：{changed_hex['judgment']}")
    st.write(f"**演變象意**：{changed_hex['finance_meaning']}")

with tab_history:
  st.subheader("📋 相同事項歷史歷程回溯")
  history_list = load_history()

  if not history_list:
    st.info("尚無歷史歷程，請點選左側按鈕開始首筆預測記錄。")
  else:
    filter_type = st.selectbox(
        "🔍 篩選相同類別查看歷史演變：",
        ["全部顯示"]
        + list(set([item.get("category", "") for item in history_list])),
    )

    filtered_data = [
        item
        for item in history_list
        if filter_type == "全部顯示" or item.get("category") == filter_type
    ]

    st.caption(f"共過濾出 {len(filtered_data)} 筆相關紀錄：")
    st.dataframe(filtered_data, use_container_width=True)

    st.download_button(
        "💾 下載歷史備份 (JSON)",
        json.dumps(filtered_data, ensure_ascii=False, indent=2),
        "iching_history.json",
        "application/json",
    )
