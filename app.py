import streamlit as st
import requests
import tempfile
import os
from io import BytesIO

# Configuration
FASTAPI_URL = "http://localhost:8000"  # Make sure this matches your FastAPI server address

def main():
    st.set_page_config(page_title="Smart Recruitment System", layout="wide")
    
    # Initialize session state
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_01"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        st.session_state.user_id = st.text_input("User ID:", value=st.session_state.user_id)
        
        st.subheader("Data Management")
        if st.button("Clear Chat History"):
            response = requests.post(
                f"{FASTAPI_URL}/clear_history",
                json={"user_id": st.session_state.user_id}
            )
            if response.status_code == 200:
                st.session_state.messages = []
                st.success("Chat history cleared!")
            else:
                st.error(f"Error: {response.text}")
    
    # Main tabs
    tab1, tab2 = st.tabs(["💬 Chat", "📊 CV Analysis"])

    with tab1:
        st.header("AI Recruitment Assistant")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Send to FastAPI
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/chat",
                    json={
                        "question": prompt,
                        "user_id": st.session_state.user_id
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    bot_reply = response.json()["response"]
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    with st.chat_message("assistant"):
                        st.markdown(bot_reply)
                else:
                    st.error(f"Server error: {response.text}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

    with tab2:
        st.header("CV Analysis System")
        
        # File upload section
        st.subheader("Upload CVs")
        uploaded_files = st.file_uploader(
            "Select PDF CV files",
            type=["pdf"],
            accept_multiple_files=True,
            key="cv_uploader"
        )
        
        if uploaded_files:
            for file in uploaded_files:
                with st.spinner(f"Uploading {file.name}..."):
                    try:
                        # Save file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                            tmp.write(file.getvalue())
                            tmp_path = tmp.name
                        
                        # Send to FastAPI
                        with open(tmp_path, 'rb') as f:
                            response = requests.post(
                                f"{FASTAPI_URL}/upload-cv/",
                                files={"file": (file.name, f)},
                                params={"user_id": st.session_state.user_id},
                                timeout=30
                            )
                        
                        if response.status_code == 200:
                            st.success(f"File uploaded: {file.name}")
                        else:
                            st.error(f"Upload error: {response.text}")
                    except Exception as e:
                        st.error(f"Error occurred: {str(e)}")
                    finally:
                        if 'tmp_path' in locals() and os.path.exists(tmp_path):
                            os.unlink(tmp_path)
        
        # CV analysis section
        st.subheader("Analyze CVs")
        job_title = st.text_input("Job Title:")
        job_reqs = st.text_area("Job Requirements:", height=150)
        
        if st.button("Start Analysis", type="primary"):
            if not job_title or not job_reqs:
                st.warning("Please enter job title and requirements")
            else:
                with st.spinner("Analyzing CVs..."):
                    try:
                        response = requests.post(
                            f"{FASTAPI_URL}/evaluate-cvs/",
                            json={
                                "user_id": st.session_state.user_id,
                                "job_title": job_title,
                                "job_requirements": job_reqs
                            },
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            st.subheader("Analysis Results")
                            st.markdown(response.json()["evaluation"])
                        else:
                            st.error(f"Analysis error: {response.text}")
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()