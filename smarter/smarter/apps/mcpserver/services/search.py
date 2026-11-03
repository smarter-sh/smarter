"""
Search of the indexed files of The Smarter Project's repositories, and of its blog.

:func:`search_documentation`, :func:`search_code` and :func:`search_blog` search the documentation,
the source code and the blog's posts. The MCPServer's public tools of the same names call them
(see :mod:`smarter.apps.mcpserver.protocol.tools.search`). They search only the indexes that are
ready, and queue the others for indexing. All three call :func:`search_files`, which ranks the
files that :mod:`smarter.apps.mcpserver.services.indexing.github` and
:mod:`smarter.apps.mcpserver.services.indexing.blog` stored, for a query, in the database, without embeddings:

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

Nothing is cached here: the public tools cache their results. The only writes are those of
queuing an index that is not ready.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import math
import re
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
from smarter.apps.mcpserver.services.indexing.indexes import (
    not_indexed_error,
    ready_indexes,
    require_blog_index,
)
from smarter.apps.mcpserver.services.repositories import (
    ProjectRepository,
    ProjectSource,
    project_blog,
)

MAX_TERMS = 8
"""The most terms of a query that are searched for.

Later terms are ignored, which keeps the SQL small.
"""

MIN_TERM_LENGTH = 2
"""The shortest term that is searched for.

A single character would match nearly every file.
"""

MAX_COUNTED_OCCURRENCES = 10
"""The most occurrences of a term in a file that count towards its score, so that long files do not win by length alone."""

PRESENCE_WEIGHT = 4.0
"""The bonus, times the term's weight, of a file whose content contains a term at all."""

PATH_WEIGHT = 6.0
"""The bonus, times the term's weight, of a file whose path contains a term, e.g. ``custom_domain``."""

TITLE_WEIGHT = 4.0
"""The bonus, times the term's weight, of a document whose title contains a term."""

MAX_LINES_PER_HIT = 6
"""The most lines of code that a hit shows, and the lines that a hit with no matching line shows."""

MAX_LINE_LENGTH = 240
"""The most characters of a line that a hit shows.

A longer line is clipped, and ends with an ellipsis.
"""

CONTEXT_LINES_BEFORE = 2
"""The lines before a document's best line that its passage shows."""

CONTEXT_LINES_AFTER = 6
"""The lines after a document's best line that its passage shows."""

MAX_SNIPPET_CHARACTERS = 900
"""The most characters of a document's passage, about a paragraph, so that a search's result stays short."""

TERM_PATTERN = re.compile(r'"([^"]+)"|([A-Za-z0-9_][A-Za-z0-9_./:-]*[A-Za-z0-9_]|[A-Za-z0-9_])')
"""
A term of a query: a quoted phrase, in group 1, or else a word, in group 2.

A word may contain ``.``, ``/``, ``:`` and ``-`` inside it, so that an identifier such as
``smarter_settings.environment_platform_domain``, a path or a url is one term.
"""

STOPWORDS = frozenset("""
    a an and are as at be by can do does for from has have how i in is it its me my of on or our
    the this that to was what when where which who why will with you your about into there their
    then than so if not no yes use used using show tell find get explain
    """.split())
"""Common English words, which an LLM puts in its queries, and which match every file. A quoted phrase keeps them."""


class SearchLine(BaseModel):
    """A line of a file, with its line number, which a :class:`SearchHit` shows."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int = Field(description="The line number, from 1.")
    text: str = Field(description="The line, clipped at MAX_LINE_LENGTH characters.")


class SearchHit(BaseModel):
    """
    A file that matches a search, as :func:`search_files` returns it.

    The search tools format it as Markdown: a heading, its links, and its lines in a code block.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str = Field(description="The name of the repository, or the blog, that the file is of.")
    path: str = Field(description="The file's path in the repository, or the post's path.")
    kind: RepositoryFileKind = Field(description="Whether the file is documentation or code.")
    title: str = Field(default="", description="The document's title, or an empty string.")
    score: float = Field(description="The file's score, rounded to 2 decimals: higher is better.")
    url: str = Field(description="The file's GitHub url, at the indexed commit, highlighting its matching lines.")
    documentation_url: Optional[str] = Field(
        default=None, description="The published documentation page of the file, if it is one."
    )
    lines: list[SearchLine] = Field(default_factory=list, description="The matching lines, and their context.")


