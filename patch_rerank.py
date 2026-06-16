f = "pipeline.py"
s = open(f).read()
OLD = '''def stage_retrieve_runbooks(incident):
    """Try the RAG module; fall back to inline runbook text."""
    try:
        from rag.knowledge_base import retrieve_runbooks
        ctx = retrieve_runbooks(incident.get("correlation_reason", "BGP failure"))
        if ctx:
            return ctx'''
NEW = '''def _rerank_runbooks(incident, candidates):
    if len(candidates) <= 1:
        return candidates
    rerank_prompt = (
        "You are a retrieval reranker for a telecom NOC. Given an incident and candidate "
        "runbook passages, score how well EACH helps diagnose/resolve THIS incident. Return "
        "ONLY JSON: {\\"ranking\\":[{\\"index\\":<int>,\\"score\\":<0-1>}]} ordered best-first. "
        "index is the candidate 0-based position."
    )
    payload = {
        "incident": {"root_cause_hint": incident.get("correlation_reason",""),
                     "severity": incident.get("severity",""),
                     "affected_devices": incident.get("affected_devices",[])[:5]},
        "candidates": [{"index": i, "text": c[:600]} for i, c in enumerate(candidates)],
    }
    try:
        out = ask_json(rerank_prompt, payload, thinking=False)
        order = [r["index"] for r in out.get("ranking", []) if isinstance(r.get("index"), int)]
        seen, ordered = set(), []
        for i in order:
            if 0 <= i < len(candidates) and i not in seen:
                ordered.append(candidates[i]); seen.add(i)
        for i in range(len(candidates)):
            if i not in seen:
                ordered.append(candidates[i])
        return ordered
    except Exception:
        return candidates


def stage_retrieve_runbooks(incident):
    """Retrieve a wide candidate set, LLM-rerank it, lead with the best match."""
    try:
        from rag.knowledge_base import retrieve_runbooks
        raw = retrieve_runbooks(incident.get("correlation_reason", "BGP failure"), k=5)
        if raw:
            candidates = [c.strip() for c in raw.split("---") if c.strip()]
            ranked = _rerank_runbooks(incident, candidates)
            ctx = "\\n\\n---\\n\\n".join(ranked[:3])
            if ctx:
                return ctx'''
if OLD in s:
    s = s.replace(OLD, NEW)
    open(f, "w").write(s)
    print("Reranking added: top-5 retrieve -> LLM rerank -> top-3.")
else:
    print("WARNING: original block not found - may already be patched.")
