f = "itsm_board.py"
s = open(f).read()
s = s.replace("const r=await fetch('/api/tickets');", "const r=await fetch('api/tickets');")
s = s.replace("const r=await fetch('/api/ticket/'+id);", "const r=await fetch('api/ticket/'+id);")
open(f, "w").write(s)
print("Board patched: relative fetch paths (proxy-safe).")
