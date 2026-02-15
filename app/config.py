import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TARIFF_PDF_NAMES = ("port tariff.pdf", "port_tariff.pdf", "port-tariff.pdf")


def get_tariff_pdf_path() -> Path | None:
    for name in TARIFF_PDF_NAMES:
        path = DATA_DIR / name
        if path.is_file():
            return path
    return None

def get_tariff_pdf_path_or_raise() -> Path:
    path = get_tariff_pdf_path()
    if path:
        return path
    raise FileNotFoundError(
        f"No tariff PDF found in {DATA_DIR}. "
        f"Please place 'port tariff.pdf' (or port_tariff.pdf) in the data/ folder."
    )

CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"

SUPPORTED_PORTS = ("Durban", "Saldanha", "Richard's Bay", "Richards Bay")

TARIFF_TYPES = [
    "light dues",
    "port dues",
    "towage dues",
    "vehicle traffic services (VTS) dues",
    "pilotage dues",
    "running of vessel lines dues",
]


def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")


def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