def query_terms(query: str) -> list[str]:
    """
    Split a search query into lowercase terms.

    A word shorter than :data:`MIN_TERM_LENGTH`, or one of :data:`STOPWORDS`, is dropped, unless it
    is quoted. Only the first :data:`MAX_TERMS` terms are kept.

    :param query: The query, e.g. ``how does "custom domain" verification work``.
    :returns: The terms, without duplicates or common words, e.g. ``["custom domain", "verification", "work"]``.
    """
    terms: list[str] = []
    if not query:
        return terms
    for phrase, word in TERM_PATTERN.findall(query):
        if phrase:
            term = phrase.strip().lower()
        else:
            term = word.strip().lower()
        if len(term) < MIN_TERM_LENGTH:
            continue
        if not phrase and term in STOPWORDS:
            continue
        if term in terms:
            continue
        terms.append(term)
        if len(terms) >= MAX_TERMS:
            break
    return terms


def occurrences(term: str) -> ExpressionWrapper:
    """
    Return the SQL expression of the number of times a lowercase term occurs in a file's content.

    Removing every occurrence of the term shortens the content by the term's length, for each one,
    so the number is the difference of the two lengths, divided by the term's length. Every database
    that Django supports can evaluate it, unlike a full text search.

    :param term: The lowercase term.
    :returns: A float expression, for ``annotate()``.
    """
    lower_content = Lower("content")
    without_term = Replace(lower_content, Value(term), Value(""))
    removed = Length(lower_content) - Length(without_term)
    removed_as_float = Cast(removed, FloatField())
    term_length = Value(float(len(term)))
    count = ExpressionWrapper(removed_as_float / term_length, output_field=FloatField())
    return count


def term_weights(queryset: QuerySet, terms: list[str]) -> dict[str, float]:
    """
    Return each term's inverse document frequency among the files of a queryset, in one query.

    A term's weight is ``1 + log((1 + files) / (1 + files with the term))``, so that a term that is
    in few files, such as an identifier, counts for more than one that is in most.

    Side effects: one database query, which counts the files that contain each term.

    :param queryset: The files searched.
    :param terms: The terms.
    :returns: Each term's weight, from 1 for a term in every file.
    """
    term_counts = {}
    for i, term in enumerate(terms):
        has_term = Q(content__icontains=term) | Q(path__icontains=term)
        term_counts[f"t{i}"] = Count("id", filter=has_term)
    counts = queryset.aggregate(total=Count("id"), **term_counts)

    total = counts["total"] or 0
    weights = {}
    for i, term in enumerate(terms):
        files_with_term = counts[f"t{i}"] or 0
        rarity = (1 + total) / (1 + files_with_term)
        weights[term] = 1.0 + math.log(rarity)
    return weights


def term_score(term: str, weight: float):
    """
    Return the SQL expression of a file's score for one term.

    :param term: The lowercase term.
    :param weight: The term's weight, from :func:`term_weights`.
    :returns: The sum of the term's presence bonus, its capped occurrences, and its path and title
        bonuses, each times the weight.
    """
    presence = Case(When(content__icontains=term, then=Value(PRESENCE_WEIGHT * weight)), default=Value(0.0))
    capped_occurrences = Least(occurrences(term), Value(float(MAX_COUNTED_OCCURRENCES)))
    frequency = capped_occurrences * Value(weight)
    in_path = Case(When(path__icontains=term, then=Value(PATH_WEIGHT * weight)), default=Value(0.0))
    in_title = Case(When(title__icontains=term, then=Value(TITLE_WEIGHT * weight)), default=Value(0.0))
    score = presence + frequency + in_path + in_title
    return score


def score_expression(terms: list[str], weights: dict[str, float]) -> ExpressionWrapper:
    """
    Return the SQL expression of a file's score for the terms: the sum of its score for each term.

    :param terms: The lowercase terms. There must be at least one.
    :param weights: Each term's weight, from :func:`term_weights`.
    :returns: A float expression, for ``annotate()``.
    """
    first_term = terms[0]
    total = term_score(first_term, weights[first_term])
    for term in terms[1:]:
        score = term_score(term, weights[term])
        total = total + score
    expression = ExpressionWrapper(total, output_field=FloatField())
    return expression


def clip(text: str) -> str:
    """
    Return a line, without trailing whitespace, shortened to at most :data:`MAX_LINE_LENGTH` characters.

    :param text: The line.
    :returns: The line, or its start and an ellipsis if it is too long.
    """
    text = text.rstrip()
    if len(text) <= MAX_LINE_LENGTH:
        return text
    clipped = text[: MAX_LINE_LENGTH - 1] + "…"
    return clipped


