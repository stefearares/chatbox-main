import getpass
import json
import signal
import sys

import requests
from groq import Groq

from src.config.settings import settings

API_BASE = settings.api_base_url

groq_client = Groq(api_key=settings.groq_key)

GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5
CHUNKS_PER_FILE = 2
CONTEXT_THRESHOLD = 10  # max exchanges before auto-reset

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful personal assistant for a document management system. "
        "You have tools to list, search, and inspect the user's uploaded files — use them when relevant. "
        "When answering questions about file contents, rely on the provided context. "
        "If the answer is not available, say so."
    ),
}


def list_user_files(token: str) -> str:
    try:
        res = requests.get(
            f"{API_BASE}/files",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        files = res.json()
        if not files:
            return "No files uploaded yet."
        return "\n".join(f"- {f['original_name']} (id: {f['id']})" for f in files)
    except Exception as e:
        return f"Error: {e}"


def search_files(query: str, token: str) -> str:
    try:
        res = requests.get(
            f"{API_BASE}/files/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        results = res.json().get("results", [])
        if not results:
            return "No results found."
        return "\n".join(f"- {r['filename']}: {r.get('snippet', '')[:200]}" for r in results)
    except Exception as e:
        return f"Error: {e}"


def get_file_content(file_id: str, token: str) -> str:
    try:
        res = requests.get(
            f"{API_BASE}/files/{file_id}/content",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        return res.text
    except Exception as e:
        return f"Error: {e}"


def get_file_info(file_id: str, token: str) -> str:
    try:
        res = requests.get(
            f"{API_BASE}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        f = res.json()
        size_kb = round(f.get("size", 0) / 1024, 2)
        return f"Name: {f['original_name']}\nSize: {size_kb} KB\nUploaded: {f.get('created_at', 'unknown')}"
    except Exception as e:
        return f"Error: {e}"


def get_file_stats(token: str) -> str:
    try:
        res = requests.get(
            f"{API_BASE}/files",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        files = res.json()
        total = len(files)
        total_kb = round(sum(f.get("size", 0) for f in files) / 1024, 2)
        return f"Total files: {total}\nTotal size: {total_kb} KB"
    except Exception as e:
        return f"Error: {e}"


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_user_files",
            "description": "List all files the user has uploaded, with their IDs",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search across uploaded file contents using hybrid search, returns file names and matching snippets",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Get the full text content of a specific file by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "The file's ID"}
                },
                "required": ["file_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get metadata for a specific file: name, size, and upload date",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "The file's ID"}
                },
                "required": ["file_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_stats",
            "description": "Get aggregate storage stats: total number of files and combined size",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def execute_tool_call(tool_call, token: str) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if name == "list_user_files":
        return list_user_files(token)
    if name == "search_files":
        return search_files(token=token, **args)
    if name == "get_file_content":
        return get_file_content(token=token, **args)
    if name == "get_file_info":
        return get_file_info(token=token, **args)
    if name == "get_file_stats":
        return get_file_stats(token)
    return f"Unknown tool: {name}"


def run_with_tools(messages: list, token: str) -> str:
    messages = list(messages)  

    while True:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or ""

        messages.append(message)

        for tool_call in message.tool_calls:
            result = execute_tool_call(tool_call, token)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": result,
            })


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


def can_answer_from_history(query: str, history: list) -> bool:
    if not history:
        return False

    history_text = "\n".join(
        f"{m['role']}: {m['content'][:300]}" for m in history[-6:]
    )

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Given the conversation history, can the user's new question be fully "
                    "answered from existing context? Reply with only 'yes' or 'no'."
                ),
            },
            {"role": "user", "content": f"History:\n{history_text}\n\nNew question: {query}"},
        ],
        max_tokens=5,
    )

    return response.choices[0].message.content.strip().lower().startswith("yes")


def ask(query: str, token: str, history: list) -> str:
    if can_answer_from_history(query, history):
        history.append({"role": "user", "content": query})
        answer = run_with_tools([SYSTEM_PROMPT] + history, token)
        history.append({"role": "assistant", "content": answer})
        return answer

    search_query = rewrite_query(query)
    chunks = retrieve_chunks(search_query, token)

    if chunks:
        context = "\n\n".join(f"[{c['filename']}] {c['text']}" for c in chunks)
        user_message = {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    else:
        user_message = {"role": "user", "content": query}

    history.append(user_message)
    answer = run_with_tools([SYSTEM_PROMPT] + history, token)
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


def check_server():
    try:
        requests.get(f"{API_BASE}/healthz", timeout=3)
    except requests.ConnectionError:
        print(f"  server not reachable at {API_BASE}. Is it running?")
        sys.exit(1)


def main():
    print(BANNER)
    check_server()
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
