import os
from dotenv import load_dotenv

load_dotenv()

print("HF token loaded:", bool(os.getenv("HF_TOKEN")))
print("LangSmith key loaded:", bool(os.getenv("LANGSMITH_API_KEY")))
print("LangSmith tracing:", os.getenv("LANGSMITH_TRACING"))
print("LangSmith project:", os.getenv("LANGSMITH_PROJECT"))
print("LangSmith endpoint:", os.getenv("LANGSMITH_ENDPOINT"))