def search_line(lines: list[str], i: int) -> SearchLine:
    """
    Return one line of a file as a :class:`SearchLine`, clipped, with its number.

    :param lines: The file's lines.
    :param i: The line's index, from 0.
    :returns: The line, numbered from 1.
    """
    return SearchLine(number=i + 1, text=clip(lines[i]))


def documentation_passage(lines: list[str], best: int) -> list[SearchLine]:
    """
    Return the passage of a document around its best line.

    The passage is :data:`CONTEXT_LINES_BEFORE` lines before the best line to
    :data:`CONTEXT_LINES_AFTER` lines after it, and ends early at :data:`MAX_SNIPPET_CHARACTERS`.

    :param lines: The document's lines.
    :param best: The index of the line that contains the most terms.
    :returns: The lines, in order, at least one.
    """
    start = max(0, best - CONTEXT_LINES_BEFORE)
    end = min(len(lines), best + CONTEXT_LINES_AFTER + 1)
    passage: list[SearchLine] = []
    characters = 0
    for i in range(start, end):
        characters += len(lines[i])
        if characters > MAX_SNIPPET_CHARACTERS and passage:
            break
        passage.append(search_line(lines, i))
    return passage


def matching_lines(content: str, terms: list[str], kind: str) -> list[SearchLine]:
    """
    Return the lines of a file that best show why it matches.

    For code, these are the :data:`MAX_LINES_PER_HIT` lines that contain the most terms, the earlier
    line first among equals. For documentation, they are a passage around the line that contains the
    most terms, so that the LLM reads a sentence in its context. A file whose content contains no
    term, e.g. one that matched by its path, shows its first lines.

    :param content: The file's content.
    :param terms: The lowercase terms.
    :param kind: The file's kind.
    :returns: The lines, in order.
    """
    lines = content.splitlines()

    # (number of terms on the line, line index), for each line with at least one term.
    scored = []
    for i, line in enumerate(lines):
        lower = line.lower()
        matched = 0
        for term in terms:
            if term in lower:
                matched += 1
        if matched:
            scored.append((matched, i))

    if not scored:
        first_lines = []
        for i in range(min(len(lines), MAX_LINES_PER_HIT)):
            first_lines.append(search_line(lines, i))
        return first_lines

    if kind == RepositoryFileKind.DOCUMENTATION:
        # The line with the most terms, the earliest among equals.
        best_item = max(scored, key=lambda item: (item[0], -item[1]))
        best = best_item[1]
        return documentation_passage(lines, best)

    # The lines with the most terms, the earliest among equals, then put back in file order.
    by_terms = sorted(scored, key=lambda item: (-item[0], item[1]))
    best_items = by_terms[:MAX_LINES_PER_HIT]
    best_indexes = sorted(item[1] for item in best_items)
    best_lines = [search_line(lines, i) for i in best_indexes]
    return best_lines


def search_files(
    repositories: Sequence[ProjectSource],
    query: str,
    kind: Optional[str] = None,
    path: Optional[str] = None,
    limit: int = 10,
) -> list[SearchHit]:
    """
    Search the indexed files of one or more repositories.

    Only indexes that are ready are searched. The files are ranked in the database, and only the
    best ``limit`` files are then read, to extract their matching lines.

    Side effects: three database queries: the terms' weights, the ranking, and the best files' rows.

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
    if not terms:
        return []
    if not repositories:
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

    # A candidate contains at least one term, in its content or its path.
    any_term = Q()
    for term in terms:
        any_term |= Q(content__icontains=term) | Q(path__icontains=term)
    candidates = queryset.filter(any_term)
    scored = candidates.annotate(score=score_expression(terms, weights))
    ordered = scored.order_by("-score", "path")
    ranked = list(ordered.values("id", "score")[:limit])
    if not ranked:
        return []

    ranked_ids = [item["id"] for item in ranked]
    row_values = RepositoryFile.objects.filter(id__in=ranked_ids).values(
        "id",
        "path",
        "kind",
        "title",
        "content",
        repository=F("index__repository"),
        commit_sha=F("index__commit_sha"),
    )
    rows = {row["id"]: row for row in row_values}

    hits = []
    for item in ranked:
        row = rows[item["id"]]
        repository = by_name[row["repository"]]
        lines = matching_lines(row["content"], terms, row["kind"])
        first_line = None
        last_line = None
        if lines:
            first_line = lines[0].number
            last_line = lines[-1].number
        url = repository.file_url(row["commit_sha"], row["path"], first_line, last_line)
        hit = SearchHit(
            repository=repository.name,
            path=row["path"],
            kind=row["kind"],
            title=row["title"],
            score=round(float(item["score"]), 2),
            url=url,
            documentation_url=repository.documentation_url(row["path"]),
            lines=lines,
        )
        hits.append(hit)
    return hits


class SearchResults(BaseModel):
    """
    The result of a search of the repositories: the hits, and the repositories that were not searched.

    A repository that is not indexed yet is queued for indexing, and named in :attr:`not_indexed`,
    so that the caller can say that it was left out, and when to try again.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hits: list[SearchHit] = Field(default_factory=list, description="The hits, best first.")
    not_indexed: list[str] = Field(
        default_factory=list,
        description="The names of the repositories that were not searched, because they are not indexed yet.",
    )


