"""
Search of the indexed files of The Smarter Project's repositories.

:func:`search_files` ranks the files of one or more repositories for a query, in the
database, without embeddings:

- The query is split into at most :data:`MAX_TERMS` terms. A quoted phrase is one term, and
  so is an identifier such as ``smarter_settings.environment_platform_domain``. Common
  English words are dropped.
- A file is a candidate if its path or content contains any of the terms.
- Each term is weighted by how rare it is among the files searched, its inverse document
  frequency, so that a rare identifier counts for more than a common word.
- A file's score adds up, for each term, a bonus for containing it, its number of
  occurrences, capped at :data:`MAX_COUNTED_OCCURRENCES` so that long files do not win by
  length alone, and bonuses for matching the file's path and title.

Occurrences are counted in SQL, as ``(LENGTH(LOWER(content)) - LENGTH(REPLACE(LOWER(content), term, ''))) / LENGTH(term)``,
which every database that Django supports can evaluate. Only the best files are then read,
to extract their matching lines.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import math
import re
from functools import reduce
from operator import or_
from typing import Optional, Sequence

from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Cast, Least, Length, Lower, Replace
from pydantic import BaseModel, ConfigDict, Field

from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndexStatus,
)
from smarter.apps.mcpserver.repositories import ProjectSource

MAX_TERMS = 8
MIN_TERM_LENGTH = 2
MAX_COUNTED_OCCURRENCES = 10
PRESENCE_WEIGHT = 4.0
PATH_WEIGHT = 6.0
TITLE_WEIGHT = 4.0
MAX_LINES_PER_HIT = 6
MAX_LINE_LENGTH = 240
CONTEXT_LINES_BEFORE = 2
CONTEXT_LINES_AFTER = 6
MAX_SNIPPET_CHARACTERS = 900

TERM_PATTERN = re.compile(r'"([^"]+)"|([A-Za-z0-9_][A-Za-z0-9_./:-]*[A-Za-z0-9_]|[A-Za-z0-9_])')
STOPWORDS = frozenset("""
    a an and are as at be by can do does for from has have how i in is it its me my of on or our
    the this that to was what when where which who why will with you your about into there their
    then than so if not no yes use used using show tell find get explain
    """.split())


class SearchLine(BaseModel):
    """A line of a file, with its line number."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int = Field(description="The line number, from 1.")
    text: str


class SearchHit(BaseModel):
    """A file that matches a search."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    path: str
    kind: RepositoryFileKind
    title: str = ""
    score: float
    url: str = Field(description="The file's GitHub url, at the indexed commit, highlighting its matching lines.")
    documentation_url: Optional[str] = Field(
        default=None, description="The published documentation page of the file, if it is one."
    )
    lines: list[SearchLine] = Field(default_factory=list, description="The matching lines, and their context.")


def query_terms(query: str) -> list[str]:
    """
    Split a search query into lowercase terms.

    :param query: The query, e.g. ``how does "custom domain" verification work``.
    :returns: The terms, without duplicates or common words, e.g. ``["custom domain", "verification", "work"]``.
    """
    terms: list[str] = []
    for phrase, word in TERM_PATTERN.findall(query or ""):
        term = (phrase or word).strip().lower()
        if len(term) < MIN_TERM_LENGTH or (not phrase and term in STOPWORDS) or term in terms:
            continue
        terms.append(term)
        if len(terms) >= MAX_TERMS:
            break
    return terms


def occurrences(term: str) -> ExpressionWrapper:
    """Return the SQL expression of the number of times a lowercase term occurs in a file's content."""
    removed = Length(Lower("content")) - Length(Replace(Lower("content"), Value(term), Value("")))
    return ExpressionWrapper(Cast(removed, FloatField()) / Value(float(len(term))), output_field=FloatField())


def term_weights(queryset: QuerySet, terms: list[str]) -> dict[str, float]:
    """
    Return each term's inverse document frequency among the files of a queryset, in one query.

    :param queryset: The files searched.
    :param terms: The terms.
    :returns: Each term's weight, from 1 for a term in every file.
    """
    counts = queryset.aggregate(
        total=Count("id"),
        **{
            f"t{i}": Count("id", filter=Q(content__icontains=term) | Q(path__icontains=term))
            for i, term in enumerate(terms)
        },
    )
    total = counts["total"] or 0
    return {term: 1.0 + math.log((1 + total) / (1 + (counts[f"t{i}"] or 0))) for i, term in enumerate(terms)}


