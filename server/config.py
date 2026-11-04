import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-20b")
AGENT_MODEL = os.getenv("AGENT_MODEL", "openai/gpt-oss-120b")
MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1" or not GROQ_API_KEY
DB_PATH = os.getenv("LEASH_DB", str(ROOT / "leash.db"))
COMPANY_DOMAIN = "acme.example"
ASK_TIMEOUT_S = float(os.getenv("ASK_TIMEOUT_S", "60"))
