"""
AI POD Web Interface - Professional Version with Authentication
ENTER submits, Beautiful bullet points, ChatGPT-style UI
"""

import streamlit as st
import os
import sys
import time
from datetime import datetime
import hashlib
import re
import streamlit.components.v1 as components
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from config and query system
try:
    from query_system import AIPodQuerySystem, detect_language
    from config import AIPodConfig
    from auth import AuthManager, init_session_state, login_required, logout, show_user_profile, check_permission
    AI_POD_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ Failed to import: {e}")
    AI_POD_AVAILABLE = False

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title=f"AI POD - {AIPodConfig.COMPANY_NAME}",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# Initialize Authentication
# --------------------------------------------------
init_session_state()

# --------------------------------------------------
# Initialize Session State
# --------------------------------------------------
if "question" not in st.session_state:
    st.session_state.question = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = hashlib.md5(
        str(datetime.now()).encode()
    ).hexdigest()[:8]

# --------------------------------------------------
# Professional Answer Formatter - REAL HTML BULLETS
# --------------------------------------------------
def format_answer(answer_text: str) -> str:
    """Convert answer into clean HTML bullet format - Professional version"""
    
    lines = answer_text.split("\n")
    html_output = ""
    bullet_mode = False
    in_source = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Handle source citation
        if line.startswith('[From:') or line.startswith('From:'):
            in_source = True
            if bullet_mode:
                html_output += "</ul>"
                bullet_mode = False
            html_output += f'<div class="source-citation">{line}</div>'
            continue
        
        # Handle numbered list (1., 2., etc)
        if re.match(r"^\d+[\.\)]", line):
            if not bullet_mode:
                html_output += "<ul class='bullet-list'>"
                bullet_mode = True
            clean_line = re.sub(r"^\d+[\.\)]\s*", "", line)
            html_output += f"<li>{clean_line}</li>"
        
        # Handle dash list
        elif line.startswith("-") or line.startswith("•"):
            if not bullet_mode:
                html_output += "<ul class='bullet-list'>"
                bullet_mode = True
            clean_line = line[1:].strip() if line.startswith("-") else line[1:].strip()
            html_output += f"<li>{clean_line}</li>"
        
        # Handle bullet points already in text
        elif "•" in line:
            if not bullet_mode:
                html_output += "<ul class='bullet-list'>"
                bullet_mode = True
            parts = line.split("•")
            for part in parts:
                if part.strip():
                    html_output += f"<li>{part.strip()}</li>"
        
        # Handle section headers (ends with colon)
        elif line.endswith(':') and len(line) < 50:
            if bullet_mode:
                html_output += "</ul>"
                bullet_mode = False
            html_output += f"<h4 class='section-header'>{line}</h4>"
        
        # Regular paragraph
        else:
            if bullet_mode:
                html_output += "</ul>"
                bullet_mode = False
            html_output += f"<p>{line}</p>"
    
    # Close any open bullet list
    if bullet_mode:
        html_output += "</ul>"
    
    return html_output

# --------------------------------------------------
# Custom CSS - ChatGPT Style Premium UI
# --------------------------------------------------
components.html("""
<style>
#customSidebarToggle {
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 9999;
    background: #2563EB;
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 50px;
    cursor: pointer;
    font-size: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
#customSidebarToggle:hover {
    background: #1D4ED8;
}
</style>

<button id="customSidebarToggle">☰</button>

<script>
const toggleBtn = document.getElementById("customSidebarToggle");

toggleBtn.onclick = function() {
    const btn = document.querySelector('button[data-testid="collapsedControl"]');
    if (btn) {
        btn.click();
    }
};
</script>
""", height=0)