def score_expression(terms: list[str], weights: dict[str, float]):
    """Return the SQL expression of a file's score for the terms."""
    parts = []
    for term in terms:
        weight = weights[term]
        parts.append(
            Case(When(content__icontains=term, then=Value(PRESENCE_WEIGHT * weight)), default=Value(0.0))
            + Least(occurrences(term), Value(float(MAX_COUNTED_OCCURRENCES))) * Value(weight)
            + Case(When(path__icontains=term, then=Value(PATH_WEIGHT * weight)), default=Value(0.0))
            + Case(When(title__icontains=term, then=Value(TITLE_WEIGHT * weight)), default=Value(0.0))
        )
    return ExpressionWrapper(reduce(lambda a, b: a + b, parts), output_field=FloatField())


def clip(text: str) -> str:
    """Return a line, shortened to at most :data:`MAX_LINE_LENGTH` characters."""
    text = text.rstrip()
    return text if len(text) <= MAX_LINE_LENGTH else text[: MAX_LINE_LENGTH - 1] + "…"


def matching_lines(content: str, terms: list[str], kind: str) -> list[SearchLine]:
    """
    Return the lines of a file that best show why it matches.

    For code, these are the lines that contain the most terms. For documentation, they are a
    passage around the line that contains the most terms, so that the LLM reads a sentence
    in its context.

    :param content: The file's content.
    :param terms: The lowercase terms.
    :param kind: The file's kind.
    :returns: The lines, in order.
    """
    lines = content.splitlines()
    scored = []
    for i, line in enumerate(lines):
        lower = line.lower()
        matched = sum(1 for term in terms if term in lower)
        if matched:
            scored.append((matched, i))
    if not scored:
        return [SearchLine(number=i + 1, text=clip(line)) for i, line in enumerate(lines[:MAX_LINES_PER_HIT])]
    if kind == RepositoryFileKind.DOCUMENTATION:
        best = max(scored, key=lambda item: (item[0], -item[1]))[1]
        start, end = max(0, best - CONTEXT_LINES_BEFORE), min(len(lines), best + CONTEXT_LINES_AFTER + 1)
        passage, characters = [], 0
        for i in range(start, end):
            characters += len(lines[i])
            if characters > MAX_SNIPPET_CHARACTERS and passage:
                break
            passage.append(SearchLine(number=i + 1, text=clip(lines[i])))
        return passage
    best_lines = sorted(
        sorted(scored, key=lambda item: (-item[0], item[1]))[:MAX_LINES_PER_HIT], key=lambda item: item[1]
    )
    return [SearchLine(number=i + 1, text=clip(lines[i])) for _, i in best_lines]


def search_files(
    repositories: Sequence[ProjectSource],
    query: str,
    kind: Optional[str] = None,
    path: Optional[str] = None,
    limit: int = 10,
) -> list[SearchHit]:
    """
    Search the indexed files of one or more repositories.

    :param repositories: The repositories to search, or the blog.
    :param query: The query.
    :param kind: Only documentation, or only code. Defaults to both.
    :param path: Only files under this folder, or with this path prefix, e.g. ``smarter/smarter/apps/llmclient``.
    :param limit: The maximum number of hits.
    :returns: The best hits, best first. Empty if the query has no terms, or nothing matches.

    **Example usage**::

        hits = search_files([get_repository("smarter")], "custom domain verification", kind="documentation")
        hits[0].documentation_url
    """
    terms = query_terms(query)
    if not terms or not repositories:
        return []
    by_name = {repository.name: repository for repository in repositories}
    queryset = RepositoryFile.objects.filter(
        index__repository__in=list(by_name), index__status=RepositoryIndexStatus.READY
    )
    if kind:
        queryset = queryset.filter(kind=kind)
    if path:
        queryset = queryset.filter(path__startswith=path.strip("/"))
    weights = term_weights(queryset, terms)
    candidates = queryset.filter(reduce(or_, (Q(content__icontains=term) | Q(path__icontains=term) for term in terms)))
    ranked = list(
        candidates.annotate(score=score_expression(terms, weights))
        .order_by("-score", "path")
        .values("id", "score")[:limit]
    )
    if not ranked:
        return []
    rows = {
        row["id"]: row
        for row in RepositoryFile.objects.filter(id__in=[item["id"] for item in ranked]).values(
            "id",
            "path",
            "kind",
            "title",
            "content",
            repository=F("index__repository"),
            commit_sha=F("index__commit_sha"),
        )
    }
    hits = []
    for item in ranked:
        row = rows[item["id"]]
        repository = by_name[row["repository"]]
        lines = matching_lines(row["content"], terms, row["kind"])
        hits.append(
            SearchHit(
                repository=repository.name,
                path=row["path"],
                kind=row["kind"],
                title=row["title"],
                score=round(float(item["score"]), 2),
                url=repository.file_url(
                    row["commit_sha"],
                    row["path"],
                    lines[0].number if lines else None,
                    lines[-1].number if lines else None,
                ),
                documentation_url=repository.documentation_url(row["path"]),
                lines=lines,
            )
        )
    return hits


__all__ = ["SearchHit", "SearchLine", "query_terms", "search_files"]
