import streamlit as st
import re

# ==========================================
# Phase 1: 系統設定與底層初始化
# ==========================================
st.set_page_config(page_title="InfoVis Master", page_icon="📊", layout="wide")

# ==========================================
# Phase 2: UI 介面與選單定義
# ==========================================
st.title("📊 InfoVis Master｜資訊視覺化簡報提示詞大師")
st.markdown("請依序設定您的簡報視覺化參數")

with st.sidebar:
    st.header("⚙️ 全局設定")
    lang_choice = st.selectbox("參數 1: 輸出語言", ["繁體中文", "English"])
    tool_choice = st.selectbox("參數 2: 目標 AI 工具", ["NotebookLM (推薦)", "Gemini"])
    st.markdown("---")
    st.caption("設計開發｜Pan Wen An\n\n版本：v2.4 單頁灰階預覽版")

tab1, tab2, tab3 = st.tabs(["📝 Step 1: 內容與受眾設定", "🎨 Step 2: 視覺與版面設定", "📄 Step 3: 原始素材輸入"])

with tab1:
    st.subheader("📊 基礎屬性與核心策略")
    col1, col2 = st.columns(2)
    with col1:
        page_num = st.number_input("參數 3: 預計頁數", 1, 50, 5)
        time_min = st.number_input("參數 4: 報告時間 (分)", 1, 120, 10)
        roles = ["教授/講師", "行銷總監", "專案經理", "產品經理", "技術主管", "社群創作者/自由工作者", "專業顧問", "資深產業專家", "導覽員/解說員", "自訂角色", "不需要角色"]
        role = st.selectbox("參數 5: 簡報角色 (我是誰)", roles)
        scenes = ["線上遠距教學", "線上視訊會議", "內部的工作進度匯報", "內部的提案會議", "對客戶的提案會議", "大型研討會", "學校課堂/期末報告", "電梯簡報", "自訂設定", "不需要設定"]
        scene = st.selectbox("參數 6: 發表場景", scenes)
        audiences = ["零基礎初學者", "企業高階主管", "專業技術人員", "一般大眾", "學生與學術人員", "潛在客戶與決策者", "內部團隊與主管", "一般大眾與消費者", "自訂設定", "不需要設定"]
        audience = st.selectbox("參數 7: 目標受眾", audiences)
    with col2:
        purposes = ["知識教學/拆解考點", "商業提案/募資", "產品發布", "個案分析", "教育與員工培訓", "專案與進度報告", "數據與成效分析", "行銷企劃與發想", "自訂簡報目的"]
        goal = st.selectbox("參數 10: 簡報目的", purposes)
        tones = ["專業嚴謹且重視證據", "嚴謹客觀且數據驅動", "充滿熱情、激勵性、號召力", "專業自信且具說服力", "輕鬆幽默且平易近人", "溫暖感性、具同理心、啟發性", "自訂設定", "不需要設定"]
        tone = st.selectbox("參數 8: 講者人設和語氣", tones)
        ctas = ["引起興趣/刺激意願", "無(純知識分享)", "批准預算/啟動專案", "改變觀念或行為", "了解痛點並促成合作", "引導參與活動/報名課程", "購買產品或服務", "訂閱電子報/加入粉絲團/加入會員", "自訂設定", "不需要設定"]
        cta = st.selectbox("參數 9: 行動呼籲 (CTA)", ctas)

with tab2:
    st.subheader("🎯 簡報大綱與視覺風格")
    outlines = ["總分總架構(適合教學)", "SCQA 金字塔(適合提案)", "NSDB：N(需求)→S(解法)→D(差異)→B(效益)", "黃金圈理論(Why-How-What)", "起承轉合(故事法)", "時間軸演進", "結論與數據先行", "自訂大綱邏輯"]
    outline = st.selectbox("參數 11: 簡報大綱邏輯", outlines)
    styles = [
        "2.5D 等距視角(Isometric)", "極簡扁平化(Minimalist Flat)", "高階寫實攝影(High-end realistic)",
        "手繪日記風格+主角", "專業企業商務風格", "溫馨插畫風格", 
        "2.5D 等距視角風格+主角", "3D 奶油 UI 科技風格", "雜誌編輯風格", 
        "高對比度極簡風格", "扁平化插畫風格", "北歐簡約插畫風格", 
        "漸層玻璃擬態風格", "教育型遊戲 UI 風格+主角", "自訂視覺風格"
    ]
    style_choice = st.selectbox("參數 12: 選擇視覺語彙", styles)

    ip_desc = ""
    ip_position_logic = ""
    ip_position = "無"
    if "+主角" in style_choice:
        st.warning("💡 您選擇了「+主角」風格。請設定您的 IP 資訊與【預計放置的版面位置】。")
        col_ip1, col_ip2 = st.columns(2)
        with col_ip1:
            ip_desc = st.text_input("主角/IP 特徵描述：", "一位形象專業的簡報者")
        with col_ip2:
            ip_position = st.selectbox("主角將放置於版面：", ["右側 (Right)", "左側 (Left)", "置中 (Center)", "底部 (Bottom)"])
        
        position_prompts = {
            "右側 (Right)": "Rule of thirds composition, heavy elements on the LEFT, absolute clear solid negative space on the RIGHT for character insertion",
            "左側 (Left)": "Rule of thirds composition, heavy elements on the RIGHT, absolute clear solid negative space on the LEFT for character insertion",
            "置中 (Center)": "Symmetrical composition, clear negative space in the absolute CENTER, surrounding elements framing the edges",
            "底部 (Bottom)": "High angle composition, clear negative space at the BOTTOM for character insertion"
        }
        ip_position_logic = position_prompts.get(ip_position, "")

