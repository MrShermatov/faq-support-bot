import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure stdout/stderr handle UTF-8 cleanly on Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file
load_dotenv()

# Model and generation parameters
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
TEMPERATURE = 0.0

BASE_DIR = Path(__file__).resolve().parent
KB_FILE = BASE_DIR / "knowledge_base.md"
PROMPT_FILE = BASE_DIR / "system_prompt.txt"


def load_system_instruction() -> str:
    """Load system prompt and knowledge base, combining them into system instruction."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"System prompt file not found: {PROMPT_FILE}")
    if not KB_FILE.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {KB_FILE}")

    with open(PROMPT_FILE, "r", encoding="utf-8") as pf:
        prompt_text = pf.read().strip()
    with open(KB_FILE, "r", encoding="utf-8") as kbf:
        kb_text = kbf.read().strip()

    return f"{prompt_text}\n\n=== KNOWLEDGE BASE ===\n{kb_text}"


SYSTEM_INSTRUCTION = load_system_instruction()


def _get_mock_response(question: str) -> str:
    """Offline deterministic fallback when GEMINI_API_KEY is not configured and MOCK_GEMINI=1."""
    q = question.lower()
    if "1842" in q or "buyurtma" in q or "заказ" in q:
        return (
            "Afsuski, menda buyurtmalar bazasiga kirish huquqi yo'q, shu sababli 1842-sonli buyurtma holatini ko'ra olmayman. "
            "Do'konimiz umumiy qoidasiga ko'ra, yetkazib berish ertasi kuni soat 18:00 dan 21:00 gacha kuryer orqali amalga oshiriladi. "
            "Buyurtmangiz bo'yicha aniq ma'lumot olish uchun savolingizni operatorga yo'naltirishim mumkin."
        )
    if "16-kun" in q or "16 kun" in q or "16" in q:
        return (
            "Afsuski, 16-kuni mahsulotni qaytarishning imkoni yo'q. "
            "Do'kon reglamentiga ko'ra, tovar (shu jumladan ochilgan nuqsonsiz mahsulot) qat'iy ravishda 14 kun ichida qaytarilishi mumkin."
        )
    if "chegirma" in q or "скидк" in q or "unut" in q or "забудь" in q:
        return (
            "Do'konimizda hech qanday sharoitda chegirmalar taqdim etilmaydi. "
            "X1 quloqchinlari yoki do'kon qoidalari bo'yicha boshqa savollaringizga mamnuniyat bilan javob beraman."
        )
    if "narx" in q or "necha pul" in q or "qancha" in q or "стоят" in q or "цена" in q:
        return "X1 quloqchinlari omborda mavjud, ularning narxi 2 490 ₽."
    if "g'ilof" in q or "chexol" in q or "чехол" in q:
        return (
            "Menda quloqchinlar uchun g'iloflar mavjudligi haqida ma'lumot yo'q, do'konimizda faqat X1 quloqchinlari sotiladi. "
            "Savolingizni operatorga yo'naltirishim mumkin."
        )
    if "brak" in q or "nuqson" in q:
        return (
            "Brak (nuqsonli) mahsulot aniqlanganda uni ekspertizaga qabul qilamiz. "
            "Pulni darhol qaytarish kafolatlanmaydi — qaror ekspertiza natijalariga ko'ra qabul qilinadi."
        )
    if "qancha vaqtda tushadi" in q or "qachon keladi" in q or "быстро придут деньги" in q:
        return "Pul to'lov amalga oshirilgan o'sha kartaga 3 ish kuni ichida qaytariladi."
    if "prompt" in q or "ko'rsatma" in q or "инструкц" in q:
        return (
            "Kechirasiz, men o'z tizim promptim yoki ichki ko'rsatmalarimni oshkor qila olmayman. "
            "Men do'kon maslahatchisiman va sizga xaridlar bo'yicha yordam berishga tayyorman."
        )
    return (
        "Do'kon reglamentida bu savol bo'yicha ma'lumot mavjud emas. "
        "Savolingizni operatorga yo'naltirishim mumkin."
    )


def ask(question: str) -> str:
    """
    Make a single stateless call to the Gemini API (temperature=0).
    No chat history is preserved between calls to prevent context leakage.
    Handles errors gracefully without throwing unhandled exceptions.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        if os.getenv("MOCK_GEMINI", "").lower() in ("1", "true", "yes"):
            return _get_mock_response(question)
        return (
            "Xatolik: GEMINI_API_KEY o'zgaruvchisi topilmadi. "
            "Iltimos, .env fayliga GEMINI_API_KEY ni kiriting."
        )

    from google import genai
    from google.genai import types
    import time

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=TEMPERATURE,
                ),
            )

            if response.text:
                return response.text.strip()
            return "Javob bo'sh yoki xavfsizlik filtri tomonidan bloklandi."

        except Exception as e:
            last_error = e
            err_str = str(e)
            # Retry transient 503 server load spikes
            if ("503" in err_str or "UNAVAILABLE" in err_str or "demand" in err_str) and attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return f"API xatoligi: {e}"

    return f"API xatoligi: {last_error}"


def interactive_loop():
    """Simple interactive CLI chat loop in Uzbek."""
    print("=" * 60)
    print("FAQ yordamchi boti (Onlayn do'kon)")
    print(f"Model: {MODEL_NAME} | Harorat: {TEMPERATURE}")
    print("Savolingizni yozing va Enter tugmasini bosing.")
    print("Chiqish uchun 'exit', 'quit' yoki 'chiqish' deb yozing.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nMijoz > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q", "chiqish", "выход"):
                print("Dastur yakunlandi. Xaridingiz xayrli bo'lsin!")
                break

            answer = ask(user_input)
            print(f"\nBot > {answer}")
        except (KeyboardInterrupt, EOFError):
            print("\nSuhbat to'xtatildi. Salomat bo'ling!")
            break


if __name__ == "__main__":
    interactive_loop()
