# openai_smoke.py
import os
import sys
import argparse
import json

def die(msg, code=1):
    print(f"❌ {msg}")
    sys.exit(code)

def fingerprint(s):
    return f"{s[:6]}...{s[-4:]}" if s and len(s) >= 12 else (s or "MISSING")

def main():
    parser = argparse.ArgumentParser(description="OpenAI smoke test with verbose env diagnostics.")
    parser.add_argument("--override", action="store_true", help="Force .env values to override existing env vars.")
    parser.add_argument("--key", default=None, help="Explicit API key to use (overrides env).")
    parser.add_argument("--embedding-model", default=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    parser.add_argument("--chat-model", default=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
    args = parser.parse_args()

    # --- Show .env details and load it ---
    dotenv_path = None
    try:
        from dotenv import find_dotenv, load_dotenv
        load_dotenv(find_dotenv(), override=True)

        dotenv_path = find_dotenv(usecwd=True)
        print("🔎 dotenv path:", dotenv_path if dotenv_path else "NOT FOUND")
        print("🔎 pre-load has OPENAI_API_KEY?:", "OPENAI_API_KEY" in os.environ)
        load_dotenv(dotenv_path=dotenv_path or None, override=args.override)
        print("🔎 post-load has OPENAI_API_KEY?:", "OPENAI_API_KEY" in os.environ)
        print("🔎 override used?:", bool(args.override))
    except Exception as e:
        print("ℹ️ python-dotenv not available or failed to load:", e)

    # --- Optional decouple fallback ---
    openai_api_key = None
    if args.key:
        source = "--key arg"
        openai_api_key = args.key
    else:
        # environment first
        openai_api_key = os.getenv("OPENAI_API_KEY")
        source = "os.environ"
        if not openai_api_key:
            try:
                from decouple import config as dconfig
                openai_api_key = dconfig("OPENAI_API_KEY", default=None)
                if openai_api_key:
                    source = "python-decouple"
            except Exception:
                pass

    if not openai_api_key:
        die("OPENAI_API_KEY is not set. Put it in your .env or export it in your shell (or pass --key=...).")

    print(f"✅ Using key from: {source}")
    print(f"✅ Key fingerprint: {fingerprint(openai_api_key)}")

    # Optional org/project headers if you use them
    openai_org = os.getenv("OPENAI_ORG") or os.getenv("OPENAI_ORGANIZATION")
    # openai_project = os.getenv("OPENAI_PROJECT")
    if openai_org:
        print("✅ Org header set:", openai_org)
    # if openai_project:
    #     print("✅ Project header set:", openai_project)

    # --- Initialize client ---
    try:
        from openai import OpenAI
    except Exception as e:
        die(f"Failed to import openai: {e}")

    client_kwargs = {"api_key": openai_api_key}
    if openai_org:
        client_kwargs["organization"] = openai_org
    # if openai_project:
    #     client_kwargs["project"] = openai_project

    client = OpenAI(**client_kwargs)

    # --- Embeddings smoke test ---
    print("→ Embedding test...")
    try:
        e = client.embeddings.create(model=args.embedding_model, input="hello world")
        vec = e.data[0].embedding
        print("   OK, embedding length:", len(vec))
    except Exception as err:
        print("   ❌ Embedding error type:", type(err).__name__)
        try:
            # openai-python v1 returns rich errors; print useful bits if present
            msg = getattr(err, "message", None) or str(err)
            status = getattr(err, "status_code", None)
            body = getattr(err, "response", None)
            print("   status:", status)
            if body is not None:
                try:
                    print("   body:", json.dumps(body, indent=2) if isinstance(body, dict) else body)
                except Exception:
                    print("   body:", body)
            print("   message:", msg)
        except Exception:
            print("   raw:", err)
        sys.exit(1)

    # --- Chat smoke test ---
    print("→ Chat test...")
    try:
        r = client.chat.completions.create(
            model=args.chat_model,
            messages=[{"role": "user", "content": "Say 'pong' if you can read this."}],
        )
        content = r.choices[0].message.content
        print("   OK:", content)
    except Exception as err:
        print("   ❌ Chat error type:", type(err).__name__)
        try:
            msg = getattr(err, "message", None) or str(err)
            status = getattr(err, "status_code", None)
            body = getattr(err, "response", None)
            print("   status:", status)
            if body is not None:
                try:
                    print("   body:", json.dumps(body, indent=2) if isinstance(body, dict) else body)
                except Exception:
                    print("   body:", body)
            print("   message:", msg)
        except Exception:
            print("   raw:", err)
        sys.exit(1)

    print("✅ All good.")

if __name__ == "__main__":
    main()
