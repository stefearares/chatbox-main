import getpass
import signal
import sys

import requests
from groq import Groq

from src.config.settings import settings

API_BASE = settings.api_base_url

groq_client = Groq(api_key=settings.groq_key)

GROQ_MODEL = "llama-3.1-8b-instant"
TOP_K = 5
CHUNKS_PER_FILE = 2
CONTEXT_THRESHOLD = 10  # max exchanges before auto-reset

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful personal assistant. Answer the user's question using only "
        "the provided context. If the answer is not in the context, say so."
    ),
}


def rewrite_query(query: str) -> str:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the core search keywords from the user's question. "
                    "Return only the keywords, nothing else."
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content.strip()


def retrieve_chunks(query: str, token: str, chunks_per_file: int = CHUNKS_PER_FILE) -> list[dict]:
    res = requests.get(
        f"{API_BASE}/files/search/chunks",
        params={"q": query, "limit": TOP_K * chunks_per_file},
        headers={"Authorization": f"Bearer {token}"},
    )
    res.raise_for_status()
    return res.json().get("results", [])


def ask(query: str, token: str, history: list) -> str:
    search_query = rewrite_query(query)
    chunks = retrieve_chunks(search_query, token)

    if not chunks:
        return "No relevant documents found."

    context = "\n\n".join(f"[{c['filename']}] {c['text']}" for c in chunks)

    history.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"})

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[SYSTEM_PROMPT] + history,
    )

    answer = response.choices[0].message.content
    history.append({"role": "assistant", "content": answer})

    return answer


def authenticate() -> tuple[str, str]:
    try:
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")

        res = requests.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": password},
        )

        if res.status_code == 401:
            print("Invalid email or password.")
            sys.exit(1)

        res.raise_for_status()
        data = res.json()
        return data["access_token"], data["user"]["name"]

    except KeyboardInterrupt:
        goodbye()


def goodbye(name: str = ""):
    print(f"\n\nGoodbye, {name}! :)" if name else "\n\nGoodbye! :)")
    sys.exit(0)


BANNER = """
    chatbox ai  *  v0.1
  =============================
  > ask anything about your files
"""


def main():
    print(BANNER)
    token, name = authenticate()
    signal.signal(signal.SIGTERM, lambda *_: goodbye(name))
    print(f"\nWelcome, {name}!\n")

    history = []

    try:
        while True:
            query = input("> ").strip()

            if query.lower() == "/exit":
                goodbye(name)
            if query.lower() == "/clear":
                history.clear()
                print("  context cleared.\n")
                continue
            if not query:
                continue

            if len(history) >= CONTEXT_THRESHOLD * 2:
                history.clear()
                print("  context limit reached, starting fresh.\n")

            print("\nchatbox_ai: " + ask(query, token, history))
            print()
    except KeyboardInterrupt:
        goodbye(name)


if __name__ == "__main__":
    main()
