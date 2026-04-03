"""
MediAssist AI — Streamlit frontend  (v2 — timeout-safe)
Run with: streamlit run app.py
Requires the FastAPI backend running at API_URL.
"""

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8003/execute"
REQUEST_TIMEOUT = 180   # 3 minutes — enough for multi-hop agentic chains

st.set_page_config(
    page_title="MediAssist AI",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: linear-gradient(135deg,#f0f7ff 0%,#e8f4f8 50%,#f5f0ff 100%); min-height:100vh; }
#MainMenu, footer, header { visibility: hidden; }

.hero {
    background: linear-gradient(135deg,#0a5c8a 0%,#1a3a6e 60%,#2d1b69 100%);
    border-radius:20px; padding:2rem 2.5rem 1.6rem; margin-bottom:1.6rem;
    box-shadow:0 8px 32px rgba(10,92,138,.25); position:relative; overflow:hidden;
}
.hero::before { content:''; position:absolute; top:-30px; right:-30px; width:180px; height:180px;
    background:rgba(255,255,255,.05); border-radius:50%; }
.hero-badge { display:inline-block; background:rgba(255,255,255,.15); color:#a8d4f5;
    font-size:11px; font-weight:500; letter-spacing:1.5px; text-transform:uppercase;
    padding:4px 12px; border-radius:20px; border:1px solid rgba(255,255,255,.2); margin-bottom:10px; }
.hero-title { font-family:'DM Serif Display',serif; font-size:2rem; color:#fff; margin:0 0 6px; line-height:1.2; }
.hero-sub { color:#90c4e8; font-size:.9rem; margin:0 0 1.2rem; font-weight:300; }
.hero-features { display:flex; gap:12px; flex-wrap:wrap; }
.hero-chip { background:rgba(255,255,255,.12); color:#cce8fa; font-size:12px; padding:5px 12px;
    border-radius:20px; border:1px solid rgba(255,255,255,.15); white-space:nowrap; }

.card { background:#fff; border-radius:16px; padding:1.4rem 1.6rem; margin-bottom:1rem;
    box-shadow:0 2px 12px rgba(0,0,0,.06); border:1px solid rgba(0,0,0,.05); }
.card-title { font-size:13px; font-weight:600; color:#6b7280; text-transform:uppercase;
    letter-spacing:.8px; margin-bottom:10px; }

.chat-wrap { display:flex; flex-direction:column; gap:12px; padding:.5rem 0; }
.bubble-user { align-self:flex-end; background:#0a5c8a; color:#fff;
    border-radius:18px 18px 4px 18px; padding:10px 16px; max-width:80%;
    font-size:14px; line-height:1.5; box-shadow:0 2px 8px rgba(10,92,138,.2); }
.bubble-bot { align-self:flex-start; background:#f3f4f6; color:#1f2937;
    border-radius:18px 18px 18px 4px; padding:10px 16px; max-width:85%;
    font-size:14px; line-height:1.5; border:1px solid #e5e7eb; }

.status-ok   { color:#059669; background:#d1fae5; border-radius:6px; padding:2px 8px; font-size:12px; font-weight:600; }
.status-err  { color:#dc2626; background:#fee2e2; border-radius:6px; padding:2px 8px; font-size:12px; font-weight:600; }
.status-warn { color:#d97706; background:#fef3c7; border-radius:6px; padding:2px 8px; font-size:12px; font-weight:600; }

.notif-banner { background:linear-gradient(90deg,#ecfdf5,#d1fae5); border:1px solid #6ee7b7;
    border-radius:10px; padding:10px 16px; display:flex; align-items:center; gap:10px;
    margin-top:8px; font-size:13px; color:#065f46; font-weight:500; }

.thinking-wrap { text-align:center; padding:1.2rem; }
.thinking-dots span { display:inline-block; width:8px; height:8px; background:#0a5c8a;
    border-radius:50%; margin:0 3px; animation:bounce 1.2s infinite ease-in-out; }
.thinking-dots span:nth-child(2) { animation-delay:.2s; }
.thinking-dots span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { 0%,80%,100%{transform:scale(0);opacity:.3} 40%{transform:scale(1);opacity:1} }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius:10px !important; border:1.5px solid #d1d5db !important;
    font-family:'DM Sans',sans-serif !important; font-size:14px !important; }
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color:#0a5c8a !important; box-shadow:0 0 0 3px rgba(10,92,138,.1) !important; }

.stButton > button {
    background:linear-gradient(135deg,#0a5c8a,#1a3a6e) !important; color:white !important;
    border:none !important; border-radius:10px !important;
    font-family:'DM Sans',sans-serif !important; font-weight:500 !important;
    font-size:14px !important; padding:.55rem 1.5rem !important;
    transition:all .2s ease !important; width:100% !important; }
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 6px 20px rgba(10,92,138,.35) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
if "chat_history"  not in st.session_state: st.session_state.chat_history  = []
if "prefill_query" not in st.session_state: st.session_state.prefill_query = ""
if "is_loading"    not in st.session_state: st.session_state.is_loading    = False

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">🩺 MediAssist AI</div>
    <div class="hero-title">Your Medical Concierge</div>
    <div class="hero-sub">AI-powered appointment booking · Availability checks · FAQs</div>
    <div class="hero-features">
        <span class="hero-chip">💬 Medical Q&amp;A</span>
        <span class="hero-chip">📅 Book appointments</span>
        <span class="hero-chip">✅ Check availability</span>
        <span class="hero-chip">❌ Cancel &amp; reschedule</span>
        <span class="hero-chip">📧 Email notifications</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Layout ───────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.8], gap="medium")

with col_left:
    # Patient ID
    st.markdown('<div class="card"><div class="card-title">Patient Details</div>', unsafe_allow_html=True)
    user_id = st.text_input("Patient ID", placeholder="e.g. 1000099",
                            label_visibility="collapsed",
                            help="7 or 8-digit patient identification number")
    if user_id:
        try:
            v = int(user_id)
            if 1_000_000 <= v <= 99_999_999:
                st.markdown('<span class="status-ok">✓ Valid ID</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-warn">⚠ 7–8 digits</span>', unsafe_allow_html=True)
        except ValueError:
            st.markdown('<span class="status-err">✗ Numbers only</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick actions
    st.markdown('<div class="card"><div class="card-title">Quick Actions</div>', unsafe_allow_html=True)
    quick = {
        "📅 Book appointment":  "I'd like to book an appointment with a general dentist.",
        "✅ Check availability": "Can you check if a dentist is available today?",
        "❌ Cancel appointment": "I want to cancel my appointment.",
        "🔄 Reschedule":         "I need to reschedule my appointment.",
        "ℹ️ Hospital FAQs":      "What specializations does your hospital offer?",
    }
    for label, text in quick.items():
        if st.button(label, key=f"qa_{label}", disabled=st.session_state.is_loading):
            st.session_state.prefill_query = text
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    # Chat history
    if st.session_state.chat_history:
        st.markdown('<div class="card"><div class="card-title">Conversation</div>', unsafe_allow_html=True)
        html = '<div class="chat-wrap">'
        for turn in st.session_state.chat_history:
            if turn["role"] == "user":
                html += f'<div class="bubble-user">{turn["content"]}</div>'
            else:
                html += f'<div class="bubble-bot">{turn["content"]}</div>'
                if turn.get("email_sent"):
                    html += '<div class="notif-banner"><span>📧</span> Email notification sent to patient.</div>'
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card"><div style="text-align:center;padding:1rem 0;">
          <div style="font-size:2.5rem;margin-bottom:.5rem;">🩺</div>
          <div style="font-weight:600;font-size:1rem;color:#1f2937;margin-bottom:6px;">Hello! I'm MediAssist AI.</div>
          <div style="color:#6b7280;font-size:13px;line-height:1.6;">
            Book, cancel, or reschedule appointments,<br>
            check doctor availability, and get answers to medical FAQs.
          </div>
        </div></div>
        """, unsafe_allow_html=True)

    # Thinking animation while waiting
    if st.session_state.is_loading:
        st.markdown("""
        <div class="card thinking-wrap">
          <div style="font-size:13px;color:#6b7280;margin-bottom:10px;">
            MediAssist is thinking — this may take up to 60 seconds…
          </div>
          <div class="thinking-dots"><span></span><span></span><span></span></div>
        </div>
        """, unsafe_allow_html=True)

    # Input
    st.markdown('<div class="card"><div class="card-title">Your Message</div>', unsafe_allow_html=True)
    default_text = st.session_state.pop("prefill_query", "") or (
        "" if st.session_state.chat_history
        else "Can you check if a dentist is available today at 10 AM?"
    )
    query = st.text_area("Query", value=default_text, placeholder="Type your question here…",
                         height=100, label_visibility="collapsed",
                         disabled=st.session_state.is_loading)
    label = "⏳ Waiting…" if st.session_state.is_loading else "Send Message →"
    submit = st.button(label, use_container_width=True, disabled=st.session_state.is_loading)
    st.markdown("</div>", unsafe_allow_html=True)

# ─── Submit — stage 1: record user message, flip loading flag ─────────────────
if submit and not st.session_state.is_loading:
    if not user_id:
        st.error("Please enter your Patient ID.")
    elif not query.strip():
        st.warning("Please type a message first.")
    else:
        try:
            int(user_id)
        except ValueError:
            st.error("Patient ID must be a number.")
            st.stop()
        st.session_state.is_loading = True
        st.session_state.chat_history.append({"role": "user", "content": query.strip()})
        st.rerun()

# ─── Submit — stage 2: make the API call after rerun ─────────────────────────
if st.session_state.is_loading and user_id:
    pending_query = st.session_state.chat_history[-1]["content"]
    try:
        id_int = int(user_id)
    except ValueError:
        st.session_state.is_loading = False
        st.rerun()

    bot_reply = None
    error_msg = None

    try:
        resp = requests.post(
            API_URL,
            json={"messages": pending_query, "id_number": id_int},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            messages = resp.json().get("messages", [])
            for msg in reversed(messages):
                content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                if content and str(content).strip():
                    bot_reply = str(content).strip()
                    break
            if not bot_reply:
                bot_reply = "I've processed your request. Is there anything else I can help you with?"
        else:
            error_msg = f"Backend error {resp.status_code}: {resp.text[:300]}"

    except requests.exceptions.Timeout:
        error_msg = (
            "⏱ Request timed out after 3 minutes. "
            "The agent chain is taking longer than expected. "
            "Please try again or simplify your query."
        )
    except requests.exceptions.ConnectionError:
        error_msg = (
            "🔌 Cannot connect to the backend. "
            "Start it with: `uvicorn main:app --host 127.0.0.1 --port 8003 --reload`"
        )
    except Exception as e:
        error_msg = f"Unexpected error: {e}"

    st.session_state.is_loading = False

    if error_msg:
        st.session_state.chat_history.pop()   # remove optimistic user message
        st.error(error_msg)
    else:
        email_sent = any(
            kw in bot_reply.lower()
            for kw in ["email sent", "notification sent", "confirmation email", "cancellation email"]
        )
        st.session_state.chat_history.append(
            {"role": "bot", "content": bot_reply, "email_sent": email_sent}
        )

    st.rerun()

st.markdown("""
<div style="text-align:center;padding:1.5rem 0 .5rem;color:#9ca3af;font-size:12px;">
    MediAssist AI · Powered by Groq LLaMA · LangGraph Multi-Agent System
</div>
""", unsafe_allow_html=True)