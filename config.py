import os


GEMINI_KEY = None


try:
    import streamlit as st
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass


if not GEMINI_KEY:
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")


if not GEMINI_KEY:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass
