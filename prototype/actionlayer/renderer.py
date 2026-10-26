"""Layer-2 renderer stub (dvr/1.0 contract pending freeze confirmation).

Implements the narrow interface the action layer will consume from the real
view renderer once its spec is confirmed frozen (INTERFACES.md):

    render_confirmation(record) -> bool   # approval prompt UI
    render_audit_view(record) -> str      # audit view (HTML)

The stub renders plain text and always returns True for confirmations; the
*decision* to execute still comes from the engine's explicit confirmation
parameter — the stub is a display path, not an authority path. CALLS is a
test-visible log so tests can assert the interface is actually invoked.
"""
CALLS = []

def render_confirmation(record):
    CALLS.append(("render_confirmation", record["action_id"]))
    n = record["intent"]["normalized"]
    print(f"[confirm:{record['reversibility_class']}] {n['action_type']} "
          f"{n.get('params', {})} — asked: \"{record['intent']['verbatim']}\"")
    return True

def render_audit_view(record):
    CALLS.append(("render_audit_view", record["action_id"]))
    n = record["intent"]["normalized"]
    return (f"<div class='audit-view' data-action='{record['action_id']}'>"
            f"{n['action_type']} — {record['outcome']['status']}</div>")
