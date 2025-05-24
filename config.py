import os


GEMINI_key="AIzaSyCeuUB1ffXZjzn5GEnmwOejAEsZOneC3wk"
CLAUDE_KEY="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"

# EXTERNAL_LLM_API_KEY = os.getenv("GOOGLE_API_KEY", GEMINI_key) 
# EXTERNAL_LLM_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash") 

EXTERNAL_LLM_API_KEY = os.getenv("API_KEY", GEMINI_key) 
EXTERNAL_LLM_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash") 