st.markdown("""
<style>
    /* Main header - Premium gradient */
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Answer box - ChatGPT style */
    .answer-box {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 10px 25px rgba(0,0,0,0.04);
        margin: 1.5rem 0;
        font-size: 1.05rem;
        line-height: 1.8;
        color: #1F2937;
        transition: box-shadow 0.2s ease;
    }
    
    .answer-box:hover {
        box-shadow: 0 15px 30px rgba(0,0,0,0.06);
    }
    
    /* Paragraphs */
    .answer-box p {
        margin-bottom: 1.2rem;
        color: #374151;
    }
    
    /* Bullet lists - Real HTML bullets */
    .answer-box ul.bullet-list {
        margin: 1.2rem 0;
        padding-left: 1.8rem;
        list-style-type: disc;
    }
    
    .answer-box ul.bullet-list li {
        margin-bottom: 0.7rem;
        color: #374151;
        line-height: 1.7;
        padding-left: 0.5rem;
    }
    
    /* Section headers */
    .answer-box h4.section-header {
        font-size: 1.15rem;
        font-weight: 600;
        color: #1E3A8A;
        margin: 1.5rem 0 0.8rem 0;
        border-bottom: 2px solid #EFF6FF;
        padding-bottom: 0.5rem;
    }
    
    /* Source citation */
    .source-citation {
        background: #F3F4F6;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-size: 0.9rem;
        color: #4B5563;
        margin: 1.2rem 0 0.5rem 0;
        border-left: 4px solid #9CA3AF;
        display: inline-block;
        font-family: 'SF Mono', monospace;
    }
    
    /* Confidence indicators */
    .confidence-high { 
        color: #10B981; 
        font-weight: 700;
        background: rgba(16, 185, 129, 0.1);
        padding: 6px 18px;
        border-radius: 30px;
        display: inline-block;
        font-size: 1.1rem;
    }
    
    .confidence-medium { 
        color: #F59E0B; 
        font-weight: 700;
        background: rgba(245, 158, 11, 0.1);
        padding: 6px 18px;
        border-radius: 30px;
        display: inline-block;
        font-size: 1.1rem;
    }
    
    .confidence-low { 
        color: #EF4444; 
        font-weight: 700;
        background: rgba(239, 68, 68, 0.1);
        padding: 6px 18px;
        border-radius: 30px;
        display: inline-block;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        border-color: #3B82F6;
        box-shadow: 0 8px 16px rgba(59, 130, 246, 0.08);
    }
    
    /* Quick question buttons - Pill style */
    .stButton > button {
        background-color: white;
        color: #1F2937;
        border: 1.5px solid #E5E7EB;
        padding: 8px 20px;
        border-radius: 40px;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #3B82F6;
        color: white;
        border-color: #3B82F6;
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(59, 130, 246, 0.2);
    }
    
    /* Primary button - Ask */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%);
        color: white;
        border: none;
        font-weight: 600;
        padding: 12px 28px;
        border-radius: 40px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%);
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
        transform: translateY(-2px);
    }
    
    /* Text input - Clean and modern */
    .stTextInput > div > input {
        font-size: 1.05rem;
        padding: 1rem 1.2rem;
        border-radius: 50px;
        border: 2px solid #E5E7EB;
        transition: all 0.2s ease;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    .stTextInput > div > input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
    }
    
    .stTextInput > div > input::placeholder {
        color: #9CA3AF;
        font-size: 1rem;
    }
    
    /* Form styling */
    .stForm {
        background-color: transparent;
        border: none;
        padding: 0;
    }
    
    /* Divider */
    .stDivider {
        margin: 2rem 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #F9FAFB 0%, #FFFFFF 100%);
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Check Authentication
# --------------------------------------------------
if not st.session_state.get('authenticated', False):
    from auth import show_login_page
    show_login_page()
    st.stop()

# --------------------------------------------------
# Load AI POD (only for authenticated users)
# --------------------------------------------------
@st.cache_resource
def load_ai_pod():
    try:
        ai_pod = AIPodQuerySystem()
        return ai_pod
    except FileNotFoundError:
        st.error("❌ Index not found. Please run: python ingest_documents.py")
        return None
    except Exception as e:
        st.error(f"❌ Failed to load AI POD: {e}")
        return None

ai_pod = load_ai_pod() if AI_POD_AVAILABLE else None

# --------------------------------------------------
# Header (for authenticated users)
# --------------------------------------------------
st.markdown('<h1 class="main-header">🤖 AI POD</h1>', unsafe_allow_html=True)
st.markdown(
    f'<p class="sub-header">{AIPodConfig.COMPANY_NAME} – Internal AI Assistant</p>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# Sidebar - With User Profile
# --------------------------------------------------
with st.sidebar:
    if st.button("🔄 Reset Sidebar", use_container_width=True):
        st.session_state.sidebar_state = "expanded"
        st.rerun()
    # User Profile
    show_user_profile()
    
    st.markdown("---")
    
    # System Status
    st.subheader("📊 System Status")
    
    if ai_pod:
        st.success("✅ Online")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Knowledge Base", f"{len(ai_pod.chunks)} chunks")
        with col2:
            mode = "AI" if ai_pod.groq_client else "Basic"
            st.metric("Mode", mode)
        
        # Show thresholds - Different access levels
        with st.expander("🔧 Semantic Thresholds"):
            st.markdown(f"""
            - **High:** > {ai_pod.thresholds['high']:.1%}
            - **Medium:** {ai_pod.thresholds['medium']:.1%} - {ai_pod.thresholds['high']:.1%}
            - **Low:** {ai_pod.thresholds['low']:.1%} - {ai_pod.thresholds['medium']:.1%}
            - **Off-topic:** < {ai_pod.thresholds['low']:.1%}
            """)
        
        # Admin section - Only visible to admin
        if check_permission(['admin']):
            with st.expander("👑 Admin Panel"):
                st.info("User management coming soon")
                if st.button("🔄 Reset Users", use_container_width=True):
                    os.remove("users.json")
                    st.rerun()
    else:
        st.error("❌ Offline")
        st.code("python ingest_documents.py")

    st.markdown("---")
    
    # Quick Questions - Role-based access
    st.subheader("💡 Quick Questions")
    
    quick_q = {
        "🏖️ Annual Leave": "How many annual leave days?",
        "🏥 Sick Leave": "What is sick leave policy?",
        "🔒 Confidential": "Are HR policies confidential?",
        "💰 Bonus": "What is bonus policy?",
    }
    
    # IT questions only for IT department or admin
    if check_permission(['admin', 'it']) or st.session_state.user.get('department') == 'IT':
        quick_q["🔑 Password"] = "What is password policy?"
        quick_q["🌐 Remote Work"] = "What is remote work policy?"
    
    for label, q in quick_q.items():
        if st.button(label, use_container_width=True, key=f"en_{label}"):
            st.session_state.question = q
            st.rerun()
    
    st.markdown("**🇸🇦 العربية**")
    ar_quick_q = {
        "🏖️ إجازة سنوية": "كم يوم إجازة سنوية؟",
        "🏥 إجازة مرضية": "ما هي سياسة الإجازة المرضية؟",
        "🔒 السرية": "هل سياسات الموارد البشرية سرية؟",
        "💰 مكافأة": "ما هي سياسة المكافآت؟",
    }
    
    for label, q in ar_quick_q.items():
        if st.button(label, use_container_width=True, key=f"ar_{label}"):
            st.session_state.question = q
            st.rerun()
    
    st.markdown("---")
    
    # Chat History
    if st.session_state.chat_history:
        st.subheader("💭 Recent Questions")
        for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):
            if st.button(f"Q: {chat['question'][:40]}...", 
                        key=f"hist_{i}", 
                        use_container_width=True):
                st.session_state.question = chat['question']
                st.rerun()
    
    # Clear History
    if st.session_state.chat_history:
        st.markdown("---")
        if st.button("🗑️ Clear History", use_container_width=True, type="secondary"):
            st.session_state.chat_history = []
            st.session_state.question = ""
            st.rerun()

# --------------------------------------------------
# Main Area - Only for authenticated users
# --------------------------------------------------
tab1, tab2 = st.tabs(["💬 Ask AI POD", "📊 Analytics"])

with tab1:
    # Clean, simple interface - no Enter hint needed
    with st.form(key="ask_form", clear_on_submit=False):
        
        # st.text_input = ENTER submits automatically! Perfect for chat
        question = st.text_input(
            "Ask your question:",
            value=st.session_state.question,
            placeholder="Example: How many annual leave days? | مثال: كم يوم إجازة سنوية؟",
            key="question_input",
            label_visibility="collapsed"
        )
        
        col1, col2, col3 = st.columns([1, 1, 5])
        
        with col1:
            submit_button = st.form_submit_button(
                "🔍 Ask", 
                type="primary", 
                use_container_width=True,
                disabled=not question.strip() or not ai_pod
            )
        
        with col2:
            clear_button = st.form_submit_button(
                "🗑️ Clear", 
                use_container_width=True,
                type="secondary"
            )
    
    # Handle Clear button
    if clear_button:
        st.session_state.question = ""
        st.rerun()
    
    # Process question when form is submitted (ENTER key or Ask button)
    if submit_button and question.strip() and ai_pod:
        with st.spinner("🔍 Searching policies..."):
            try:
                # Get answer
                result = ai_pod.ask(question)
                lang = detect_language(question)
                
                # Extract source if present
                source_match = re.search(r'\[From: (.*?)\]', result["answer"])
                source_doc = source_match.group(1) if source_match else "Company Policy"
                
                # Clean the answer
                clean_answer = result["answer"].replace(f"[From: {source_doc}]", "").strip()
                
                # Format with REAL HTML bullet points
                formatted_answer = format_answer(clean_answer)
                
                # Display answer in beautiful ChatGPT-style box
                st.markdown(
                    f"""
                    <div class="answer-box">
                        {formatted_answer}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Copy button
                col_copy, _ = st.columns([1, 6])
                with col_copy:
                    if st.button("📋 Copy Answer", key="copy_button"):
                        st.toast("✅ Answer copied to clipboard!")
                
                # Analysis in clean columns
                st.subheader("📊 Analysis")
                
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                
                with col_a1:
                    lang_name = "Arabic 🇸🇦" if lang == "ar" else "English 🇬🇧"
                    st.metric("Language", lang_name)
                
                with col_a2:
                    confidence = result["confidence"]
                    if confidence >= 0.7:
                        conf_class = "confidence-high"
                        conf_text = "High Confidence"
                    elif confidence >= 0.4:
                        conf_class = "confidence-medium"
                        conf_text = "Medium Confidence"
                    else:
                        conf_class = "confidence-low"
                        conf_text = "Low Confidence"
                    
                    st.markdown(
                        f"<span class='{conf_class}'>{conf_text}: {confidence:.1%}</span>",
                        unsafe_allow_html=True
                    )
                
                with col_a3:
                    match_type = result.get('match_type', 'none').replace('_', ' ').title()
                    st.metric("Match Type", match_type)
                
                with col_a4:
                    response_time = result.get('response_time', 0)
                    st.metric("Response Time", f"{response_time:.2f}s")
                
                # Save to history
                st.session_state.chat_history.append({
                    "question": question,
                    "answer": clean_answer[:100] + "...",
                    "timestamp": datetime.now().isoformat(),
                    "language": lang,
                    "confidence": confidence
                })
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)[:200]}")

