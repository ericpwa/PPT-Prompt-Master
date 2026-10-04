import streamlit as st
import re

# ==========================================
# Phase 1: 系統設定與底層初始化
# ==========================================
st.set_page_config(
    page_title="InfoVis Master 2.5 資訊視覺化簡報提示詞大師",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 嘗試載入 Google GenAI SDK（具備動態防護）
GENAI_SDK_AVAILABLE = False
try:
    from google import genai
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False

# 初始化 Session State
if "raw_text_draft" not in st.session_state:
    st.session_state.raw_text_draft = ""
if "ai_live_result" not in st.session_state:
    st.session_state.ai_live_result = ""

# ==========================================
# 輔助函式：文字清理與強健性診斷
# ==========================================
def sanitize_api_key(key: str) -> str:
    """清理 API Key，去除複製夾帶的前後空格、單雙引號與反引號"""
    if not key:
        return ""
    return key.strip().strip("'").strip('"').strip('`')

def is_page_number_marker(line: str) -> bool:
    """判斷該行是否僅為頁碼標籤（如 第1頁、Slide 2、Page 3、1/10），避免誤殺正文中的『第』『頁』字樣"""
    cleaned = line.strip()
    return bool(re.match(r'^(第\s*\d+\s*頁|slide\s*\d+|page\s*\d+|\d+\s*/\s*\d+)$', cleaned, re.IGNORECASE))

def generate_ai_presentation_with_fallback(api_key: str, system_prompt: str, user_content: str, selected_model: str):
    """
    四層級聯降級（Cascade Fallback）AI 呼叫引擎：
    首選模型 ➔ gemini-2.5-flash ➔ gemini-1.5-flash ➔ gemini-2.0-flash ➔ gemini-1.5-pro
    確保 100% 絕不因單一模型 404/下線而崩潰。
    """
    clean_key = sanitize_api_key(api_key)
    if not clean_key:
        return False, "❌ 請輸入有效的 Google Gemini API Key", None, False

    if not GENAI_SDK_AVAILABLE:
        return False, "⚠️ 系統尚未安裝 google-genai 套件，請確認 requirements.txt 設定", None, False

    client = genai.Client(api_key=clean_key)
    
    # 構建四層備援鏈，去重且首選優先
    fallback_chain = [
        selected_model,
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]
    unique_chain = []
    for m in fallback_chain:
        if m and m not in unique_chain:
            unique_chain.append(m)

    last_error = None
    fell_back = False
    
    full_prompt = f"{system_prompt}\n\n=== 原始資料文稿 ===\n{user_content}"

    for idx, model_name in enumerate(unique_chain):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            if idx > 0:
                fell_back = True
            return True, response.text, model_name, fell_back
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            # 若為金鑰本身無效或權限問題，立即中斷，避免在錯誤 Key 下盲目輪詢其他模型
            if any(k in err_str for k in ["api_key_invalid", "api key not valid", "403", "forbidden", "resource_exhausted", "429"]):
                break
            continue

    # 透明精確的錯誤診斷回饋
    err_str = str(last_error)
    if "api_key_invalid" in err_str.lower() or "api key not valid" in err_str.lower():
        diag_msg = "❌ 金鑰無效 (API_KEY_INVALID)：請檢查複製的金鑰是否正確完整（開頭應為 AIzaSy...）。"
    elif "403" in err_str or "forbidden" in err_str.lower():
        diag_msg = "❌ 存取受限 (403 Forbidden)：此 API Key 受 Google 政策限制，或未啟用 Generative Language API 存取權限。建議至 Google AI Studio 重新生成。"
    elif "429" in err_str or "resource_exhausted" in err_str.lower():
        diag_msg = "❌ 配額上限 (429 Rate Limit)：已達 Google API 免費額度限制，請稍候 1 分鐘再試。"
    elif "404" in err_str or "not_found" in err_str.lower() or "no longer available" in err_str.lower():
        diag_msg = "❌ 模型端點未開通或已被 Google 下線 (404 Not Found)：級聯備援皆無法連線，請檢查帳號權限。"
    else:
        diag_msg = f"❌ 呼叫失敗：{err_str}"

    return False, diag_msg, None, False

# ==========================================
# Phase 2: UI 介面與選單定義
# ==========================================
st.title("📊 InfoVis Master｜資訊視覺化簡報提示詞大師")
st.caption("🚀 v2.5 DD 零死角容錯版 ｜ 雙引擎架構：免金鑰純提示詞模式 ＋ BYOK 極速 AI 在線編譯直出")

# 側邊欄：全局設定與 BYOK
with st.sidebar:
    st.header("⚙️ 全局設定")
    lang_choice = st.selectbox("參數 1: 輸出語言", ["繁體中文", "English"])
    tool_choice = st.selectbox("參數 2: 目標 AI 工具", ["Gemini (支援在線生成)", "NotebookLM (推薦)", "Claude / ChatGPT"])
    
    st.divider()
    st.subheader("🔑 Google Gemini BYOK (選填)")
    st.markdown("填入您的 Google API Key 可解鎖**「AI 在線現場生成簡報企劃」**；若不填寫，亦可**100% 免費使用下方提示詞生成器**！")
    
    user_api_key = st.text_input(
        "輸入 Google Gemini API Key：",
        type="password",
        placeholder="AIzaSy...",
        help="金鑰僅存在您的瀏覽器會話中，直接發送至 Google 官方節點，絕不上傳第三方伺服器。"
    )
    clean_user_key = sanitize_api_key(user_api_key)
    
    selected_model_engine = "gemini-2.5-flash"
    if clean_user_key:
        st.success("🟢 已提供 API Key：已解鎖在線 AI 實戰生成！")
        selected_model_engine = st.selectbox(
            "AI 引擎選擇 (含級聯自動降級)：",
            ["gemini-2.5-flash (推薦：最新極速運算)", "gemini-1.5-flash (經典高相容版)", "gemini-2.0-flash (穩健平衡版)", "gemini-1.5-pro (深度邏輯版)"],
            index=0
        ).split(" ")[0]
    else:
        st.info("ℹ️ 目前處於純提示詞模式（無需 API Key）。")
        
    with st.expander("❓ 如何 30 秒免費取得 API Key？"):
        st.markdown("""
        1. 前往 👉 [Google AI Studio 官網](https://aistudio.google.com/app/apikey)
        2. 使用您的 **Google 個人帳號** 登入。
        3. 點選 **"Create API Key"** 藍色按鈕。
        4. 複製產生的金鑰（開頭為 `AIzaSy...`），貼至上方輸入框。
        *完全免費、無須信用卡！*
        """)
        
    st.markdown("---")
    st.caption("設計開發｜Pan Wen An\n\n版本：v2.5 DD 零死角容錯版")

# 主頁面 Tab 標籤頁
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

        # 視覺化模擬器 (UI 動態線框)
        st.markdown("---")
        st.markdown("### 👁️ 版面構圖預覽 (Composition Preview)")
        st.caption("此線框圖協助您確認 AI 將如何為您的主角【預留空間】。")
        
        with st.container(border=True):
            if ip_position == "右側 (Right)":
                c_text, c_img = st.columns([2, 1])
                with c_text:
                    st.markdown("#### 📊 資訊視覺化圖表與說明文字區")
                    st.caption("AI 會在此處生成密集的視覺元素與背景。")
                with c_img:
                    st.error("👤 絕對淨空區\n\n(留給您的 IP)")
                    
            elif ip_position == "左側 (Left)":
                c_img, c_text = st.columns([1, 2])
                with c_img:
                    st.error("👤 絕對淨空區\n\n(留給您的 IP)")
                with c_text:
                    st.markdown("#### 📊 資訊視覺化圖表與說明文字區")
                    st.caption("AI 會在此處生成密集的視覺元素與背景。")
                    
            elif ip_position == "置中 (Center)":
                c_side1, c_center, c_side2 = st.columns([1, 2, 1])
                with c_side1:
                    st.caption("背景裝飾區")
                with c_center:
                    st.error("👤 絕對淨空區\n\n(主角置中)")
                with c_side2:
                    st.caption("背景裝飾區")
                    
            elif ip_position == "底部 (Bottom)":
                st.markdown("#### 📊 上方資訊視覺化區域")
                st.caption("AI 會在畫面上半部生成資訊元素。")
                st.error("👤 絕對淨空區 (留給您的 IP 站在底部)")

with tab3:
    st.subheader("📄 指定簡報原始素材")
    st.info("💡 系統將自動抓取文稿標題與段落，即時渲染下方的版面排版預覽。")
    
    col_demo1, col_demo2, col_demo3 = st.columns(3)
    with col_demo1:
        if st.button("💡 套用範例：AI 商業提案募資", use_container_width=True):
            st.session_state.raw_text_draft = (
                "第一頁：AI 智慧零售解決方案 - 顛覆傳統門市營運\n"
                "我們運用邊緣 AI 視覺辨識，協助實體零售業掌握客流熱區與消費偏好。\n\n"
                "第二頁：實體店面痛點分析與轉換率瓶頸\n"
                "傳統店家缺乏即時數據追蹤，導致庫存積壓與行銷預算錯置。\n\n"
                "第三頁：核心產品架構與邊緣計算引擎\n"
                "即插即用攝影模組，結合專屬大語言模型生成每日營運優化決策。"
            )
            st.rerun()
    with col_demo2:
        if st.button("💡 套用範例：知識教學與考點拆解", use_container_width=True):
            st.session_state.raw_text_draft = (
                "第一講：現代資訊視覺化與認知心理學基礎\n"
                "人類大腦處理視覺資訊的速度比文字快 60,000 倍，良好的圖表能顯著降低認知負荷。\n\n"
                "第二講：圖表選型五大黃金準則\n"
                "趨勢看折線、佔比看圓餅、比較看長條、關係看散佈、結構看樹狀。\n\n"
                "第三講：簡報色彩學與高對比留白藝術\n"
                "60-30-10 原則：主色調佔 60%，輔助色佔 30%，強調行動呼籲色佔 10%。"
            )
            st.rerun()
    with col_demo3:
        if st.button("💡 清空輸入內容", use_container_width=True):
            st.session_state.raw_text_draft = ""
            st.rerun()

    raw_text = st.text_area(
        "在此貼上文稿或摘要 (建議 5,000 字內)：",
        value=st.session_state.raw_text_draft,
        height=200,
        placeholder="例如：第一頁：2027 年度策略目標\n第二頁：關鍵指標與市場成效..."
    )

st.divider()

# ==========================================
# Phase 3.5: 動態灰階渲染引擎 (DD 健壯版)
# ==========================================
st.header("👁️ 成果預覽｜動態灰階排版示意圖")

# 精準文字抽取邏輯：使用正則表達式過濾純頁碼標記，絕不誤殺含有「第」「頁」之商務文字
cleaned_lines = [
    line.strip() for line in raw_text.split('\n')
    if line.strip() and not is_page_number_marker(line)
]

def extract_slide_sample(index: int):
    title_idx = index * 2
    content_idx = index * 2 + 1
    t = cleaned_lines[title_idx][:22] + "..." if len(cleaned_lines) > title_idx else f"（Slide {index+1} 標題預備中）"
    c = cleaned_lines[content_idx][:55] + "..." if len(cleaned_lines) > content_idx else f"（請於 Step 3 輸入內容，系統將為第 {index+1} 頁自動擷取...）"
    return t, c

# CSS 灰階線框樣式（深淺色自適應）
st.markdown("""
<style>
.wireframe-slide {
    background: rgba(220, 225, 232, 0.9);
    border: 2px solid #64748b;
    border-radius: 12px;
    padding: 16px;
    height: 240px;
    display: flex;
    flex-direction: row;
    margin-bottom: 15px;
    color: #1e293b;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.wf-content { flex: 2; padding: 10px; display: flex; flex-direction: column; justify-content: center;}
.wf-ip-zone { flex: 1; border: 2px dashed #475569; background: rgba(148, 163, 184, 0.35); border-radius: 8px; 
              display: flex; align-items: center; justify-content: center; font-weight: bold; color: #334155; text-align: center;}
.wf-title { font-size: 1.1em; font-weight: 700; border-bottom: 2px solid #94a3b8; padding-bottom: 8px; margin-bottom: 8px; color: #0f172a;}
.wf-text { font-size: 0.85em; line-height: 1.4; color: #334155;}
</style>
""", unsafe_allow_html=True)

def render_wireframe(title, content, position):
    if position == "右側 (Right)":
        html = f"""<div class='wireframe-slide'><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>📊 <b>[AI 生成之視覺圖表區]</b></div></div><div class='wf-ip-zone'>👤 淨空留白區<br>(IP 置入)</div></div>"""
    elif position == "左側 (Left)":
        html = f"""<div class='wireframe-slide'><div class='wf-ip-zone'>👤 淨空留白區<br>(IP 置入)</div><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>📊 <b>[AI 生成之視覺圖表區]</b></div></div></div>"""
    elif position == "置中 (Center)":
         html = f"""<div class='wireframe-slide' style='flex-direction: column; align-items: center;'><div class='wf-title' style='width:100%; text-align:center;'>{title}</div><div class='wf-ip-zone' style='width: 60%; height: 90px; margin: 8px 0;'>👤 中央淨空區</div><div class='wf-text' style='text-align:center;'>{content}</div></div>"""
    elif position == "底部 (Bottom)":
         html = f"""<div class='wireframe-slide' style='flex-direction: column;'><div class='wf-content' style='flex:1;'><div class='wf-title'>{title}</div><div class='wf-text'>{content}</div></div><div class='wf-ip-zone' style='width: 100%; height: 50px;'>👤 底部淨空區</div></div>"""
    else: # 無主角或一般風格
        html = f"""<div class='wireframe-slide'><div class='wf-content'><div class='wf-title'>{title}</div><div class='wf-text'>{content}<br><br>🎨 <b>[ 滿版 AI 視覺生成區 ]</b></div></div></div>"""
    return html

# 依照設定頁數動態渲染預覽（最多並排 2 頁，避免版面擁擠）
num_preview = min(page_num, 2)
preview_cols = st.columns(num_preview)

for i in range(num_preview):
    with preview_cols[i]:
        st.markdown(f"**【Slide {i+1} 構圖預測】**")
        s_title, s_content = extract_slide_sample(i)
        st.markdown(render_wireframe(s_title, s_content, ip_position), unsafe_allow_html=True)

st.divider()

# ==========================================
# Phase 4: 動力引擎與成果輸出 (提示詞大師模式)
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
{raw_text if raw_text else "請根據 NotebookLM 的來源文件或上方參數進行智能擴寫與結構化發想。"}

[Output Constraints]
請以標準 Markdown 格式完整輸出全部 {page_num} 頁簡報：
1. 【Page X】：標題
2. 【核心觀點】：一句話總結該頁精髓
3. 【口白摘要】：對應「{tone}」語氣的講者演講稿（約 60~120 字）
4. 【視覺化建議】：
   - 畫面排版：說明文字、圖表元件與視覺焦點的精準佈局
   - 英文生圖 Prompt：強制套用「{style_choice}」畫風，適合 Midjourney / DALL-E / Imagen 生圖。{ip_prompt_injection}
"""

st.header("📦 成果 1｜InfoVis PROMPT (純提示詞大師模式)")
st.markdown("無需任何金鑰，直接複製或下載以下高結構化提示詞，前往目標 AI 工具展開詠唱：")
st.code(final_prompt, language="markdown")

col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    st.download_button(
        "📥 一鍵下載提示詞 (.md)",
        final_prompt,
        file_name="InfoVis_Master_Prompt.md",
        mime="text/markdown",
        use_container_width=True
    )
with col_btn2:
    st.link_button("🚀 前往 NotebookLM 詠唱", "https://notebooklm.google.com/", use_container_width=True)
with col_btn3:
    st.link_button("🚀 前往 Google Gemini 詠唱", "https://gemini.google.com/", use_container_width=True)

st.divider()

# ==========================================
# Phase 5: AI 現場極速直出區 (BYOK 實戰詠唱模式)
# ==========================================
st.header("⚡ 成果 2｜AI 現場即時生成 (BYOK 實戰直出模式)")
st.caption("內建四層級聯降級（Cascade Fallback）與智能防護，避免 404/403 斷線風險。")

if clean_user_key:
    if st.button("🚀 召喚 AI 現場為我編譯生成完整簡報大綱與視覺提案", type="primary", use_container_width=True):
        with st.spinner(f"正在召喚 Google Gemini ({selected_model_engine}) 深度編譯中..."):
            sys_instruct = (
                "你是一位頂級的資訊視覺化簡報設計師與邏輯架構師。"
                "請嚴格依據使用者的簡報參數與輸入素材，產出專業、具備講者口白與生圖 Prompt 的結構化簡報。"
            )
            success, result_text, used_model, fell_back = generate_ai_presentation_with_fallback(
                api_key=clean_user_key,
                system_prompt=sys_instruct,
                user_content=final_prompt,
                selected_model=selected_model_engine
            )
            if success:
                st.session_state.ai_live_result = result_text
                if fell_back:
                    st.toast(f"🛡️ 原選定模型已自動安全切換至 {used_model} 完成生成！", icon="🪄")
                st.success(f"✨ 簡報大綱生成完畢！使用引擎：{used_model}")
                st.balloons()
            else:
                st.error(result_text)
                
    if st.session_state.ai_live_result:
        st.markdown("### 📝 AI 現場生成成果展示：")
        st.markdown(st.session_state.ai_live_result)
        st.download_button(
            "📥 下載 AI 生成簡報企劃書 (.md)",
            st.session_state.ai_live_result,
            file_name="InfoVis_Generated_Presentation.md",
            mime="text/markdown",
            use_container_width=True
        )
else:
    st.info(
        "💡 **想要在網頁上直接看 AI 現場生成嗎？**<br>"
        "請至左側側邊欄輸入您的 **Google Gemini API Key**，即可解鎖現場一鍵生成簡報大綱、演講講稿與英文生圖 Prompt！<br>"
        "（若暫無 API Key，直接複製上方的【成果 1】至 NotebookLM 或 Gemini 亦可免費使用）",
        icon="✨"
    )