"""Records → transcript-shaped text for cognify, with a header carrying the canonical IDs."""


def render(rec: dict) -> str | None:
    m, ref = rec["meta"], rec["ref"]
    if rec["type"] == "adr":
        head = f"[DECISION {ref} {m.get('date', '')} status={m.get('status', '')}] {m.get('title', '')}"
    elif rec["type"] == "meeting":
        head = f"[MEETING {ref} {m.get('date', '')}] {m.get('title', '')}\nattendees: {', '.join(m.get('attendees') or [])}"
    elif rec["type"] == "ticket":
        head = (
            f"[TICKET {ref} {m.get('created', '')} status={m.get('status', '')}] {m.get('title', '')}\n"
            f"assignee: {m.get('assignee')}; service: {m.get('service')}; refs: {', '.join(m.get('refs') or [])}"
        )
    elif rec["type"] == "org":
        people = {p["id"]: p for p in m.get("people", [])}
        lines = [
            f"Team {t['id']} ({t.get('name', '')}) is led by {t.get('lead')} and owns {', '.join(t.get('owns', []))}. "
            f"Members: {', '.join(p['id'] for p in people.values() if p.get('team') == t['id'])}."
            for t in m.get("teams", [])
        ]
        lines += [f"{p['id']} is {p.get('name', '')}, also called {', '.join(p.get('aliases', []))}." for p in people.values()]
        head = "[ORG CHART]\n" + "\n".join(lines)
    else:
        return None
    return f"{head}\n\n{rec['body']}".strip()
