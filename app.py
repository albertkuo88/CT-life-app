import json
import os
from datetime import date, datetime
import streamlit as st

st.set_page_config(page_title="易經占卜預測程式", page_icon="☯️", layout="wide")
HISTORY_FILE = "iching_divination_history.json"

TRIGRAMS = {
    "乾 (天)": {"binary": "111", "symbol": "☰", "nature": "剛健強勢"},
    "兌 (澤)": {"binary": "110", "symbol": "☱", "nature": "喜悅和合"},
    "離 (火)": {"binary": "101", "symbol": "☲", "nature": "明理附著"},
    "震 (雷)": {"binary": "100", "symbol": "☳", "nature": "奮起震動"},
    "巽 (風)": {"binary": "011", "symbol": "☴", "nature": "順應滲透"},
    "坎 (水)": {"binary": "010", "symbol": "☵", "nature": "險陷考驗"},
    "艮 (山)": {"binary": "001", "symbol": "☶", "nature": "止息蓄勢"},
    "坤 (地)": {"binary": "000", "symbol": "☷", "nature": "柔順包容"},
}

HEXAGRAM_DATABASE = {
    ("乾 (天)", "乾 (天)"): {
        "name": "乾為天",
        "symbol": "䷀",
        "base_luck": 88,
        "judgment": "元亨利貞。天行健，君子以自強不息。",
        "trend": "飛龍在天，大勢盛旺，需防亢龍有悔。",
    },
    ("坤 (地)", "坤 (地)"): {
        "name": "坤為地",
        "symbol": "䷁",
        "base_luck": 75,
        "judgment": "元亨，利牝馬之貞。地勢坤，君子以厚德載物。",
        "trend": "以靜制動，後發先至，切忌盲目主動搶攻。",
    },
    ("坎 (水)", "震 (雷)"): {
        "name": "水雷屯",
        "symbol": "䷂",
        "base_luck": 45,
        "judgment": "元亨利貞，勿用有攸往，利建侯。",
        "trend": "創業維艱，萌芽受阻，宜積蓄實力建立體系。",
    },
    ("艮 (山)", "坎 (水)"): {
        "name": "山水蒙",
        "symbol": "䷃",
        "base_luck": 52,
        "judgment": "亨。匪我求童蒙，童蒙求我。初筮告，再三瀆，瀆則不告。",
        "trend": "局勢迷霧未散，宜拜師請益，切莫妄下斷言。",
    },
    ("坎 (水)", "乾 (天)"): {
        "name": "水天需",
        "symbol": "䷄",
        "base_luck": 70,
        "judgment": "有孚，光亨，貞吉。利涉大川。",
        "trend": "時機未完全成熟，需耐心等待時變，必有轉機。",
    },
    ("乾 (天)", "坎 (水)"): {
        "name": "天水訟",
        "symbol": "䷅",
        "base_luck": 32,
        "judgment": "有孚，窒惕，中吉，終凶。利見大人，不利涉大川。",
        "trend": "爭端多發，合夥分歧，宜退讓止爭防法律風險。",
    },
    ("坎 (水)", "坤 (地)"): {
        "name": "水地比",
        "symbol": "䷇",
        "base_luck": 82,
        "judgment": "吉。原筮元永貞，無咎。不寧方來，後夫凶。",
        "trend": "親和團結，外援充足，適合團隊合夥或建立盟友。",
    },
    ("離 (火)", "乾 (天)"): {
        "name": "火天大有",
        "symbol": "䷍",
        "base_luck": 92,
        "judgment": "元亨。順天休命，順應天時。",
        "trend": "資源豐盈，豐收吉兆，需謙沖自牧以保長久成果。",
    },
}