def search_repositories(
    repositories: Sequence[ProjectRepository],
    query: str,
    kind: str,
    path: Optional[str],
    limit: int,
) -> SearchResults:
    """
    Search the files of one kind in the repositories that are indexed, and name those that are not.

    **Side effects:** database queries, and Celery tasks queued for the repositories that are not
    indexed yet (see :func:`~smarter.apps.mcpserver.services.indexing.indexes.ready_indexes`).

    :param repositories: The repositories to search.
    :param query: The query.
    :param kind: Documentation, or code: a :class:`~smarter.apps.mcpserver.models.RepositoryFileKind`.
    :param path: Only files under this folder, or None to search them all.
    :param limit: The maximum number of hits.
    :returns: The hits, best first, and the repositories that were not searched.
    :raises SmarterMCPServerServiceError: If none of the repositories is indexed yet.
    """
    ready = ready_indexes(repositories)
    if not ready:
        names = [repository.name for repository in repositories]
        raise not_indexed_error(", ".join(names))
    searchable = []
    not_indexed = []
    for repository in repositories:
        if repository.name in ready:
            searchable.append(repository)
        else:
            not_indexed.append(repository.name)
    hits = search_files(searchable, query, kind=kind, path=path, limit=limit)
    results = SearchResults(hits=hits, not_indexed=not_indexed)
    return results


def search_documentation(repositories: Sequence[ProjectRepository], query: str, limit: int) -> SearchResults:
    """
    Search the documentation of the repositories: the Sphinx documentation, READMEs and other prose.

    **Side effects:** see :func:`search_repositories`.

    :param repositories: The repositories to search.
    :param query: The query, e.g. ``custom domain verification``.
    :param limit: The maximum number of hits.
    :returns: The passages, best first, and the repositories that were not searched.
    :raises SmarterMCPServerServiceError: If none of the repositories is indexed yet.

    **Example usage**::

        results = search_documentation([get_repository("smarter")], "custom domain verification", limit=8)
        results.hits[0].documentation_url
    """
    results = search_repositories(repositories, query, RepositoryFileKind.DOCUMENTATION, path=None, limit=limit)
    return results


def search_code(
    repositories: Sequence[ProjectRepository], query: str, limit: int, path: Optional[str] = None
) -> SearchResults:
    """
    Search the source code and configuration of the repositories.

    **Side effects:** see :func:`search_repositories`.

    :param repositories: The repositories to search.
    :param query: The query, e.g. ``verify_custom_domain``.
    :param limit: The maximum number of hits.
    :param path: Only files under this folder, e.g. ``smarter/smarter/apps/llmclient``, or None.
    :returns: The files, best first, with their matching lines, and the repositories that were not searched.
    :raises SmarterMCPServerServiceError: If none of the repositories is indexed yet.
    """
    results = search_repositories(repositories, query, RepositoryFileKind.CODE, path=path, limit=limit)
    return results


def search_blog(query: str, limit: int) -> list[SearchHit]:
    """
    Search the posts of The Smarter Project's blog.

    **Side effects:** database queries, and, if the blog is not indexed yet, a Celery task queued to
    index it.

    :param query: The query, e.g. ``caching``.
    :param limit: The maximum number of hits.
    :returns: The passages of the posts, best first.
    :raises SmarterMCPServerServiceError: If the blog is not indexed yet.
    """
    blog = project_blog()
    require_blog_index(blog)
    hits = search_files([blog], query, kind=RepositoryFileKind.DOCUMENTATION, limit=limit)
    return hits


__all__ = [
    "SearchHit",
    "SearchLine",
    "SearchResults",
    "query_terms",
    "search_blog",
    "search_code",
    "search_documentation",
    "search_files",
    "search_repositories",
]
