f = "app.py"
s = open(f).read()

# Remove the approve_btn from its current spot (right after sim button)
old_pos = ('    sim = gr.Button("\\u26a1 Simulate Outage", elem_id="simbtn")\n'
           '    approve_btn = gr.Button("\\U0001F512 Approve & Execute High-Risk Action", elem_id="apprbtn", visible=False)\n'
           '    surface = gr.HTML(board())')
new_pos = ('    sim = gr.Button("\\u26a1 Simulate Outage", elem_id="simbtn")\n'
           '    surface = gr.HTML(board())\n'
           '    approve_btn = gr.Button("\\U0001F512 Approve & Execute High-Risk Action", elem_id="apprbtn", visible=False)')

if old_pos in s:
    s = s.replace(old_pos, new_pos, 1)
    import ast; ast.parse(s)
    open(f, "w").write(s)
    print("Approve button moved BELOW the board (near remediation panel).")
elif new_pos in s:
    print("Already in the new position.")
else:
    print("Layout differs - paste me lines around 'approve_btn = gr.Button'")