with tab3:
    st.subheader("📄 指定簡報原始素材")
    st.info("⚠️ 系統將自動抓取下方文稿的前幾行，作為最終輸出的灰階示意圖內容。")
    raw_text = st.text_area("在此貼上文稿或摘要 (建議 5,000 字內)：", height=200)

st.divider()

# ==========================================
# Phase 3.5: 動態灰階渲染引擎 (單頁示範版)
# ==========================================
st.header("👁️ 成果預覽｜動態灰階排版示意圖")

# 文本萃取邏輯 (精簡為只抽取首頁)
lines = [line.strip() for line in raw_text.split('\n') if line.strip() and "第" not in line and "頁" not in line]
slide_1_title = lines[0][:20] + "..." if len(lines) > 0 else "（請至 Step 3 輸入標題）"
slide_1_content = lines[1][:50] + "..." if len(lines) > 1 else "（請至 Step 3 輸入內文素材，系統將自動擷取...）"

# CSS 灰階線框樣式
st.markdown("""
<style>
.wireframe-slide {
    background-color: #e0e0e0; border: 2px solid #999; border-radius: 8px; padding: 20px;
    height: 250px; display: flex; flex-direction: row; margin-bottom: 20px; color: #333;
}
.wf-content { flex: 2; padding: 10px; display: flex; flex-direction: column; justify-content: center;}
.wf-ip-zone { flex: 1; border: 2px dashed #777; background-color: #ccc; border-radius: 8px; 
              display: flex; align-items: center; justify-content: center; font-weight: bold; color: #555; text-align: center;}
.wf-title { font-size: 1.2em; font-weight: bold; border-bottom: 2px solid #999; padding-bottom: 10px; margin-bottom: 10px;}
.wf-text { font-size: 0.9em; line-height: 1.5; color: #555;}
</style>
""", unsafe_allow_html=True)

def render_wireframe(title, content, position):
    if position == "右側 (Right)":
        html = f"""<div class='wireframe-slide'><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>[📊 AI 生成之視覺元素]</div></div><div class='wf-ip-zone'>👤 淨空留白區<br>(IP 置入)</div></div>"""
    elif position == "左側 (Left)":
        html = f"""<div class='wireframe-slide'><div class='wf-ip-zone'>👤 淨空留白區<br>(IP 置入)</div><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>[📊 AI 生成之視覺元素]</div></div></div>"""
    elif position == "置中 (Center)":
         html = f"""<div class='wireframe-slide' style='flex-direction: column; align-items: center;'><div class='wf-title' style='width:100%; text-align:center;'>{title}</div><div class='wf-ip-zone' style='width: 50%; height: 100px; margin: 10px 0;'>👤 中央淨空區</div><div class='wf-text' style='text-align:center;'>{content}</div></div>"""
    elif position == "底部 (Bottom)":
         html = f"""<div class='wireframe-slide' style='flex-direction: column;'><div class='wf-content' style='flex:1;'><div class='wf-title'>{title}</div><div class='wf-text'>{content}</div></div><div class='wf-ip-zone' style='width: 100%; height: 60px;'>👤 底部淨空區</div></div>"""
    else: # 無主角或一般風格
        html = f"""<div class='wireframe-slide'><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>[ 滿版 AI 視覺生成區 ]</div></div></div>"""
    return html

# 渲染唯一 1 頁的示意圖
st.markdown("**【首頁構圖預測】**")
st.markdown(render_wireframe(slide_1_title, slide_1_content, ip_position), unsafe_allow_html=True)

st.divider()

# ==========================================
# Phase 4: 動力引擎與成果區塊
# ==========================================
ip_prompt_injection = f"\n   - **[構圖嚴格約束]**: {ip_position_logic}. 確保此空間完全淨空，並在畫面上與未來的「{ip_desc}」風格匹配。" if "+主角" in style_choice else ""

final_prompt = f"""[System Role]
你現在是一位頂級的「資訊視覺化簡報設計師」與「邏輯架構師」。

[Briefing Parameters]
- 語言: {lang_choice} | 頁數: {page_num} | 時間: {time_min}min
- 角色: {role} | 受眾: {audience} | 場景: {scene}
- 語氣: {tone} | 目的: {goal} | CTA: {cta}
- 大綱邏輯: {outline}
- 視覺風格: {style_choice}

[Source Content]
{raw_text if raw_text else "請根據 NotebookLM 的來源文件進行檢索。"}

[Output Constraints]
請以 Markdown 格式輸出每頁簡報：
1. 【Page X】：標題
2. 【核心觀點】：一句話總結
3. 【口白摘要】：對應「{tone}」語氣的演講稿
4. 【視覺化建議】：
   - 畫面排版（說明文字與圖表的配置）
   - 英文生圖 Prompt：強制套用「{style_choice}」畫風。{ip_prompt_injection}
"""

st.header("📦 成果｜InfoVis PROMPT")
st.code(final_prompt, language="markdown")

col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    st.download_button("📥 下載 .md", final_prompt, "InfoVis_Prompt.md", "text/markdown", use_container_width=True)
with col_btn2:
    st.link_button("🚀 前往 NotebookLM", "https://notebooklm.google.com/", use_container_width=True)
with col_btn3:
    st.link_button("🚀 前往 Gemini", "https://gemini.google.com/", use_container_width=True)