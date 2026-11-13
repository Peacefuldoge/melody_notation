"""Launch real Tk GUI and verify help, search, clipboard, shortcut, single-instance behavior."""
import sys
from pathlib import Path
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from melody_notation.gui import Editor
from melody_notation.help_dialog import EXAMPLE_SCORE

root = tk.Tk()
e = Editor(root)
root.update()
original_score = e.score_model.to_dict()
e.show_help()
root.update()
h = e._help_dialog
assert h is not None and h.window.winfo_exists()
assert h.chapter_list.size() >= 7
footer = h.feedback.get()
assert footer.startswith('教程仅供阅读')
footer_frame = h.window.winfo_children()[0].winfo_children()[2]
assert footer_frame.winfo_height() > 20, 'Help footer must stay visible'
assert '第一次使用' in h.text.get('1.0','end')
h.search_text.set('6/5')
root.update()
assert h.chapter_list.size() >= 1
h.copy_example()
assert root.clipboard_get() == EXAMPLE_SCORE
assert e.score_model.to_dict() == original_score
assert h.feedback.get().startswith('示例已复制')
e.show_help()
assert e._help_dialog is h  # No duplicate dialog
h.window.destroy()
root.update()
e.show_help()
assert e._help_dialog is not h
root.destroy()
print('HELP GUI smoke OK: chapters, search, clipboard, reuse, reopen, score safety')