def get_hexagram_info(upper_tri: str, lower_tri: str):
  if (upper_tri, lower_tri) in HEXAGRAM_DATABASE:
    return HEXAGRAM_DATABASE[(upper_tri, lower_tri)]
  up_nat = TRIGRAMS[upper_tri]["nature"]
  low_nat = TRIGRAMS[lower_tri]["nature"]
  base_score = 60
  if "剛健" in up_nat or "明理" in up_nat:
    base_score += 15
  if "險陷" in low_nat or "險陷" in up_nat:
    base_score -= 20
  if "喜悅" in up_nat or "順應" in low_nat:
    base_score += 10
  base_score = max(25, min(95, base_score))
  clean_up = upper_tri.split()[0]
  clean_low = lower_tri.split()[0]
  return {
      "name": f"{clean_up}{clean_low}卦",
      "symbol": "䷆",
      "base_luck": base_score,
      "judgment": (
          f"上卦為{upper_tri}，下卦為{lower_tri}。象徵以「{low_nat}」為內核，外顯「{up_nat}」。"
      ),
      "trend": (
          f"內外交互動態顯示，當前正處於由『{clean_low}』轉向『{clean_up}』之過渡期。"
      ),
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


def generate_quantitative_metrics(
    base_luck: int, changing_line: int, category: str
):
  line_modifiers = {1: -4, 2: +8, 3: -8, 4: +3, 5: +10, 6: -7}
  final_luck = max(
      15, min(98, base_luck + line_modifiers.get(changing_line, 0))
  )
  metrics = {
      "final_luck": final_luck,
      "phase_1": max(10, min(95, final_luck - 12)),
      "phase_2": max(10, min(98, final_luck + 5)),
      "phase_3": max(10, min(95, final_luck)),
      "key_period": f"第 {changing_line * 2} ~ {changing_line * 3} 天",
      "action_ratio": f"{final_luck}% 積極推進 / {100 - final_luck}% 靜候防禦",
      "risk_level": (
          "低度風險 (可大膽執行)"
          if final_luck >= 75
          else (
              "中度風險 (需配套對策)"
              if final_luck >= 50
              else "高度風險 (暫緩盲動)"
          )
      ),
  }
  category_advice = {
      "事業 / 升遷發展": (
          f"關鍵突破指標：團隊溝通效率需達 80% 以上。主管認可度指數為"
          f" {final_luck}%。建議在未來 {changing_line * 4}"
          " 天內主動提交具體方案。"
      ),
      "財運 / 投資理財": (
          f"資金安全權重：建議保留 {100 - final_luck}%"
          f" 的流動現金。投資預期勝率評估為 {final_luck}%，切忌高槓桿操作。"
      ),
      "感情 / 婚姻緣分": (
          f"共識契合度指數：{final_luck}%。若遇分歧，宜在 {changing_line}"
          " 天內主動釋出善意，切忌冷戰超過 72 小時。"
      ),
      "學業 / 考試進修": (
          f"專注度轉化率預估：{final_luck}%。每日高效衝刺時間需達到"
          f" {max(3, changing_line + 1)} 小時，並加強弱科考古題覆盤。"
      ),
      "健康 / 身心調理": (
          f"體能復原指數：{final_luck}%。每日維持 7 小時休息，劇烈運動應調降強度"
          " 30%。"
      ),
      "合夥 / 簽約決策": (
          f"合作利益透明度：{final_luck}%。利益分配條款必須白紙黑字寫明，建議留存"
          " 15 天審閱緩衝期。"
      ),
  }
  metrics["specific_advice"] = category_advice.get(
      category, "依卦象數據順勢而為，把握核心節點。"
  )
  return metrics


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


st.title("☯️ 易經占卜預測程式")
st.sidebar.header("📝 占卜參數設定")
input_date = st.sidebar.date_input("占卜日期", value=date.today())
category = st.sidebar.selectbox(
    "選擇詢問事項類別",
    [
        "事業 / 升遷發展",
        "財運 / 投資理財",
        "感情 / 婚姻緣分",
        "學業 / 考試進修",
        "健康 / 身心調理",
        "合夥 / 簽約決策",
    ],
)
question_detail = st.sidebar.text_input(
    "詳細問題描述 (選填)", placeholder="例如：本季是否適合轉職？"
)
upper_tri_choice = st.sidebar.selectbox(
    "選擇上卦 (外卦)", list(TRIGRAMS.keys()), index=0
)
lower_tri_choice = st.sidebar.selectbox(
    "選擇下卦 (內卦)", list(TRIGRAMS.keys()), index=1
)
changing_line_choice = st.sidebar.selectbox(
    "選擇第幾爻為變爻",
    [1, 2, 3, 4, 5, 6],
    index=4,
    format_func=lambda x: f"第 {x} 爻 ({['初爻','二爻','三爻','四爻','五爻','上爻'][x-1]}) 變動",
)
btn_predict = st.sidebar.button("🔮 進行卦象推算與預測", type="primary")

original_info = get_hexagram_info(upper_tri_choice, lower_tri_choice)
new_up, new_low = calculate_changing_hexagram(
    upper_tri_choice, lower_tri_choice, changing_line_choice
)
changed_info = get_hexagram_info(new_up, new_low)
metrics = generate_quantitative_metrics(
    original_info["base_luck"], changing_line_choice, category
)

if btn_predict:
  save_history({
      "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "date": str(input_date),
      "category": category,
      "question": question_detail if question_detail else "無額外描述",
      "original_hexagram": original_info["name"],
      "changing_line": f"第 {changing_line_choice} 爻",
      "changed_hexagram": changed_info["name"],
      "luck_score": f"{metrics['final_luck']}%",
      "risk_level": metrics["risk_level"],
  })
  st.success("✅ 占卜完成！已自動儲存至歷史歷程。")

tab_result, tab_history = st.tabs(
    ["📊 卦象推算與量化預測結果", "📜 歷史詢問歷程庫"]
)
with tab_result:
  col1, col2 = st.columns(2)
  with col1:
    st.subheader("【 本卦 (當前處境) 】")
    st.markdown(f"### {original_info['symbol']} {original_info['name']}")
    st.info(f"**上卦**：{upper_tri_choice} | **下卦**：{lower_tri_choice}")
    st.write(f"**卦辭釋義**：{original_info['judgment']}")
    st.write(f"**局勢總評**：{original_info['trend']}")
  with col2:
    st.subheader(f"【 之卦 (變卦後走向 - 第 {changing_line_choice} 爻變) 】")
    st.markdown(f"### {changed_info['symbol']} {changed_info['name']}")
    st.info(f"**轉變為**：上 {new_up} | 下 {new_low}")
    st.write(f"**變卦釋義**：{changed_info['judgment']}")
    st.write(f"**未來演變**：{changed_info['trend']}")
  st.divider()
  st.subheader("📈 明確量化預測指標 (非模糊語義)")
  m1, m2, m3, m4 = st.columns(4)
  m1.metric("綜合勝率／吉凶指數", f"{metrics['final_luck']} %")
  m2.metric("風險評級", metrics["risk_level"])
  m3.metric("近期突破機率 (1~3週)", f"{metrics['phase_1']} %")
  m4.metric("中遠期成就度 (3~6月)", f"{metrics['phase_3']} %")
  st.progress(metrics["final_luck"] / 100)
  st.caption(
      f"📊 **決策行動配比建議**：{metrics['action_ratio']}｜**關鍵應驗窗口期**：{metrics['key_period']}"
  )
  st.warning(
      f"📌 **【{category}】實質方向指導**：\n\n{metrics['specific_advice']}"
  )

with tab_history:
  st.subheader("📋 歷次占卜歷史歷程與趨勢比對")
  history_data = load_history()
  if not history_data:
    st.info("尚無歷史紀錄，請點選「進行卦象推算與預測」產出首筆記錄。")
  else:
    filter_cat = st.selectbox(
        "🔍 篩選相同詢問事項類別查看歷程：",
        ["全部顯示"]
        + [
            "事業 / 升遷發展",
            "財運 / 投資理財",
            "感情 / 婚姻緣分",
            "學業 / 考試進修",
            "健康 / 身心調理",
            "合夥 / 簽約決策",
        ],
    )
    filtered = [
        item
        for item in history_data
        if filter_cat == "全部顯示" or item.get("category") == filter_cat
    ]
    st.caption(f"共檢索出 {len(filtered)} 筆歷程紀錄：")
    st.dataframe(filtered, use_container_width=True)
    st.download_button(
        "💾 下載歷程資料備份 (JSON)",
        json.dumps(filtered, ensure_ascii=False, indent=2),
        "iching_history.json",
        "application/json",
    )
