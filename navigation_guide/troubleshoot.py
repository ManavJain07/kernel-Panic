"""'I'm stuck' troubleshooter. Pure Python (no bpy). Owner: navigation team.

problems.json lists common beginner problems. Each has ordered causes; a cause
with a `when` condition is checked against the live Blender state, so the
causes that apply to the user RIGHT NOW are shown first.
"""
import json
import os

try:
    from . import finder, navigator
except ImportError:
    import finder
    import navigator

_PATH = os.path.join(os.path.dirname(__file__), "problems", "problems.json")
_cache = None
_EXTRA_STOP = {"doesn", "don", "isn", "won", "didn", "wont", "dont"}


def load_problems(force=False):
    global _cache
    if _cache is None or force:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _cache = json.load(f)["problems"]
        except (OSError, ValueError, KeyError):
            _cache = []
    return _cache


def get_problem(problem_id):
    for p in load_problems():
        if p["id"] == problem_id:
            return p
    return None


def search(query, limit=2):
    tokens = [t for t in finder._words(query) if len(t) >= 2 or t.isdigit()]
    useful = [t for t in tokens if t not in finder._STOPWORDS and t not in _EXTRA_STOP] or tokens
    scored = []
    for index, p in enumerate(load_problems()):
        title_words = finder._words(p["title"])
        keywords = [w for k in p.get("keywords", []) for w in finder._words(k)]
        summary_words = finder._words(p.get("summary", ""))
        score = 0
        for t in useful:
            if any(finder._match(t, w) for w in title_words):
                score += 3
            if any(finder._match(t, w) for w in keywords):
                score += 2
            if any(finder._match(t, w) for w in summary_words):
                score += 1
        if score > 0:
            scored.append((-score, index, p))
    scored.sort(key=lambda s: (s[0], s[1]))
    if not scored:
        return []
    best = -scored[0][0]
    close = [p for neg, _, p in scored if -neg >= max(2, 0.6 * best)]  # drop weak, noisy matches
    return close[:limit]


def cause_matches(cause, state):
    when = cause.get("when")
    return bool(when) and navigator.check_condition(when, state, {})


def causes_for(problem, state):
    """[(cause, likely)] with the causes that match the live state first."""
    likely = [(c, True) for c in problem["causes"] if cause_matches(c, state)]
    others = [(c, False) for c in problem["causes"] if not cause_matches(c, state)]
    return likely + others


def quick_check(state):
    """Things that look wrong right now, from causes flagged "quick"."""
    found, seen = [], set()
    for p in load_problems():
        for c in p["causes"]:
            if c.get("quick") and c["text"] not in seen and cause_matches(c, state):
                seen.add(c["text"])
                found.append(c)
    return found
