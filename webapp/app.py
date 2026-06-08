"""
脑退行性疾病知识库 — 网页查询系统
Flask backend with Claude API RAG
"""

import os
import re
import json
from pathlib import Path
from flask import Flask, request, jsonify, Response, render_template, stream_with_context
import frontmatter
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────
KB_DIR = Path(__file__).resolve().parent.parent  # neurodegenerative-diseases-kb/
DISEASES_DIR = KB_DIR / "diseases"
TOPICS_DIR = KB_DIR / "topics"


def _load_api_config():
    """Load API credentials from env or existing Claude config."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # Fallback: read from Claude Code settings
    if not api_key:
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
                env = settings.get("env", {})
                api_key = api_key or env.get("ANTHROPIC_AUTH_TOKEN")
                base_url = base_url or env.get("ANTHROPIC_BASE_URL")
                model = os.getenv("ANTHROPIC_MODEL") or env.get("ANTHROPIC_MODEL", model)
            except Exception:
                pass

    return api_key, base_url, model


API_KEY, BASE_URL, MODEL = _load_api_config()
CLIENT = Anthropic(api_key=API_KEY, base_url=BASE_URL or None)

SYSTEM_PROMPT = """你是一个脑退行性疾病知识库助手。你的回答必须严格基于下方提供的知识库内容。

规则：
1. 只使用「参考资料」中提供的信息来回答问题
2. 如果知识库中有答案，请详细、准确地引用，使用 Markdown 格式让回答清晰易读
3. 如果知识库中信息不完整，可以如实说明局限性，但不要编造
4. 如果知识库完全没有相关信息，请诚实说明："本知识库暂未收录这方面的详细内容。"
5. 回答时优先使用中文，专业术语附带英文原名
6. 当引用具体数据时，注明出处是哪个疾病文件"""


# ── Knowledge Base Loader ──────────────────────────────────────

def load_knowledge_base():
    """Load all markdown files into memory with parsed frontmatter."""
    documents = []

    md_files = []
    if DISEASES_DIR.exists():
        md_files.extend(DISEASES_DIR.glob("*.md"))
    if TOPICS_DIR.exists():
        md_files.extend(TOPICS_DIR.glob("*.md"))
    # Also load glossary and README
    for f in [KB_DIR / "glossary.md", KB_DIR / "README.md"]:
        if f.exists():
            md_files.append(f)

    for filepath in md_files:
        try:
            post = frontmatter.load(filepath)
            doc = {
                "filename": filepath.name,
                "path": str(filepath.relative_to(KB_DIR)),
                "title": post.get("title", filepath.stem),
                "aliases": post.get("aliases", []),
                "tags": post.get("tags", []),
                "core_protein": post.get("core_protein", []),
                "type": post.get("type", ""),
                "content": post.content,
                "frontmatter": dict(post.metadata),
            }
            documents.append(doc)
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")

    print(f"Loaded {len(documents)} documents from knowledge base")
    return documents


DOCUMENTS = load_knowledge_base()


# ── Search / Retrieval ─────────────────────────────────────────

def tokenize(text):
    """Simple Chinese + English tokenizer."""
    # Split on whitespace and punctuation for English
    # Keep Chinese characters as individual tokens (bigrams would be better but keep simple)
    tokens = re.findall(r"[一-鿿]+|[a-zA-Z0-9]+", text.lower())
    return set(tokens)


def search(query, top_n=5):
    """Search documents by multi-dimensional keyword matching."""
    query_tokens = tokenize(query)
    query_lower = query.lower()

    scored = []
    for doc in DOCUMENTS:
        score = 0.0

        # Aliases match (weight ×3)
        for alias in doc["aliases"]:
            alias_lower = alias.lower()
            if alias_lower in query_lower:
                score += 3.0
            # Partial token match
            for qt in query_tokens:
                if qt in alias_lower:
                    score += 2.0

        # Tags match (weight ×1.5)
        for tag in doc["tags"]:
            tag_lower = tag.lower()
            if any(qt in tag_lower or tag_lower in qt for qt in query_tokens):
                score += 1.5

        # Content keyword match (weight ×1)
        content_lower = doc["content"].lower()
        for qt in query_tokens:
            count = content_lower.count(qt)
            if count > 0:
                score += min(count, 10) * 0.5  # cap per term to avoid bias

        # Title match bonus
        title_lower = doc["title"].lower()
        for qt in query_tokens:
            if qt in title_lower:
                score += 2.0

        if score > 0:
            scored.append((score, doc))

    # Sort by score descending, take top_n
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_n]]


def build_context(docs):
    """Build context string from retrieved documents."""
    parts = []
    for doc in docs:
        header = f"## [{doc['title']}] ({doc['path']})\n"
        # Each disease file is ~80-140 lines. Use full content for best RAG.
        # Total KB is ~2000 lines across 18 files, so 5 full docs is ~500-700 lines — well within context.
        parts.append(header + doc["content"])
    return "\n\n---\n\n".join(parts)


# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    """Pure keyword search endpoint (no AI, no cost)."""
    data = request.get_json()
    query_text = data.get("question", "").strip()
    if not query_text:
        return jsonify({"error": "问题不能为空"}), 400

    results = search(query_text, top_n=5)
    return jsonify({
        "results": [
            {
                "title": doc["title"],
                "path": doc["path"],
                "aliases": doc["aliases"],
                "tags": doc["tags"],
                "snippet": doc["content"][:300],
            }
            for doc in results
        ]
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Chat endpoint with Claude-powered RAG, streaming via SSE."""
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    # Retrieve relevant documents
    docs = search(question, top_n=5)
    if not docs:
        # Fallback: include glossary + README if no relevant docs found
        docs = [d for d in DOCUMENTS if d["filename"] in ("glossary.md", "README.md")]

    context = build_context(docs)

    def generate():
        try:
            stream = CLIENT.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"<参考资料>\n{context}\n</参考资料>\n\n用户问题: {question}\n\n请基于参考资料回答。",
                    }
                ],
                stream=True,
            )

            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield f"data: {json.dumps({'text': event.delta.text})}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/chat/sync", methods=["POST"])
