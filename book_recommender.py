"""Local book catalog parsing and retrieval for grounded recommendations."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


BOOKS_DIR = Path(__file__).with_name("books")
ENTRY_PATTERN = re.compile(
    r"^## (?P<id>\d{3})\. 《(?P<title>.+?)》\s*$"
    r"(?P<body>.*?)(?=^## \d{3}\. 《|\Z)",
    re.MULTILINE | re.DOTALL,
)
FIELD_PATTERN = re.compile(r"^- \*\*(?P<name>.+?)\*\*：(?P<value>.*)$", re.MULTILINE)
TOPIC_PATTERN = re.compile(r"^# (?P<topic>.+)$", re.MULTILINE)

QUERY_EXPANSIONS = {
    "资源": ["资源", "谈判", "利益", "说服", "向上汇报", "跨部门"],
    "决策": ["决策", "说服", "影响力", "汇报", "结构化表达"],
    "冲突": ["冲突", "困难对话", "心理安全", "降温", "情绪", "谈判"],
    "反馈": ["反馈", "绩效", "防御心理", "成长", "直接挑战"],
    "汇报": ["汇报", "结构化表达", "结论先行", "说服", "演示"],
    "谈判": ["谈判", "利益", "共同收益", "拒绝处理", "战术同理心"],
    "跨部门": ["跨部门", "协作", "利益", "冲突", "谈判"],
    "领导": ["领导", "向上汇报", "影响力", "权力", "授权"],
    "焦虑": ["焦虑", "情绪", "降温", "心理安全", "倾听"],
    "关系": ["关系", "信任", "倾听", "同理心", "沟通"],
    "数据": ["数据", "结构化表达", "决策", "汇报"],
    "创新": ["创新", "变革", "说服", "愿景"],
}
DEFAULT_TERMS = ["沟通", "表达", "对话"]


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    english_title: str
    author: str
    tags: str
    summary: str
    recommended_scenario: str
    topic: str

    def for_prompt(self) -> dict[str, str]:
        return asdict(self)


def _detail_files(books_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in books_dir.glob("[0-9][0-9]-*.md")
        if path.name[:2] not in {"00", "99"}
    )


def _field(fields: dict[str, str], name: str) -> str:
    return fields.get(name, "").strip()


@lru_cache(maxsize=4)
def load_books(books_dir: Path = BOOKS_DIR) -> tuple[Book, ...]:
    """Parse the ten detailed Markdown catalogs into structured books."""
    books: list[Book] = []
    for path in _detail_files(books_dir):
        text = path.read_text(encoding="utf-8")
        topic_match = TOPIC_PATTERN.search(text)
        topic = topic_match.group("topic").strip() if topic_match else path.stem
        for match in ENTRY_PATTERN.finditer(text):
            fields = {
                item.group("name").strip(): item.group("value").strip()
                for item in FIELD_PATTERN.finditer(match.group("body"))
            }
            books.append(
                Book(
                    id=match.group("id"),
                    title=match.group("title").strip(),
                    english_title=_field(fields, "English Title"),
                    author=_field(fields, "作者"),
                    tags=_field(fields, "标签"),
                    summary=_field(fields, "简介"),
                    recommended_scenario=_field(fields, "推荐场景"),
                    topic=topic,
                )
            )
    return tuple(books)


def _query_text(form_data: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in form_data.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts)


def _query_terms(form_data: dict[str, Any]) -> set[str]:
    query = _query_text(form_data)
    terms = set(DEFAULT_TERMS)
    for trigger, expansions in QUERY_EXPANSIONS.items():
        if trigger in query:
            terms.add(trigger)
            terms.update(expansions)
    return terms


def _score(book: Book, terms: set[str]) -> int:
    score = 0
    for term in terms:
        score += 8 * book.tags.count(term)
        score += 4 * book.title.count(term)
        score += 3 * book.recommended_scenario.count(term)
        score += book.summary.count(term)
        score += book.topic.count(term)
    if book.topic.startswith("三、沟通"):
        score += 3
    return score


def recommend_candidates(form_data: dict[str, Any], limit: int = 12) -> list[dict[str, str]]:
    """Return a small, grounded candidate set for the model to choose from."""
    terms = _query_terms(form_data)
    ranked = sorted(load_books(), key=lambda book: (-_score(book, terms), book.id))
    return [book.for_prompt() for book in ranked[:limit]]


def ground_recommendations(
    strategy: dict[str, Any],
    candidates: list[dict[str, str]],
) -> dict[str, Any]:
    """Keep model recommendations tied to local candidates and ensure 2-3 results."""
    catalog = {book["id"]: book for book in candidates}
    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()

    suggestions = strategy.get("recommended_books", [])
    if not isinstance(suggestions, list):
        suggestions = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            continue
        book_id = str(suggestion.get("id", ""))
        if book_id not in catalog or book_id in selected_ids:
            continue
        book = catalog[book_id]
        selected.append(
            {
                "id": book["id"],
                "title": book["title"],
                "author": book["author"],
                "reason": str(suggestion.get("reason", "")).strip()
                or "这本书与当前沟通情境相关，可用于进一步准备和复盘。",
                "reading_focus": str(suggestion.get("reading_focus", "")).strip() or book["tags"],
            }
        )
        selected_ids.add(book_id)
        if len(selected) == 3:
            break

    for book in candidates:
        if len(selected) >= 2:
            break
        if book["id"] in selected_ids:
            continue
        selected.append(
            {
                "id": book["id"],
                "title": book["title"],
                "author": book["author"],
                "reason": "这本书与当前沟通情境相关，可用于进一步准备和复盘。",
                "reading_focus": book["tags"],
            }
        )
        selected_ids.add(book["id"])

    strategy["recommended_books"] = selected
    return strategy
