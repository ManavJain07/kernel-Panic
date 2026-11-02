"""Small UI helpers shared by the navigation and tutorial panels."""


def draw_wrapped(layout, text, width=34, icon="NONE"):
    """Draw long text as several short labels so it fits the sidebar."""
    line = ""
    first = True
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            layout.label(text=line, icon=icon if first else "NONE")
            first = False
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        layout.label(text=line, icon=icon if first else "NONE")
