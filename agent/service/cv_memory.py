"""
CV Memory (cv_memory.py)
------------------------
Builds and stores long-term "memory" about a candidate from an uploaded CV, and
provides the short-term conversation window used to always feed the agent only the
last few messages.

- LLM-based extraction of exact keywords + structured knowledge from the CV text.
- Persistence of that knowledge per user (via service.db.cv_memory table).
- A `langchain_classic.memory.ConversationBufferWindowMemory` helper that trims the
  running chat history to the most recent messages.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_classic.memory import ConversationBufferWindowMemory

from agent.llm.load_model import llm
from agent.service.db import save_cv_memory, get_cv_memory

logger = logging.getLogger(__name__)

# Always feed the agent only the last N messages of the running conversation.
HISTORY_WINDOW = 3

# Marker that identifies the CV memory SystemMessage inside a message list, so
# downstream nodes can pull the candidate knowledge back out of state["messages"].
CV_MEMORY_PREFIX = "CANDIDATE CV ON FILE"

_EXTRACTION_PROMPT = """You are an expert technical recruiter and CV parser.
Read the candidate CV below and extract a structured profile.

Return ONLY a single valid JSON object (no markdown, no backticks, no commentary)
with exactly these keys:
{{
  "name": "candidate full name or empty string",
  "title": "current/most-recent job title or empty string",
  "summary": "2-3 sentence professional summary",
  "keywords": ["exact, important keywords: technologies, tools, languages, domains, certifications"],
  "skills": ["distinct technical and soft skills"],
  "experience": ["one short line per role: 'Title @ Company (years) - key work'"],
  "education": ["degree, institution, year"],
  "years_experience": "total years of experience as a string, or empty string"
}}

Keep "keywords" precise and de-duplicated — these are used for search/matching.

CV TEXT:
\"\"\"
{cv_text}
\"\"\"
"""


async def extract_cv_knowledge(cv_text: str) -> Dict[str, Any]:
    """Use the LLM to extract structured knowledge + exact keywords from CV text."""
    # Guard against very large CVs blowing the context window.
    snippet = cv_text[:12000]
    prompt = _EXTRACTION_PROMPT.format(cv_text=snippet)

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        knowledge = _parse_json_object(content)
    except Exception as e:
        logger.error(f"[cv_memory] LLM extraction failed: {e}")
        knowledge = {}

    # Normalise shape so downstream code can rely on it.
    knowledge.setdefault("name", "")
    knowledge.setdefault("title", "")
    knowledge.setdefault("summary", "")
    knowledge.setdefault("keywords", [])
    knowledge.setdefault("skills", [])
    knowledge.setdefault("experience", [])
    knowledge.setdefault("education", [])
    knowledge.setdefault("years_experience", "")
    return knowledge


def _parse_json_object(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    candidate = match.group(0) if match else text
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


async def ingest_cv(user_id: str, file_name: str, file_path: str, cv_text: str) -> Dict[str, Any]:
    """
    Extract knowledge from a CV and persist it as the user's CV memory.
    Returns the stored knowledge dict (including keywords and summary).
    """
    knowledge = await extract_cv_knowledge(cv_text)
    keywords: List[str] = [str(k) for k in knowledge.get("keywords", []) if k]
    summary = knowledge.get("summary", "") or knowledge.get("title", "")

    save_cv_memory(
        user_id=user_id,
        file_name=file_name,
        file_path=file_path,
        keywords=keywords,
        knowledge=knowledge,
        summary=summary,
    )
    logger.info(
        f"[cv_memory] Stored CV memory for user={user_id} "
        f"({len(keywords)} keywords, file={file_name})"
    )
    return {"file_name": file_name, "keywords": keywords, "knowledge": knowledge, "summary": summary}


def cv_memory_system_message(user_id: str) -> Optional[SystemMessage]:
    """
    Build a SystemMessage carrying the candidate's CV knowledge so the agent can
    answer from it. Returns None if the user has no CV on file.
    """
    mem = get_cv_memory(user_id)
    if not mem:
        return None

    knowledge = mem.get("knowledge", {})
    lines = [
        f"{CV_MEMORY_PREFIX} — use this knowledge to answer questions about the candidate.",
        f"File: {mem.get('file_name', '')}",
    ]
    if knowledge.get("name"):
        lines.append(f"Name: {knowledge['name']}")
    if knowledge.get("title"):
        lines.append(f"Title: {knowledge['title']}")
    if knowledge.get("years_experience"):
        lines.append(f"Years of experience: {knowledge['years_experience']}")
    if knowledge.get("summary"):
        lines.append(f"Summary: {knowledge['summary']}")
    if mem.get("keywords"):
        lines.append("Keywords: " + ", ".join(mem["keywords"]))
    if knowledge.get("skills"):
        lines.append("Skills: " + ", ".join(str(s) for s in knowledge["skills"]))
    if knowledge.get("experience"):
        lines.append("Experience:\n- " + "\n- ".join(str(x) for x in knowledge["experience"]))
    if knowledge.get("education"):
        lines.append("Education:\n- " + "\n- ".join(str(x) for x in knowledge["education"]))

    return SystemMessage(content="\n".join(lines))


def cv_message_from_history(messages: Sequence[BaseMessage]) -> Optional[SystemMessage]:
    """
    Pull the CV memory SystemMessage back out of a message list (it is injected by
    the chat service at the front of state["messages"]). Returns None if absent.

    Nodes rebuild their own LLM context instead of forwarding state["messages"]
    wholesale, so they use this to re-inject the candidate knowledge where it
    matters (tool reasoning and the final synthesis).
    """
    for m in messages or []:
        content = getattr(m, "content", "")
        if isinstance(m, SystemMessage) and isinstance(content, str) \
                and content.startswith(CV_MEMORY_PREFIX):
            return m
    return None


def window_messages(messages: Sequence[BaseMessage], k: int = HISTORY_WINDOW) -> List[BaseMessage]:
    """
    Return only the last `k` messages of the conversation, using
    langchain_classic's ConversationBufferWindowMemory as the windowing primitive.

    CV knowledge is injected separately (see `cv_memory_system_message`), so this
    only needs to trim the running chat history that is sent to the agent.
    """
    if not messages:
        return []

    memory = ConversationBufferWindowMemory(k=k, return_messages=True)
    for m in messages:
        memory.chat_memory.add_message(m)

    return memory.chat_memory.messages[-k:]
