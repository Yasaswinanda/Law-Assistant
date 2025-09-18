import os
import hashlib
from typing import Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

from processing import PDFProcessor
from retrieval import load_vector_store_or_raise
from agents import AgentOrchestrator

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
INDEX_DIR = os.environ.get("INDEX_DIR", "./index")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required")

# ---- Load persisted index (MUST exist) ----
vector_store = load_vector_store_or_raise(INDEX_DIR)  # raises if missing

pdf = PDFProcessor()
agent = AgentOrchestrator(
    gemini_api_key=GEMINI_API_KEY,
    vector_store=vector_store
)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        top_k = 6
        session_id: Optional[str] = None
        user_doc_text: Optional[str] = None

        if request.content_type and request.content_type.startswith("multipart/form-data"):
            msg = request.form.get("message", "").strip()
            session_id = request.form.get("session_id", None)
            f = request.files.get("user_pdf")
            if f and f.filename.lower().endswith(".pdf"):
                temp_path = os.path.join(UPLOAD_DIR, hashlib.md5(f.read()).hexdigest() + ".pdf")
                f.stream.seek(0)
                f.save(temp_path)
                pages = pdf.process_pdf(temp_path)
                os.remove(temp_path)
                user_doc_text = "\n\n".join([p["text"] for p in pages if p["text"]])
            else:
                user_doc_text = request.form.get("user_doc_text", None)
        else:
            data = request.get_json(force=True)
            msg = (data.get("message") or "").strip()
            session_id = data.get("session_id")
            user_doc_text = data.get("user_doc_text")
            top_k = int(data.get("top_k") or 6)

        if not msg:
            return jsonify({"error": "message is required"}), 400

        result = agent.answer(
            user_message=msg,
            session_id=session_id,
            user_doc_text=user_doc_text,
            top_k=top_k
        )
        return jsonify(result)
    except FileNotFoundError as e:
        # In case someone deletes the index after boot
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app.logger.exception("chat failed")
        return jsonify({"error": f"chat failed: {e}"}), 500

@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    try:
        data = request.get_json(force=True)
        msg = (data.get("message") or "").strip()
        session_id = data.get("session_id")
        user_doc_text = data.get("user_doc_text")
        top_k = int(data.get("top_k") or 6)

        if not msg:
            return jsonify({"error": "message is required"}), 400

        def gen():
            for event in agent.stream_answer(
                user_message=msg,
                session_id=session_id,
                user_doc_text=user_doc_text,
                top_k=top_k
            ):
                yield f"data: {event}\n\n"

        return Response(gen(), mimetype="text/event-stream")
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app.logger.exception("chat stream failed")
        return jsonify({"error": f"chat stream failed: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
