"""Chat-session persistence and context building.

Follows the db/similarity.py precedent: module functions over the pool.
Hard rule: the chat layer adds zero methods to database.py.
"""
from __future__ import annotations

import hashlib
from typing import Any

from psycopg.types.json import Jsonb


def next_turn_index(pool, session_id: str) -> int:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT COALESCE(MAX(turn_index), -1) + 1 AS next FROM advisor_sessions WHERE session_id = %s",
            (session_id,))
        return cur.fetchone()["next"]


def session_owner_ok(pool, session_id: str, user_email: str, is_admin: bool = False) -> bool:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT user_email FROM advisor_sessions WHERE session_id = %s LIMIT 1",
            (session_id,))
        row = cur.fetchone()
    if row is None:
        return False
    return is_admin or row["user_email"] == user_email


def log_chat_turn(
    pool, *, session_id: str, turn_index: int, user_email: str | None,
    query_text: str | None, results: list[dict] | None,
    overall_assessment: str | None, intent: str | None,
    envelope: dict | None, scope: dict | None, opted_out: bool = False,
) -> int:
    # Privacy handling mirrors Database.log_advisor_session (database.py:1796)
    if opted_out:
        query_text = None
        results = None
        overall_assessment = None
        envelope = None
        scope = None
        if user_email:
            user_email = hashlib.sha256(user_email.encode()).hexdigest()[:16]
    with pool.connection() as conn:
        cur = conn.execute(
            """INSERT INTO advisor_sessions
               (session_id, turn_index, user_email, query_text, results_json,
                overall_assessment, intent, envelope_json, scope_json, opted_out)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (session_id, turn_index, user_email, query_text,
             Jsonb(results) if results is not None else None,
             overall_assessment, intent,
             Jsonb(envelope) if envelope is not None else None,
             Jsonb(scope) if scope is not None else None,
             opted_out))
        row_id = cur.fetchone()["id"]
        conn.commit()
    return row_id


def get_session_context(pool, session_id: str, user_email: str | None = None,
                        max_turns: int = 5) -> list[dict[str, Any]]:
    """The router's view: last <=max_turns turns, fixed shape, no prose."""
    sql = ("SELECT turn_index, intent, query_text, results_json "
           "FROM advisor_sessions WHERE session_id = %s")
    params: list = [session_id]
    if user_email is not None:
        sql += " AND user_email = %s"
        params.append(user_email)
    sql += " ORDER BY turn_index DESC LIMIT %s"
    params.append(max_turns)
    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    context = []
    for row in reversed(rows):
        results = [{"id": r["content_id"], "name": r.get("display_name") or r["content_id"]}
                   for r in (row["results_json"] or []) if r.get("content_id")]
        context.append({"n": row["turn_index"], "intent": row["intent"] or "recommend",
                        "query": row["query_text"] or "", "results": results})
    return context


def get_performance_scores(pool, content_ids: list[str]) -> dict[str, int]:
    if not content_ids:
        return {}
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT content_id, performance_score FROM performance_scores WHERE content_id = ANY(%s)",
            (content_ids,)).fetchall()
    return {r["content_id"]: r["performance_score"] for r in rows}


def get_item_workloads(pool, content_id: str) -> list[str]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT workload_role FROM babylon_item_workloads WHERE content_id = %s ORDER BY workload_role",
            (content_id,)).fetchall()
    return [r["workload_role"] for r in rows]
