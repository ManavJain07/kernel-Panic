"""'Find a tool' search for the navigation side of the add-on.

Pure Python (no bpy) so it can be tested outside Blender.
Owner: navigation team.
"""
import json
import os
import re

_PATH = os.path.join(os.path.dirname(__file__), "tools", "tools.json")
_cache = None

_STOPWORDS = {
    "a", "an", "the", "to", "how", "do", "i", "my", "of", "in", "it", "can",
    "want", "make", "create", "use", "where", "is", "find", "for", "with", "me",
}


def load_tools(force=False):
    global _cache
    if _cache is None or force:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _cache = json.load(f)["tools"]
        except (OSError, ValueError, KeyError):
            _cache = []
    return _cache


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _match(token, word):
    if token == word:
        return True
    if len(token) >= 4 and word.startswith(token):
        return True
    if len(word) >= 4 and token.startswith(word):  # colours -> colour
        return True
    return False


def search(query, limit=3):
    """Return the best matching tools for a plain-language query."""
    tokens = _words(query)
    useful = [t for t in tokens if t not in _STOPWORDS] or tokens
    if not useful:
        return []

    scored = []
    for index, tool in enumerate(load_tools()):
        name_words = _words(tool["name"])
        keywords = [w for k in tool.get("keywords", []) for w in _words(k)]
        what_words = _words(tool.get("what", ""))
        score = 0
        for token in useful:
            if any(_match(token, w) for w in name_words):
                score += 3
            if any(_match(token, w) for w in keywords):
                score += 2
            if any(_match(token, w) for w in what_words):
                score += 1
        if score > 0:
            scored.append((-score, index, tool))

    scored.sort(key=lambda s: (s[0], s[1]))
    return [tool for _, _, tool in scored[:limit]]


def mode_advice(tool, state):
    """Explain if the tool will not work in the current mode.

    Returns (message, action). Both are None when everything is fine.
    `action` is a name from operators.ACTIONS that can fix the problem.
    """
    need = tool.get("mode", "ANY")
    cur = state["mode_id"]
    if need == "ANY" or need == cur:
        return None, None

    if need == "EDIT_MESH":
        if state["active_type"] != "MESH":
            return "Works in Edit Mode. Select a mesh object first, then press Tab.", None
        if cur == "OBJECT":
            return f"Works in Edit Mode. You are in {state['mode']}. Press Tab.", "toggle_edit_mode"
        return f"Works in Edit Mode. You are in {state['mode']}. Go back to Object Mode (Tab), then press Tab again.", None

    if need == "OBJECT":
        if cur == "EDIT_MESH":
            return f"Works in Object Mode. You are in {state['mode']}. Press Tab.", "toggle_edit_mode"
        return f"Works in Object Mode. You are in {state['mode']}. Switch back using the mode menu at the top-left.", None

    return None, None