def api_chat_sync():
    """Non-streaming chat endpoint — works through any proxy/tunnel."""
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    # Retrieve relevant documents
    docs = search(question, top_n=5)
    if not docs:
        docs = [d for d in DOCUMENTS if d["filename"] in ("glossary.md", "README.md")]

    context = build_context(docs)

    try:
        message = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"<参考资料>\n{context}\n</参考资料>\n\n用户问题: {question}\n\n请基于参考资料回答。",
                }
            ],
            stream=False,
        )

        # Handle both TextBlock and ThinkingBlock from API
        text_blocks = [b for b in message.content if b.type == "text"]
        answer = text_blocks[0].text if text_blocks else "未能获取回答。"
        return jsonify({
            "answer": answer,
            "sources": [{"title": d["title"], "path": d["path"]} for d in docs],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/diseases", methods=["GET"])
def api_diseases():
    """List all diseases with metadata (for sidebar/browsing)."""
    diseases = [
        {
            "title": doc["title"],
            "path": doc["path"],
            "aliases": doc["aliases"],
            "tags": doc["tags"],
            "core_protein": doc.get("core_protein", []),
        }
        for doc in DOCUMENTS
        if doc.get("type") == "disease"
    ]
    return jsonify({"diseases": diseases})


# ── Health check ────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "documents": len(DOCUMENTS)})


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    is_debug = os.getenv("FLASK_DEBUG", "0") == "1"

    if not API_KEY:
        print("WARNING: No ANTHROPIC_API_KEY configured!")
        print("  Set it via environment variable or .env file.")

    print(f"\n{'='*60}")
    print(f"  脑退行性疾病知识库查询系统")
    print(f"  本地访问: http://localhost:{port}")
    print(f"  已加载 {len(DOCUMENTS)} 个文档")
    print(f"  API: {'已配置' if API_KEY else '未配置!'}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=is_debug)
