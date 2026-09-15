"""
Configuration for the Buy or Wait? financial decision agent.
"""
import os
from pathlib import Path

# Repository root
REPO_ROOT = Path(__file__).parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
MEDIA_DIR = DATASET_DIR / "media" / "images"
CODE_DIR = REPO_ROOT / "code"
EVAL_DIR = CODE_DIR / "evaluation"

# Input files
REQUESTS_CSV = DATASET_DIR / "requests.csv"
SAMPLE_REQUESTS_CSV = DATASET_DIR / "sample_requests.csv"
FINANCIAL_PROFILES_CSV = DATASET_DIR / "financial_profiles.csv"
FINANCIAL_EVENTS_CSV = DATASET_DIR / "financial_events.csv"
EXCHANGE_RATES_CSV = DATASET_DIR / "exchange_rates.csv"
PAYMENT_OPTIONS_CSV = DATASET_DIR / "request_payment_options.csv"
MESSAGES_CSV = DATASET_DIR / "messages.csv"
IMAGES_CSV = DATASET_DIR / "images.csv"

# Output files
OUTPUT_CSV = REPO_ROOT / "output.csv"
USAGE_REPORT = EVAL_DIR / "usage_report.md"
VALIDATION_REPORT = EVAL_DIR / "validation_report.md"
SAMPLE_RESULTS_CSV = EVAL_DIR / "sample_results.csv"

# Forecast horizon
FORECAST_DAYS = 90

# LLM settings (optional - for explanations and image OCR)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Which LLM to use for explanations
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")  # google, openai, anthropic, none
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

# Ollama local integration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")  # Empty means auto-detect
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "1"))

# Agentic mode flags
AGENTIC_MODE = os.getenv("AGENTIC_MODE", "true").lower() == "true"
AGENTIC_ROUTING = os.getenv("AGENTIC_ROUTING", "true").lower() == "true"
AGENT_CROSS_REVIEW = os.getenv("AGENT_CROSS_REVIEW", "true").lower() == "true"
MAX_AGENT_ROUNDS = int(os.getenv("MAX_AGENT_ROUNDS", "1"))
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.1"))

# Whether to use LLM for explanations (can disable for deterministic-only run)
USE_LLM_EXPLANATIONS = os.getenv("USE_LLM_EXPLANATIONS", "true").lower() == "true"
USE_LLM_IMAGE_OCR = os.getenv("USE_LLM_IMAGE_OCR", "true").lower() == "true"

# Deterministic confidence threshold (below which selective multi-agent triggers)
DETERMINISTIC_CONFIDENCE_THRESHOLD = 0.75

# Max spending changes to consider
MAX_SPENDING_CHANGES = 3

# Currencies
SUPPORTED_CURRENCIES = {"INR", "ZAR", "IDR", "USD", "EUR"}

# Status enums
EVENT_STATUS_INCLUDE = {"settled", "scheduled", "confirmed"}
EVENT_STATUS_EXCLUDE = {"cancelled", "failed", "reversed"}
EVENT_STATUS_PENDING = {"pending"}

# Flexibility types
FLEXIBILITY_STOPPABLE = "stoppable"
FLEXIBILITY_REDUCIBLE = "reducible"
FLEXIBILITY_REDUCIBLE_OR_STOPPABLE = "reducible_or_stoppable"
FLEXIBILITY_FIXED = "fixed"

# Affordability status values
AFFORDABLE_NOW = "affordable_now"
AFFORDABLE_WITH_PLAN = "affordable_with_plan"
AFFORDABLE_LATER = "affordable_later"
NOT_AFFORDABLE = "not_affordable"

# Payment method values
FULL_PAYMENT = "full_payment"
PARTIAL_PAYMENT = "partial_payment"
INSTALLMENTS = "installments"
WAIT = "wait"
NOT_RECOMMENDED = "not_recommended"
