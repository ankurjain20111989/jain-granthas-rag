import streamlit as st
from datetime import datetime
import httpx
import os

# Backend URL from environment (Render/Streamlit Cloud)
BACKEND_URL = os.getenv("BACKEND_URL", "https://jain-granthas-backend.onrender.com")
API_CHAT_ENDPOINT = f"{BACKEND_URL}/invoke/tool/travel_agent_prompt"
API_UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload_file/"

# Keep message history
if "log" not in st.session_state:
    st.session_state.log = []

# Page setup
st.set_page_config(page_title="Jain Granthas Search", page_icon="📖")
st.title("📖 Upload and Search Jain Granthas")

# Status sidebar FIRST (shows backend URL)
with st.sidebar:
    st.markdown("### 🔧 Status")
    st.info(f"**Backend**: {BACKEND_URL}")
    st.info("**Files**: Auto-indexed | **Query**: Semantic search")
    st.caption("✅ Production ready")

# Call backend API
def call_gemini_agent(prompt):
    try:
        response = httpx.post(
            API_CHAT_ENDPOINT,
            json={"input": {"input": prompt}},
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json().get("result", {})
        return {"output": data.get("output", ""), "files": data.get("files", [])}
    except Exception as e:
        return {"output": f"❌ Backend error: {str(e)}"}

# Display chat history
def show_history():
    for turn in st.session_state.log[-10:]:
        msg = st.chat_message(turn["role"])
        msg.write(turn["content"])

# --- 📂 File Upload Section ---
st.subheader("📂 Upload Granthas (PDF, TXT, CSV, DOCX)")
uploaded_file = st.file_uploader(
    "Choose a Jain grantha file",
    type=["pdf", "txt", "csv", "docx"],
    help="Upload PDF granthas, text files, or CSV data for search"
)

if uploaded_file is not None:
    with st.spinner(f"Indexing {uploaded_file.name}..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            resp = httpx.post(
                API_UPLOAD_ENDPOINT,
                files=files,
                timeout=120.0
            )
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(result.get("message", "✅ File indexed!"))
                st.caption(f"File: {result.get('file_name', 'uploaded')}")
        except Exception as e:
            st.error(f"Upload failed: {str(e)}")

# --- 🔍 Query Section ---
st.subheader("🔍 Ask Questions About Your Granthas")
show_history()

# Main chat input
if prompt := st.chat_input("Ask about Jain granthas, upanishads, or uploaded files..."):
    # User message
    st.chat_message("user").write(prompt)
    st.session_state.log.append({"role": "user", "content": prompt})

    # Agent response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching with Gemini..."):
            result = call_gemini_agent(prompt)
            answer = result.get("output", "No response.")
            st.write(answer)

            # Show files context if available
            files = result.get("files", [])
            if files:
                st.caption(f"📄 Files: {', '.join(files)}")

    st.session_state.log.append({"role": "assistant", "content": answer})

# Footer
st.caption(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
