import streamlit as st
from datetime import datetime
import httpx

# Keep message history
st.session_state.setdefault("log", [])

# Page setup
st.set_page_config(page_title="Jain Granthas Search", page_icon="📖")
st.title("📖 Upload and Search Jain Granthas")

# Call your Gemini File Search backend
def call_gemini_agent(prompt):
    try:
        response = httpx.post(
            "http://localhost:3000/invoke/tool/travel_agent_prompt",
            json={"input": {"input": prompt}},
            timeout=120.0  # File Search can take longer
        )
        response.raise_for_status()
        data = response.json().get("result", {})
        return {"output": data.get("output", "")}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}

# Display chat history
def show_history():
    for turn in st.session_state.log[-10:]:  # Show last 10 exchanges
        msg = st.chat_message(turn["role"])
        msg.write(turn["content"])

# --- 📂 File Upload Section ---
st.subheader("📂 Upload Granthas (PDF, TXT, CSV)")
uploaded_file = st.file_uploader(
    "Choose a Jain grantha file", 
    type=["pdf", "txt", "csv", "docx"],
    help="Upload PDF granthas, text files, or CSV data for search"
)

if uploaded_file is not None:
    with st.spinner(f"Indexing {uploaded_file.name} in Gemini File Search..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            resp = httpx.post(
                "http://localhost:3000/upload_file/",
                files=files,
                timeout=120.0
            )
            resp.raise_for_status()
            result = resp.json()
            st.success(result.get("message", "✅ File indexed successfully!"))
            st.caption(f"Store: {result.get('store_name', 'created')}")
        except Exception as e:
            st.error(f"Upload failed: {str(e)}")

# Sidebar info
with st.sidebar:
    st.markdown("### 🔧 Status")
    st.info("**Backend**: Gemini File Search\n**Files**: Auto-indexed\n**Query**: Semantic search across all uploads")
    st.caption("Run backend: `uvicorn app:app --port 3000`")

# --- 🔍 Query Section ---
st.subheader("🔍 Ask Questions About Your Granthas")

# Show history first
show_history()

# Main chat input
if prompt := st.chat_input("Ask about Jain granthas, upanishads, or uploaded files..."):
    # User message
    st.chat_message("user").write(prompt)
    st.session_state.log.append({"role": "user", "content": prompt})

    # Agent response
    with st.chat_message("assistant"):
        with st.spinner("Searching your files with Gemini..."):
            result = call_gemini_agent(prompt)
            answer = result.get("output", "No response.")
            st.write(answer)
    
    st.session_state.log.append({"role": "assistant", "content": answer})

# Footer
st.caption(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
