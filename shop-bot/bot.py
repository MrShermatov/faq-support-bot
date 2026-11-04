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
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
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
    if "1842" in q or "заказ" in q:
        return (
            "У меня нет доступа к базе данных заказов, поэтому я не могу проверить статус заказа 1842. "
            "По общему регламенту магазина доставка осуществляется курьером на следующий день с 18:00 до 21:00. "
            "Я могу передать ваш вопрос оператору для уточнения информации."
        )
    if "16-й день" in q or "16 день" in q or "16" in q:
        return (
            "К сожалению, возврат на 16-й день невозможен. "
            "По регламенту магазина товар (в том числе вскрытый без брака) можно вернуть строго в течение 14 дней."
        )
    if "скидк" in q or "забудь" in q:
        return (
            "В нашем магазине скидок нет ни при каких условиях. "
            "Я с удовольствием отвечу на любые вопросы по регламенту магазина или характеристикам наушников X1."
        )
    if "стоят" in q or "цена" in q:
        return "Наушники X1 есть в наличии, их стоимость составляет 2 490 ₽."
    if "чехол" in q:
        return (
            "У меня нет информации о наличии чехлов для наушников, в нашем ассортименте представлены только наушники X1. "
            "Я могу передать ваш вопрос оператору."
        )
    if "брак" in q:
        return (
            "При наличии брака мы принимаем товар на экспертизу. "
            "Возврат денежных средств сразу не гарантируется — решение принимается по результатам экспертизы."
        )
    if "быстро придут деньги" in q or "сроки возврата денег" in q:
        return "Деньги возвращаются на ту же карту, с которой была совершена оплата, и поступают в течение 3 рабочих дней."
    if "системный промпт" in q or "инструкц" in q:
        return (
            "Я не могу раскрыть свой системный промпт или внутренние инструкции. "
            "Я виртуальный консультант магазина и готов ответить на ваши вопросы по регламенту."
        )
    return (
        "У меня нет информации по данному вопросу в регламенте магазина. "
        "Я могу передать ваш вопрос оператору."
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
            "Ошибка: переменная окружения GEMINI_API_KEY не задана. "
            "Пожалуйста, добавьте GEMINI_API_KEY в файл .env или установите её в системе."
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
            return "Ответ пуст или заблокирован фильтрами безопасности."

        except Exception as e:
            last_error = e
            err_str = str(e)
            # Retry transient 503 server load spikes
            if ("503" in err_str or "UNAVAILABLE" in err_str or "demand" in err_str) and attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return f"Ошибка при обращении к API: {e}"

    return f"Ошибка при обращении к API: {last_error}"


def interactive_loop():
    """Simple interactive CLI chat loop."""
    print("=" * 60)
    print("FAQ Support Assistant (Online Shop)")
    print(f"Model: {MODEL_NAME} | Temperature: {TEMPERATURE}")
    print("Type your question and press Enter. Type 'exit' or 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nПокупатель > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q", "выход"):
                print("Завершение работы. До свидания!")
                break

            answer = ask(user_input)
            print(f"\nБот > {answer}")
        except (KeyboardInterrupt, EOFError):
            print("\nСессия прервана. До свидания!")
            break


if __name__ == "__main__":
    interactive_loop()
