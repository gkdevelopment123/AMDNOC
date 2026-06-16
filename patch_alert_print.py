f = "pipeline.py"
s = open(f).read()
old = '''        elif stage == "ticket":
            print(f"[ticket]      -> {payload['ticket'].get('ticket_id')} created")'''
new = '''        elif stage == "ticket":
            print(f"[ticket]      -> {payload['ticket'].get('ticket_id')} created")
        elif stage == "alerts":
            print(f"[alert]       -> {len(payload['alerts'].get('notify', []))} notification(s) dispatched")'''
if old in s and "[alert]" not in s:
    s = s.replace(old, new, 1)
    open(f, "w").write(s)
    print("Terminal print for alerts added.")
else:
    print("Could not add print (anchor not found or already present) - but the agent still runs.")
