f = "app.py"
s = open(f).read()

add_css = '''
.cc-ticklink-wrap,.cc-ticklink-wrap *{{text-decoration:none !important}}
.cc-ticklink-wrap .cc-h{{color:#64748B !important}}
.cc-ticklink-wrap .cc-tid{{color:#059669 !important}}
.cc-ticklink-wrap .cc-prio{{color:#DC2626 !important;background:#FEE2E2 !important}}
.cc-ticklink-wrap .cc-tstat{{color:#2563EB !important;background:#DBEAFE !important}}
.cc-ticklink-wrap .cc-turl{{color:#94A3B8 !important}}
.cc-ticklink-wrap .cc-ticklink{{color:#6366F1 !important}}'''

anchor = ".cc-turl{{font-family:'JetBrains Mono';font-size:.7rem;color:#94A3B8}}"
if anchor in s and ".cc-ticklink-wrap .cc-tid" not in s:
    s = s.replace(anchor, anchor + add_css, 1)
    open(f, "w").write(s)
    print("Fixed: ticket card text colors restored, underlines removed.")
elif ".cc-ticklink-wrap .cc-tid" in s:
    print("Already fixed.")
else:
    print("Anchor still not found - paste me lines 275-295 of app.py")
