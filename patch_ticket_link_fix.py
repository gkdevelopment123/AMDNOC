f = "app.py"
s = open(f).read()

# Add CSS that forces all text inside the ticket-card link to keep its own color
# and removes underlines — only the explicit "open board" stays accent-colored.
add_css = '''.cc-ticklink-wrap,.cc-ticklink-wrap *{{text-decoration:none !important}}
.cc-ticklink-wrap .cc-h{{color:#64748B !important}}
.cc-ticklink-wrap .cc-tid{{color:#059669 !important}}
.cc-ticklink-wrap .cc-prio{{color:#DC2626 !important}}
.cc-ticklink-wrap .cc-tstat{{color:#2563EB !important}}
.cc-ticklink-wrap .cc-turl{{color:#94A3B8 !important}}
.cc-ticklink-wrap .cc-ticklink{{color:#6366F1 !important}}'''

# inject right after the existing cc-ticklink rule we added earlier
anchor = ".cc-ticklink{{margin-left:auto;font-family:'JetBrains Mono';font-size:.62rem;color:#6366F1;font-weight:700}}"
if anchor in s and ".cc-ticklink-wrap .cc-tid" not in s:
    s = s.replace(anchor, anchor + "\n" + add_css, 1)
    open(f, "w").write(s)
    print("Ticket card link styling fixed - text colors restored, no underlines.")
else:
    print("Anchor not found or already fixed - will adjust if needed.")
