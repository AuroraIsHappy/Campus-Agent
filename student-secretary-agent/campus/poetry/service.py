"""SQLite-backed poetry workflow, migrated from the standalone poetry_agent.

The service deliberately has no ORM dependency.  It uses Campus' LLM runtime
when available and a deterministic local composer when CAMPUS_POETRY_MOCK=1.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from campus.runtime.paths import campus_home

POETRY_WORDS = ("写诗", "一首诗", "改诗", "诗歌", "诗句", "诗意", "写成诗", "润色这首")


def is_poetry_intent(text: str) -> bool:
    value = (text or "").strip().lower()
    return any(word in value for word in POETRY_WORDS)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now() -> int:
    return int(time.time())


class PoetryService:
    def __init__(self, db_path: str | None = None) -> None:
        path = Path(db_path or os.path.join(campus_home(), "poetry.sqlite3"))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(path)
        self.upload_dir = Path(campus_home()) / "poetry_uploads"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, status TEXT NOT NULL, observation TEXT NOT NULL,
              analysis TEXT NOT NULL DEFAULT '{}', context TEXT NOT NULL DEFAULT '{}',
              question_count INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL, error TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
              content TEXT NOT NULL, created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS poems (
              id TEXT PRIMARY KEY, session_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
              content TEXT NOT NULL, themes TEXT NOT NULL DEFAULT '[]', images TEXT NOT NULL DEFAULT '[]',
              inspiration TEXT NOT NULL DEFAULT '{}', originality_risk TEXT NOT NULL DEFAULT 'low',
              finalized INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS poem_versions (
              id TEXT PRIMARY KEY, poem_id TEXT NOT NULL, version INTEGER NOT NULL,
              content TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_type TEXT NOT NULL,
              sha256 TEXT UNIQUE NOT NULL, path TEXT NOT NULL, status TEXT NOT NULL,
              content TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', deleted_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS poet_profiles (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0,
              profile TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, deleted_at INTEGER
            );
            """)

    @staticmethod
    def _loads(value: str, default: Any) -> Any:
        try:
            return json.loads(value)
        except Exception:
            return default

    def _session(self, row: sqlite3.Row, db: sqlite3.Connection) -> dict[str, Any]:
        messages = db.execute(
            "SELECT role,content,created_at FROM messages WHERE session_id=? ORDER BY created_at,id", (row["id"],)
        ).fetchall()
        return {
            "id": row["id"], "status": row["status"], "observation": row["observation"],
            "analysis": self._loads(row["analysis"], {}), "context": self._loads(row["context"], {}),
            "question_count": row["question_count"], "error": row["error"],
            "messages": [dict(m) for m in messages],
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            return self._session(row, db) if row else None

    def create_session(self, observation: str, context: dict | None = None) -> dict[str, Any]:
        observation = observation.strip()
        if len(observation) < 2:
            raise ValueError("请先告诉我一个你刚刚注意到的具体瞬间。")
        session_id, now = _id("poetry"), _now()
        enough = len(observation) >= 16 or any(x in observation for x in ("灯", "雨", "风", "声音", "颜色", "影", "门", "手"))
        analysis = {"enough_detail": enough, "themes": self._themes(observation), "images": self._images(observation)}
        status = "ready" if enough else "collecting"
        with self._connect() as db:
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)", (
                session_id, status, observation, json.dumps(analysis, ensure_ascii=False),
                json.dumps(context or {}, ensure_ascii=False), 0, now, now, ""))
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?)", (_id("msg"), session_id, "user", observation, now))
            if not enough:
                question = "那个瞬间里，最清楚的颜色、声音或动作是什么？"
                db.execute("INSERT INTO messages VALUES(?,?,?,?,?)", (_id("msg"), session_id, "assistant", question, now + 1))
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            return self._session(row, db)

    def add_message(self, session_id: str, content: str, skip: bool = False) -> dict[str, Any]:
        now = _now()
        with self._connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                raise KeyError("诗歌会话不存在")
            value = content.strip() or "我想直接开始"
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?)", (_id("msg"), session_id, "user", value, now))
            db.execute("UPDATE sessions SET status='ready',question_count=question_count+1,updated_at=? WHERE id=?", (now, session_id))
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            return self._session(row, db)

    def _material(self, db: sqlite3.Connection, session_id: str) -> str:
        rows = db.execute("SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY created_at,id", (session_id,)).fetchall()
        return "\n".join(r[0] for r in rows)

    @staticmethod
    def _themes(text: str) -> list[str]:
        pairs = (("雨", "雨夜"), ("灯", "灯光"), ("宿舍", "归途"), ("想", "思念"), ("晚", "夜晚"), ("风", "季节"))
        result = [theme for word, theme in pairs if word in text]
        return result[:4] or ["日常", "时间"]

    @staticmethod
    def _images(text: str) -> list[str]:
        words = ("雨", "灯", "门", "伞", "窗", "风", "影子", "便利店", "宿舍", "月亮")
        return [word for word in words if word in text][:6]

    def _compose_local(self, material: str) -> dict[str, Any]:
        images = self._images(material)
        anchor = images[0] if images else "这一刻"
        detail = next((line.strip("。 ，") for line in material.splitlines() if line.strip()), "今天留下了一点声音")
        content = f"{detail}\n\n{anchor}没有催我赶路\n只是把沉默放低了一些\n\n我从它身边经过\n带走一小块未熄的夜"
        return {"title": f"{anchor}之后", "content": content, "themes": self._themes(material), "images": images,
                "notes": "保留具体物件，让情绪从动作和停顿中出现。"}

    def _compose_with_llm(self, material: str, instruction: str = "") -> dict[str, Any]:
        if os.environ.get("CAMPUS_POETRY_MOCK", "").lower() in ("1", "true"):
            return self._compose_local(material)
        try:
            from campus.runtime.llm_turn import ask_llm, extract_json
            prompt = f"""你是诗隙，一位克制的现代汉语诗歌共同作者。只使用用户真实提供的生活细节，不虚构经历，不模仿具体诗句。{instruction}
请只返回 JSON：{{"title":"", "content":"", "themes":[], "images":[], "notes":""}}
生活素材：\n{material}"""
            raw, _rc = ask_llm(prompt)
            data = extract_json(raw)
            if isinstance(data, dict) and data.get("content"):
                return data
        except Exception:
            if os.environ.get("CAMPUS_POETRY_REQUIRE_LLM", "").lower() in ("1", "true"):
                raise RuntimeError("诗歌 Agent 暂时无法连接 LLM，请检查 Campus 的模型配置。")
        return self._compose_local(material)

    @staticmethod
    def originality(text: str) -> dict[str, Any]:
        normalized = re.sub(r"\s+", "", text)
        repeated = max((normalized.count(normalized[i:i+8]) for i in range(max(0, len(normalized)-7))), default=1)
        risk = "high" if repeated >= 4 else "medium" if repeated >= 3 else "low"
        return {"risk": risk, "explanation": "检测到较多重复片段" if risk != "low" else "未发现明显的内部重复风险"}

    def compose(self, session_id: str) -> dict[str, Any]:
        with self._connect() as db:
            session = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not session:
                raise KeyError("诗歌会话不存在")
            material = self._material(db, session_id)
            result = self._compose_with_llm(material)
            check = self.originality(result["content"])
            now = _now()
            poem = db.execute("SELECT * FROM poems WHERE session_id=?", (session_id,)).fetchone()
            poem_id = poem["id"] if poem else _id("poem")
            if poem:
                db.execute("UPDATE poems SET title=?,content=?,themes=?,images=?,inspiration=?,originality_risk=?,updated_at=? WHERE id=?", (
                    result["title"], result["content"], json.dumps(result.get("themes", []), ensure_ascii=False),
                    json.dumps(result.get("images", []), ensure_ascii=False), json.dumps({"notes": result.get("notes", ""), "user_material": material}, ensure_ascii=False), check["risk"], now, poem_id))
            else:
                db.execute("INSERT INTO poems VALUES(?,?,?,?,?,?,?,?,?,?,?)", (poem_id, session_id, result["title"], result["content"],
                    json.dumps(result.get("themes", []), ensure_ascii=False), json.dumps(result.get("images", []), ensure_ascii=False),
                    json.dumps({"notes": result.get("notes", ""), "user_material": material}, ensure_ascii=False), check["risk"], 0, now, now))
            version = db.execute("SELECT COUNT(*) FROM poem_versions WHERE poem_id=?", (poem_id,)).fetchone()[0] + 1
            db.execute("INSERT INTO poem_versions VALUES(?,?,?,?,?,?)", (_id("ver"), poem_id, version, result["content"], result.get("notes", ""), now))
            db.execute("UPDATE sessions SET status='review',updated_at=? WHERE id=?", (now, session_id))
            return self.get_poem(poem_id, db)

    def revise(self, session_id: str, content: str | None, instruction: str) -> dict[str, Any]:
        with self._connect() as db:
            poem = db.execute("SELECT * FROM poems WHERE session_id=?", (session_id,)).fetchone()
            if not poem:
                raise ValueError("请先生成诗稿。")
            source = content or poem["content"]
            result = self._compose_with_llm(source, f"编辑要求：{instruction or '语言更克制，保留具体细节'}。这是编辑任务，保留原诗核心意象。")
            check, now = self.originality(result["content"]), _now()
            db.execute("UPDATE poems SET title=?,content=?,originality_risk=?,updated_at=? WHERE id=?", (result.get("title") or poem["title"], result["content"], check["risk"], now, poem["id"]))
            version = db.execute("SELECT COUNT(*) FROM poem_versions WHERE poem_id=?", (poem["id"],)).fetchone()[0] + 1
            db.execute("INSERT INTO poem_versions VALUES(?,?,?,?,?,?)", (_id("ver"), poem["id"], version, result["content"], instruction, now))
            return self.get_poem(poem["id"], db)

    def finalize(self, session_id: str, content: str | None = None, accept_medium: bool = False) -> dict[str, Any]:
        with self._connect() as db:
            poem = db.execute("SELECT * FROM poems WHERE session_id=?", (session_id,)).fetchone()
            if not poem:
                raise ValueError("请先生成诗稿。")
            final_content = content or poem["content"]
            risk = self.originality(final_content)["risk"]
            if risk == "high" or (risk == "medium" and not accept_medium):
                raise ValueError("原创性风险需要处理或明确确认。")
            now = _now()
            db.execute("UPDATE poems SET content=?,originality_risk=?,finalized=1,updated_at=? WHERE id=?", (final_content, risk, now, poem["id"]))
            db.execute("UPDATE sessions SET status='finalized',updated_at=? WHERE id=?", (now, session_id))
            result = self.get_poem(poem["id"], db)
        self._remember(result)
        return result

    def _remember(self, poem: dict[str, Any]) -> None:
        try:
            from campus.memory.json_store import JsonFileStore
            from campus.memory.types import MemoryRecord, KNOWLEDGE
            store = JsonFileStore()
            store.add(MemoryRecord(id=_id("memory"), layer=KNOWLEDGE,
                key=f"poem/{poem['id']}", content=f"诗歌《{poem['title']}》：{poem['content']}",
                metadata={"kind": "poem", "poem_id": poem["id"], "themes": poem["themes"]}, created_at=_now()))
        except Exception:
            pass

    def get_poem(self, poem_id: str, db: sqlite3.Connection | None = None) -> dict[str, Any]:
        own = db is None
        db = db or self._connect()
        try:
            row = db.execute("SELECT * FROM poems WHERE id=?", (poem_id,)).fetchone()
            if not row:
                raise KeyError("诗稿不存在")
            versions = db.execute("SELECT version,content,notes,created_at FROM poem_versions WHERE poem_id=? ORDER BY version", (poem_id,)).fetchall()
            return {"id": row["id"], "session_id": row["session_id"], "title": row["title"], "content": row["content"],
                    "themes": self._loads(row["themes"], []), "images": self._loads(row["images"], []),
                    "inspiration": self._loads(row["inspiration"], {}), "originality_risk": row["originality_risk"],
                    "finalized": bool(row["finalized"]), "version": len(versions), "versions": [dict(v) for v in versions]}
        finally:
            if own:
                db.close()

    def poem_for_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT id FROM poems WHERE session_id=?", (session_id,)).fetchone()
            return self.get_poem(row["id"], db) if row else None

    def list_poems(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            ids = db.execute("SELECT id FROM poems ORDER BY updated_at DESC").fetchall()
            return [self.get_poem(row["id"], db) for row in ids]

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM poet_profiles WHERE deleted_at IS NULL ORDER BY created_at DESC").fetchall()]

    def save_profile(self, name: str, profile_id: str | None = None, active: bool = False) -> dict[str, Any]:
        with self._connect() as db:
            if profile_id:
                row = db.execute("SELECT * FROM poet_profiles WHERE id=? AND deleted_at IS NULL", (profile_id,)).fetchone()
                if not row:
                    raise KeyError("诗人资料不存在")
                if active:
                    db.execute("UPDATE poet_profiles SET active=0")
                db.execute("UPDATE poet_profiles SET name=?,active=? WHERE id=?", (name.strip() or row["name"], int(active), profile_id))
            else:
                profile_id = _id("poet")
                if active:
                    db.execute("UPDATE poet_profiles SET active=0")
                db.execute("INSERT INTO poet_profiles VALUES(?,?,?,?,?,NULL)", (profile_id, name.strip() or "未命名诗人", int(active), "{}", _now()))
            return dict(db.execute("SELECT * FROM poet_profiles WHERE id=?", (profile_id,)).fetchone())

    def delete_profile(self, profile_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("UPDATE poet_profiles SET deleted_at=?,active=0 WHERE id=?", (_now(), profile_id))
            return cur.rowcount > 0

    def ingest_document(self, filename: str, data: bytes, max_mb: int = 20) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".md"}:
            raise ValueError("仅支持 PDF、DOCX、TXT、MD")
        if len(data) > max_mb * 1024 * 1024:
            raise ValueError("文件超过大小限制")
        digest = hashlib.sha256(data).hexdigest()
        with self._connect() as db:
            existing = db.execute("SELECT * FROM documents WHERE sha256=?", (digest,)).fetchone()
            if existing:
                return {**dict(existing), "deduplicated": True}
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        path = self.upload_dir / f"{digest}{suffix}"
        path.write_bytes(data)
        document_id, status, content, error = _id("doc"), "ready", "", ""
        try:
            if suffix in {".txt", ".md"}:
                content = data.decode("utf-8")
            elif suffix == ".docx":
                from docx import Document
                content = "\n".join(p.text for p in Document(path).paragraphs)
            else:
                from pypdf import PdfReader
                content = "\n".join((page.extract_text() or "") for page in PdfReader(path).pages)
            if not content.strip():
                raise ValueError("文档没有可提取文本；扫描型 PDF 暂不支持 OCR")
        except Exception as exc:
            status, error = "failed", str(exc)
        with self._connect() as db:
            db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,NULL)", (document_id, filename, suffix[1:], digest, str(path), status, content, error))
        return {"id": document_id, "filename": filename, "status": status, "error": error, "deduplicated": False}

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(r) for r in db.execute("SELECT id,filename,file_type,status,error FROM documents WHERE deleted_at IS NULL").fetchall()]

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("UPDATE documents SET deleted_at=? WHERE id=?", (_now(), document_id))
            return cur.rowcount > 0


def poem_canvas(poem: dict[str, Any] | None, status: str) -> dict[str, Any]:
    if not poem:
        return {"type": "empty", "title": "诗稿尚未出现", "data": {"status": status}, "editable": False, "actions": []}
    actions = [] if poem["finalized"] else ["revise", "finalize"]
    return {"type": "poem", "title": poem["title"], "data": poem, "editable": not poem["finalized"], "actions": actions}
