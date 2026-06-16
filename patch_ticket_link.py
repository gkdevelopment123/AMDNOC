f = "app.py"
s = open(f).read()

old = '''    return (f'<div class="cc-panel cc-tick"><div class="cc-h">ITSM TICKET</div>'
            f'<div class="cc-tid">{esc(t.get("ticket_id",""))}</div>'
            f'<div class="cc-trow"><span class="cc-prio">{esc(t.get("priority",""))}</span>'
            f'<span class="cc-tstat">{esc(t.get("status",""))}</span></div>'
            f'<div class="cc-turl">{esc(t.get("url",""))}</div></div>')'''

new = '''    return (f'<a class="cc-ticklink-wrap" href="{ITSM_BOARD_URL}" target="_blank">'
            f'<div class="cc-panel cc-tick"><div class="cc-h">ITSM TICKET '
            f'<span class="cc-ticklink">open board &#8599;</span></div>'
            f'<div class="cc-tid">{esc(t.get("ticket_id",""))}</div>'
            f'<div class="cc-trow"><span class="cc-prio">{esc(t.get("priority",""))}</span>'
            f'<span class="cc-tstat">{esc(t.get("status",""))}</span></div>'
            f'<div class="cc-turl">{esc(t.get("url",""))}</div></div></a>')'''

if old in s:
    s = s.replace(old, new, 1)
    # add CSS so the wrapping link doesn't look like a blue underlined link
    if "cc-ticklink-wrap" not in s.split('CSS = f"""')[0]:
        s = s.replace(
            '.cc-turl{{font-family:\'JetBrains Mono\';font-size:.7rem;color:#94A3B8}}',
            '.cc-turl{{font-family:\'JetBrains Mono\';font-size:.7rem;color:#94A3B8}}\n'
            '.cc-ticklink-wrap{{text-decoration:none;display:block;cursor:pointer}}\n'
            '.cc-ticklink-wrap .cc-tick{{transition:transform .15s,box-shadow .15s}}\n'
            '.cc-ticklink-wrap:hover .cc-tick{{transform:translateY(-2px);box-shadow:0 14px 36px rgba(16,185,129,.22)}}\n'
            '.cc-ticklink{{margin-left:auto;font-family:\'JetBrains Mono\';font-size:.62rem;color:#6366F1;font-weight:700}}')
    open(f, "w").write(s)
    print("Ticket card is now clickable -> opens ITSM board.")
else:
    print("WARNING: p_ticket block not found - paste me the current p_ticket.")