with tab2:
    st.subheader("📊 System Analytics")
    
    if ai_pod and st.session_state.chat_history:
        # Key metrics in clean cards
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            st.metric("Questions Asked", len(st.session_state.chat_history))
        
        with col_m2:
            avg_conf = sum(c.get('confidence', 0) for c in st.session_state.chat_history) / len(st.session_state.chat_history)
            st.metric("Avg. Confidence", f"{avg_conf:.1%}")
        
        with col_m3:
            st.metric("Knowledge Base", f"{len(ai_pod.chunks)} chunks")
        
        st.divider()
        
        # Language distribution
        col_l1, col_l2 = st.columns(2)
        
        with col_l1:
            st.write("**🌐 Languages**")
            lang_counts = {}
            for chat in st.session_state.chat_history:
                lang = chat.get('language', 'en')
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
            for lang, count in lang_counts.items():
                lang_name = "Arabic" if lang == "ar" else "English"
                st.write(f"• {lang_name}: {count}")
        
        with col_l2:
            st.write("**📈 Confidence Distribution**")
            confidences = [c.get('confidence', 0) for c in st.session_state.chat_history]
            high = sum(1 for c in confidences if c >= 0.7)
            medium = sum(1 for c in confidences if 0.4 <= c < 0.7)
            low = sum(1 for c in confidences if c < 0.4)
            
            st.write(f"• High (>70%): {high}")
            st.write(f"• Medium (40-70%): {medium}")
            st.write(f"• Low (<40%): {low}")
    
    elif ai_pod:
        st.info("📊 No usage data yet. Start asking questions!")
    else:
        st.warning("⚠️ System offline")

# --------------------------------------------------
# Footer - Clean and minimal
# --------------------------------------------------
st.divider()
st.markdown(f"""
<div style="text-align: center; color: #6B7280; padding: 1rem; font-size: 0.85rem;">
    <strong>AI POD v{AIPodConfig.VERSION}</strong> • {AIPodConfig.COMPANY_NAME}<br>
    <span style="font-family: monospace;">User: {st.session_state.user['username']} | Session: {st.session_state.session_id}</span>
</div>
""", unsafe_allow_html=True)