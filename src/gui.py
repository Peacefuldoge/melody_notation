"""Desktop GUI: click-to-select jianpu notes, change attributes, draw slur spans.

Tkinter + Pillow (no web dependency). The source tab is an explicit edit/apply view.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from importlib import resources
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from . import __version__
from .core import Score, ORNAMENTS, parse_text, text_from_score
from .editing import DURATIONS, add_slur, clear_slur, update_note, insert_note, delete_note, get_note
from .midi import INSTRUMENTS, export_midi
from .audio import export_audio, synthesize, SAMPLE_RATE
from .playback import PlaybackError, create_player, clock_label
from .png import render_score, export_png
from .vision import transcribe_image
from .help_dialog import HelpDialog
from .ui_theme import apply_theme
from .workspace import ProjectWorkspace, ScoreTab, WorkspaceError, validate_name, load_recent_projects
from .workspace_gui import WorkspaceMixin

INITIAL = """title: 山风（示例）
key: C
time: 4/4
bpm: 120
notes:
| ( 1 2 3 5 ) | 6/2 5/2 3 2 1 | 3' 2' 1' 7 | 1' - - - |
"""
BEAT_LABELS = {
    '1/8拍（32分）': .125,
    '1/4拍（16分）': .25,
    '3/8拍（附点16分）': .375,
    '1/2拍（8分）': .5,
    '3/4拍（附点8分）': .75,
    '7/8拍': .875,
    '1拍（4分）': 1,
    '1.5拍（附点4分）': 1.5,
    '1.75拍': 1.75,
    '2拍（2分）': 2,
    '3拍（附点2分）': 3,
    '4拍（全音符）': 4,
}
REV_BEATS = {v:k for k,v in BEAT_LABELS.items()}
ACC_LABELS = {'自然':0,'升号 #':1,'降号 ♭':-1}
REV_ACC = {v:k for k,v in ACC_LABELS.items()}
ORNAMENT_LABELS = {
    '无': '', '颤音 Trill': 'tr', '上波音 Mordent': 'mordent',
    '下波音': 'lower_mordent', '回音 Turn': 'turn',
    '断奏 Staccato': 'staccato', '重音 Accent': 'accent',
    '保持音 Tenuto': 'tenuto', '同音震音 Tremolo': 'tremolo',
}
REV_ORNAMENTS = {v:k for k,v in ORNAMENT_LABELS.items()}
SPEED_LABELS = {'1.00×':1.0, '1.25×':1.25, '1.50×':1.5, '1.75×':1.75, '2.00×':2.0}


def score_preview_layout(image_size: tuple[int, int], viewport_size: tuple[int, int],
                         gutter: int = 12) -> tuple[float, tuple[int, int], tuple[int, int], tuple[int, int, int, int]]:
    """Layout the score page in a scrollable Tk Canvas without stretching it.

    The page stays centered when the viewport grows beyond the page's maximum
    display width. A narrow viewport fits the page proportionally (and keeps a
    260px minimum preview, matching the previous GUI's small-window behavior).
    Returns scale, image origin, rendered size and scroll region. Coordinates
    from the PNG hit-test map are transformed using the same scale and origin.
    """
    image_w, image_h = image_size
    viewport_w, viewport_h = viewport_size
    if image_w <= 0 or image_h <= 0:
        raise ValueError('Preview image dimensions must be positive')
    target_w = max(260, viewport_w - 2 * gutter)
    scale = min(1.0, target_w / image_w)
    shown = (max(1, round(image_w * scale)), max(1, round(image_h * scale)))
    origin = (max(gutter, (viewport_w - shown[0]) // 2), gutter)
    region = (0, 0,
              max(viewport_w, origin[0] + shown[0] + gutter),
              max(viewport_h, origin[1] + shown[1] + gutter))
    return scale, origin, shown, region


class Editor(WorkspaceMixin):
    def __init__(self, root: tk.Tk):
        self.root=root
        root.title(f'Melody Notation v{__version__} — 项目工作台')
        root.geometry('1520x850')
        root.minsize(1050,690)
        self.project: ProjectWorkspace | None = None
        self.documents: list[ScoreTab] = []
        self.active_document: ScoreTab | None = None
        self._tree_paths: dict[str, Path] = {}
        self._recent_projects = load_recent_projects()
        self._nav_collapsed = False
        self._modified = False
        self.path:Path|None=None
        self.is_sample=False
        self.score_model=parse_text(INITIAL)
        self.selected:tuple[int,int]|None=None
        self.slur_anchor:tuple[int,int]|None=None
        self.undo_stack:list[Score]=[]
        self.redo_stack:list[Score]=[]
        self.photo=None
        self.hits=[]
        self.scale=1.0
        self.offset=(12,12)
        self._source_internal=False
        self.source_dirty=False
        self._redraw_job=None
        self._help_dialog: HelpDialog | None = None
        self.theme_mode='light'
        self.palette=apply_theme(root, self.theme_mode)
        self.source_visible=False
        self.hover_job=None
        self.file_label=tk.StringVar(value='未保存的乐谱')
        self.status_right=tk.StringVar(value='就绪')
        self._status_after=None
        self._player=None
        self._preview_signature=None
        self._preview_token=0
        self._preview_future=None
        self._preview_executor=None
        self._progress_dragging=False
        self._last_player_state='stopped'
        self._pending_play_fraction=0.0
        self._build()
        self.refresh_project_tree()
        self._open_untitled_tab(parse_text(INITIAL), label='山风 · 新建', is_sample=True)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.after(140, self._playback_tick)
        self._set_source_text()
        self.root.after(200,self.redraw)

    def _menu(self, host: tk.Widget) -> tk.Menu:
        p=self.palette
        menu=tk.Menu(host, tearoff=False, bg=p['raised'], fg=p['text'],
                     activebackground=p['accent_faint'], activeforeground=p['text'],
                     bd=0, relief='flat', font=('Microsoft YaHei UI',10))
        return menu

    def _popup_menu(self, button, menu):
        menu.tk_popup(button.winfo_rootx(), button.winfo_rooty()+button.winfo_height())
        menu.grab_release()

    def _divider(self, parent, side='left', padx=6):
        ttk.Frame(parent, style='Hairline.TFrame', width=1).pack(side=side, fill='y', padx=padx, pady=9)

    def _build(self):
        p=self.palette
        shell=ttk.Frame(self.root,style='Root.TFrame')
        shell.pack(fill='both',expand=True)

        # One quiet context strip; file/editor actions live in the project navigator,
        # and the entire transport lives in a dedicated card beside the score.
        context=ttk.Frame(shell,style='Soft.TFrame',padding=(18,10))
        context.pack(fill='x')
        ttk.Label(context,textvariable=self.file_label,style='ContextTitle.TLabel').pack(side='left')
        self.score_meta=tk.StringVar(value='1=C   ·   4/4   ·   ♩ 120')
        ttk.Label(context,textvariable=self.score_meta,style='Meta.TLabel').pack(side='right')
        # The sidebar menus are built on demand with the current light/dark palette.
        self.menus=()

        # Project tree / centered editor / note Inspector, like a code workstation.
        body=ttk.Frame(shell,style='Root.TFrame',padding=(12,12,12,10))
        body.pack(fill='both',expand=True)
        body.grid_rowconfigure(0,weight=1);body.grid_columnconfigure(1,weight=1)
        self._build_project_navigator(body,p)
        # Separate preview/playback card above the note Inspector.
        right_stack=tk.Frame(body,bg=p['window'],bd=0,highlightthickness=0,width=286)
        right_stack.grid(row=0,column=2,sticky='ns',padx=(9,0))
        right_stack.grid_propagate(False)
        self.right_stack=right_stack

        play_border=tk.Frame(right_stack,bg=p['line'],bd=0,highlightthickness=0)
        play_border.pack(fill='x',pady=(0,9))
        self.playback_border=play_border
        player=ttk.Frame(play_border,style='Surface.TFrame',padding=(13,11,13,11))
        player.pack(fill='x',padx=1,pady=1)
        ttk.Label(player,text='试听控制',style='PanelTitle.TLabel').pack(anchor='w',pady=(0,10))
        transport_buttons=ttk.Frame(player,style='Surface.TFrame')
        transport_buttons.pack(fill='x')
        self.play_button=ttk.Button(transport_buttons,text='▶  播放',command=self.listen,style='Primary.TButton')
        self.play_button.pack(side='left',fill='x',expand=True,padx=(0,5))
        self.stop_button=ttk.Button(transport_buttons,text='■  停止',command=self.stop_listen,style='Soft.TButton')
        self.stop_button.pack(side='left',fill='x',expand=True,padx=(5,0))

        settings=ttk.Frame(player,style='Surface.TFrame')
        settings.pack(fill='x',pady=(11,0))
        settings.columnconfigure(0,weight=1)
        settings.columnconfigure(1,weight=0)
        ttk.Label(settings,text='音色',style='Quiet.TLabel').grid(row=0,column=0,sticky='w',pady=(0,4))
        ttk.Label(settings,text='倍速',style='Quiet.TLabel').grid(row=0,column=1,sticky='w',pady=(0,4))
        self.instrument=tk.StringVar(value='piano')
        self.instrument_box=ttk.Combobox(settings,textvariable=self.instrument,values=list(INSTRUMENTS),
                                        state='readonly',width=15,style='Modern.TCombobox')
        self.instrument_box.grid(row=1,column=0,sticky='ew',padx=(0,8))
        self.instrument_box.bind('<<ComboboxSelected>>',lambda e:self._invalidate_preview())
        self.speed_label=tk.StringVar(value='1.00×')
        self.speed_box=ttk.Combobox(settings,textvariable=self.speed_label,values=list(SPEED_LABELS),
                                     state='readonly',width=6,style='Modern.TCombobox')
        self.speed_box.grid(row=1,column=1,sticky='e')
        self.speed_box.bind('<<ComboboxSelected>>',self._on_speed_changed)
        self.playback_progress=tk.DoubleVar(value=0.0)
        self.playback_scale=ttk.Scale(player,from_=0,to=1,variable=self.playback_progress,
                                      orient='horizontal',style='Transport.Horizontal.TScale')
        self.playback_scale.pack(fill='x',pady=(13,2))
        self.playback_scale.bind('<ButtonPress-1>',self._begin_seek)
        self.playback_scale.bind('<ButtonRelease-1>',self._finish_seek)
        self.time_label=tk.StringVar(value='0:00 / 0:00')
        ttk.Label(player,textvariable=self.time_label,style='Quiet.TLabel',anchor='e').pack(fill='x')

        # Scroll only the Inspector contents. The playback card never disappears
        # when the user needs the bottom slur actions on a small window.
        left_container=tk.Frame(right_stack,bg=p['line'],bd=0,highlightthickness=0)
        left_container.pack(fill='both',expand=True)
        self.left_border=left_container
        inspector_canvas=tk.Canvas(left_container,bg=p['surface'],bd=0,highlightthickness=0)
        inspector_canvas.pack(side='left',fill='both',expand=True,padx=(1,0),pady=1)
        self.inspector_canvas=inspector_canvas
        inspector_scroll=ttk.Scrollbar(left_container,orient='vertical',
                command=inspector_canvas.yview,style='Modern.Vertical.TScrollbar')
        inspector_scroll.pack(side='right',fill='y',pady=1,padx=(0,1))
        inspector_canvas.configure(yscrollcommand=inspector_scroll.set)
        left=ttk.Frame(inspector_canvas,style='Surface.TFrame',padding=(12,13,12,18))
        inspector_window=inspector_canvas.create_window((0,0),window=left,anchor='nw')
        left.bind('<Configure>',lambda e: inspector_canvas.configure(scrollregion=inspector_canvas.bbox('all')))
        inspector_canvas.bind('<Configure>',lambda e: inspector_canvas.itemconfigure(inspector_window,width=e.width))
        self.sidebar=left
        left.columnconfigure(0,weight=1)
        ttk.Label(left,text='音符属性',style='PanelTitle.TLabel').pack(anchor='w')
        ttk.Label(left,text='选择乐谱中的音符进行编辑',style='Quiet.TLabel').pack(anchor='w',pady=(3,10))
        self.selected_label=tk.StringVar(value='未选中音符')
        ttk.Label(left,textvariable=self.selected_label,style='Selected.TLabel').pack(fill='x',pady=(0,12))
        self.degree=tk.StringVar(value='1');self.octave=tk.StringVar(value='0')
        self.duration=tk.StringVar(value=REV_BEATS[1]);self.accidental=tk.StringVar(value='自然')
        self.ornament=tk.StringVar(value='无')
        self.prop_controls=[]
        for label,var,values in [('音级 / 休止',self.degree,[str(i) for i in range(8)]),
                                 ('高低八度',self.octave,[str(i) for i in range(-3,4)]),
                                 ('音符时值',self.duration,list(BEAT_LABELS)),
                                 ('临时升降号',self.accidental,list(ACC_LABELS)),
                                 ('演奏记号',self.ornament,list(ORNAMENT_LABELS))]:
            row=ttk.Frame(left,style='Surface.TFrame'); row.pack(fill='x',pady=(0,9))
            ttk.Label(row,text=label,style='Surface.TLabel',width=11).pack(side='left')
            c=ttk.Combobox(row,textvariable=var,values=values,state='readonly',width=19,style='Modern.TCombobox')
            c.pack(side='right',fill='x',expand=True)
            c.bind('<<ComboboxSelected>>',self._auto_apply_property)
            self.prop_controls.append(c)
        ttk.Button(left,text='应用音符修改',command=self.apply_properties,style='Soft.TButton').pack(fill='x',pady=(3,8))
        actions_row=ttk.Frame(left,style='Surface.TFrame');actions_row.pack(fill='x')
        ttk.Button(actions_row,text='后插入',command=self.add_note,style='Soft.TButton').pack(side='left',expand=True,fill='x',padx=(0,4))
        ttk.Button(actions_row,text='删除',command=self.remove_note,style='Soft.TButton').pack(side='left',expand=True,fill='x',padx=(4,0))
        ttk.Frame(left,style='Hairline.TFrame',height=1).pack(fill='x',pady=(18,14))
        ttk.Label(left,text='连音线',style='Subheading.TLabel').pack(anchor='w')
        self.slur_label=tk.StringVar(value='先选择起点，再选终点建立连音线')
        ttk.Label(left,textvariable=self.slur_label,style='Quiet.TLabel',wraplength=250).pack(fill='x',pady=(6,9))
        slur_buttons=ttk.Frame(left,style='Surface.TFrame');slur_buttons.pack(fill='x')
        ttk.Button(slur_buttons,text='设起点',command=self.mark_slur_start,style='Soft.TButton').pack(side='left',expand=True,fill='x',padx=(0,3))
        ttk.Button(slur_buttons,text='连接',command=self.connect_slur,style='Soft.TButton').pack(side='left',expand=True,fill='x',padx=3)
        ttk.Button(slur_buttons,text='移除',command=self.remove_slur,style='Soft.TButton').pack(side='left',expand=True,fill='x',padx=(3,0))
        score_outer=tk.Frame(body,bg=p['line'],bd=0)
        score_outer.grid(row=0,column=1,sticky='nsew')
        self.score_border=score_outer
        score_frame=ttk.Frame(score_outer,style='Surface.TFrame')
        score_frame.pack(fill='both',expand=True,padx=1,pady=1)
        self._build_document_tabs(score_frame)
        board_head=ttk.Frame(score_frame,style='Surface.TFrame',padding=(16,11))
        board_head.pack(fill='x')
        ttk.Label(board_head,text='乐谱',style='PanelTitle.TLabel').pack(side='left')
        self.source_toggle=ttk.Button(board_head,text='▸  源码',style='Small.TButton',command=self.toggle_source)
        self.source_toggle.pack(side='right',padx=(10,0))
        self.bars=tk.StringVar(value='3')
        self.bar_box=ttk.Combobox(board_head,textvariable=self.bars,values=['2','3','4','5'],
                                 state='readonly',width=3,style='Modern.TCombobox')
        self.bar_box.pack(side='right')
        self.bar_box.bind('<<ComboboxSelected>>',lambda e:self.redraw())
        ttk.Label(board_head,text='每行小节',style='Surface.TLabel').pack(side='right',padx=(0,5))
        ttk.Frame(score_frame,style='Hairline.TFrame',height=1).pack(fill='x')
        wrapper=ttk.Frame(score_frame,style='Surface.TFrame',padding=(12,12,8,9))
        wrapper.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(wrapper,bg=p['canvas'],highlightthickness=0,cursor='hand2')
        yscroll=ttk.Scrollbar(wrapper,orient='vertical',command=self.canvas.yview,style='Modern.Vertical.TScrollbar')
        xscroll=ttk.Scrollbar(wrapper,orient='horizontal',command=self.canvas.xview,style='Modern.Horizontal.TScrollbar')
        self.canvas.configure(yscrollcommand=yscroll.set,xscrollcommand=xscroll.set)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        yscroll.grid(row=0,column=1,sticky='ns')
        xscroll.grid(row=1,column=0,sticky='ew')
        wrapper.rowconfigure(0,weight=1);wrapper.columnconfigure(0,weight=1)
        self.canvas.bind('<Button-1>',self._on_canvas_click)
        self.canvas.bind('<Configure>',self._schedule_redraw)
        self.canvas.bind('<MouseWheel>',self._on_wheel)
        self.canvas.bind('<Button-4>',lambda e:self.canvas.yview_scroll(-2,'units'))
        self.canvas.bind('<Button-5>',lambda e:self.canvas.yview_scroll(2,'units'))

        # Bottom source drawer: its controls must remain visible even at 970×640.
        self.source_panel=ttk.Frame(score_frame,style='Surface.TFrame',padding=(16,0,16,10))
        ttk.Frame(self.source_panel,style='Hairline.TFrame',height=1).pack(fill='x',pady=(0,9))
        source_top=ttk.Frame(self.source_panel,style='Surface.TFrame')
        source_top.pack(fill='x',pady=(0,7))
        ttk.Label(source_top,text='简谱源码',style='Subheading.TLabel').pack(side='left')
        ttk.Button(source_top,text='从源码更新谱面  Ctrl+Enter',command=self.apply_source,style='Soft.TButton').pack(side='right')
        self.edit=tk.Text(self.source_panel,wrap='word',font=('Consolas',10),undo=True,height=6,
                          bg=p['raised'],fg=p['text'],insertbackground=p['text'],bd=0,
                          highlightthickness=1,highlightbackground=p['line'],padx=10,pady=9,
                          selectbackground=p['accent_faint'],selectforeground=p['text'])
        self.edit.pack(fill='x',expand=False)
        self.edit.bind('<KeyRelease>',self._on_source_edit)
        self.edit.bind('<Control-Return>',lambda e:self.apply_source())

        footer=ttk.Frame(shell,style='Surface.TFrame',padding=(18,10))
        footer.pack(fill='x')
        self.status=tk.StringVar(value='选择音符后可直接编辑 · 调整时值后请检查节拍')
        ttk.Label(footer,textvariable=self.status,style='Status.TLabel').pack(side='left',fill='x',expand=True)
        ttk.Label(footer,textvariable=self.status_right,style='StatusRight.TLabel').pack(side='right')
        self.root.bind('<F1>',self.show_help)
        self.root.bind('<Control-z>',lambda e:self.undo() if self.root.focus_get()!=self.edit else None)
        self.root.bind('<Control-y>',lambda e:self.redo() if self.root.focus_get()!=self.edit else None)
        self.root.bind('<Control-s>',lambda e:self._shortcut(self.save))
        self.root.bind('<Control-o>',lambda e:self._shortcut(self.open))
        self.root.bind('<Control-n>',lambda e:self._shortcut(self.new_score))
        self.root.bind('<Control-Shift-s>',lambda e:self._shortcut(self.save_as))
        self.root.bind('<Control-space>', self._play_shortcut)
        self.root.bind('<Control-Tab>',lambda e:self._shortcut(self.next_tab))
        self.root.bind('<Control-w>',lambda e:self._shortcut(self.close_current_tab))
        self.root.bind('<Control-Shift-f>',lambda e:self._shortcut(self.focus_project_search))

    def _play_shortcut(self, event=None):
        if self.root.focus_get() != self.edit:
            self.listen()
            return 'break'
        return None

    def _shortcut(self, fn):
        fn()
        return 'break'

    @staticmethod
    def available_samples() -> list[str]:
        """All bundled examples, included in both source-tree and wheel builds."""
        folder = resources.files(__package__).joinpath('samples')
        return sorted(p.name for p in folder.iterdir() if p.name.endswith('.jianpu'))

    @staticmethod
    def sample_display_name(filename: str) -> str:
        names = {'huang.jianpu': '荒（A 调 → 降 B 调）',
                 'shanfeng.jianpu': '山风（基础示例）',
                 'visual_demo.jianpu': '山风（连音示例）',
                 'chiptune_ornaments.jianpu': '像素冒险（8-bit / 装饰音）',
                 'yueguang.jianpu': '月光（图片简化样例）'}
        return names.get(filename, filename)

    def load_sample(self, filename: str):
        return self.open_sample_tab(filename)

    def new_score(self):
        return self.new_score_tab()

    def save_as(self):
        if self.source_dirty and not self.apply_source():return False
        target=filedialog.asksaveasfilename(defaultextension='.jianpu',
            filetypes=[('简谱','*.jianpu')],initialdir=str(self.project.root) if self.project else None)
        return self.save_current_to(target) if target else False

    def toggle_source(self):
        if self.source_visible:
            self.source_panel.pack_forget()
            self.source_toggle.configure(text='▸  源码')
            self.source_visible=False
        else:
            self.source_panel.pack(fill='x',expand=False)
            self.source_toggle.configure(text='▾  收起源码')
            self.source_visible=True
        self.root.after_idle(self._schedule_redraw)

    def toggle_theme(self):
        # Rebuild only GUI controls. Never reconstruct or mutate score data.
        # Keep source draft, note selection, file path and undo history intact.
        self.theme_mode='dark' if self.theme_mode=='light' else 'light'
        self.palette=apply_theme(self.root,self.theme_mode)
        self._theme_project_navigator(self.palette)
        self.canvas.configure(bg=self.palette['canvas'])
        self.edit.configure(bg=self.palette['raised'],fg=self.palette['text'],
                            insertbackground=self.palette['text'],
                            highlightbackground=self.palette['line'],
                            selectbackground=self.palette['accent_faint'],
                            selectforeground=self.palette['text'])
        # Custom one-pixel panel borders stay consistent with the chosen palette.
        self.right_stack.configure(bg=self.palette['window'])
        self.inspector_canvas.configure(bg=self.palette['surface'])
        for frame in (self.playback_border,self.left_border,self.score_border):
            frame.configure(bg=self.palette['line'])
        for menu in self.menus:
            menu.configure(bg=self.palette['raised'],fg=self.palette['text'],
                           activebackground=self.palette['accent_faint'],
                           activeforeground=self.palette['text'])
        self.redraw()
        for editor in getattr(self,'_asset_editors',{}).values():
            if editor.window.winfo_exists():
                editor.set_theme(self.theme_mode)

    def show_help(self, event=None):
        """Open or focus the in-app tutorial without affecting editor state."""
        if self._help_dialog is None or not self._help_dialog.window.winfo_exists():
            self._help_dialog = HelpDialog(self.root)
        else:
            self._help_dialog.show()
        return 'break' if event is not None else None

    def _schedule_redraw(self,e=None):
        if self._redraw_job is not None:self.root.after_cancel(self._redraw_job)
        self._redraw_job=self.root.after(140,self.redraw)

    def _on_wheel(self,e):
        self.canvas.yview_scroll(-1 if e.delta>0 else 1,'units')

    def _on_source_edit(self,e=None):
        if not self._source_internal:
            self._invalidate_preview()
            self.source_dirty=True
            self._render_tabs()
            self.status_right.set('源码未应用')
            self.status.set('源码有未应用的更改：点击「从源码更新谱面」后，才能继续可视化编辑。')

    def _set_source_text(self):
        self._source_internal=True
        self.edit.delete('1.0','end');self.edit.insert('1.0',text_from_score(self.score_model))
        self.edit.edit_modified(False)
        self.source_dirty=False
        self._source_internal=False
        if hasattr(self,'status_right'): self.status_right.set('源码已同步')

    def _ready(self):
        if self.source_dirty:
            messagebox.showwarning('有未应用的源码更改','请先展开乐谱下方的「源码」，点击「从源码更新谱面」，再进行可视化编辑。')
            return False
        return True

    def _commit(self,new:Score,selection=None):
        if not self._ready():return False
        self._invalidate_preview()
        self.undo_stack.append(deepcopy(self.score_model))
        self.redo_stack.clear()
        self.score_model=new
        self._modified=True
        if selection is not None:self.selected=selection
        self._set_source_text()
        self._show_selection()
        self.redraw()
        self._render_tabs()
        return True

    def _show_selection(self):
        if self.selected:
            try:
                bar,idx=self.selected
                note=get_note(self.score_model,bar,idx)
                self.selected_label.set(f'第 {bar} 小节 · 第 {idx} 个音符')
                self.degree.set(str(note.degree));self.octave.set(str(note.octave))
                self.duration.set(REV_BEATS.get(note.beats,f'{note.beats:g}拍'))
                self.accidental.set(REV_ACC.get(note.accidental,'自然'))
                self.ornament.set(REV_ORNAMENTS.get(note.ornament,'无'))
                return
            except IndexError: self.selected=None
        self.selected_label.set('未选中音符')

    def _auto_apply_property(self,e=None):
        if self.selected and not self.source_dirty:
            self.apply_properties()

    def apply_properties(self):
        if not self.selected:
            self.status.set('请先在右侧谱面点击一个音符。')
            return
        if not self._ready():return
        try:
            d=int(self.degree.get());o=int(self.octave.get())
            a=ACC_LABELS[self.accidental.get()];b=BEAT_LABELS[self.duration.get()]
            ornament=ORNAMENT_LABELS[self.ornament.get()]
            if d==0: o=0;a=0;ornament=''
            new=update_note(self.score_model,*self.selected,degree=d,octave=o,beats=b,
                            accidental=a,ornament=ornament)
            if new.to_dict()==self.score_model.to_dict(): return
            self._commit(new)
        except Exception as exc:messagebox.showerror('音符修改失败',str(exc))

    def add_note(self):
        if not self._ready():return
        try:
            if self.selected:
                b,i=self.selected
            else:
                b=max(1,len(self.score_model.measures))
                i=len(self.score_model.measures[b-1]) if self.score_model.measures else 0
            self._commit(insert_note(self.score_model,b,i+1,degree=1,beats=1),(b,i+1))
        except Exception as exc:messagebox.showerror('插入失败',str(exc))

    def remove_note(self):
        if not self.selected or not self._ready():return
        try:
            b,i=self.selected
            self._commit(delete_note(self.score_model,b,i),(b,max(1,i-1)))
        except Exception as exc:messagebox.showerror('删除失败',str(exc))

    def mark_slur_start(self):
        if not self.selected or not self._ready():return
        self.slur_anchor=self.selected
        self.slur_label.set(f'已选起点：第 {self.selected[0]} 小节，第 {self.selected[1]} 音')
        self.status.set('请在谱面点选连音终点，然后点击「连接到当前音符」。')

    def connect_slur(self):
        if not self.selected or not self.slur_anchor or not self._ready():return
        try:
            s=add_slur(self.score_model,*self.slur_anchor,*self.selected)
            self._commit(s)
            self.slur_anchor=None
            self.slur_label.set('连音线已创建；可继续选择其他音符。')
        except Exception as exc:messagebox.showerror('连音失败',str(exc))

    def remove_slur(self):
        if not self.selected or not self._ready():return
        try:self._commit(clear_slur(self.score_model,*self.selected))
        except Exception as exc:messagebox.showerror('删除连音失败',str(exc))

    def _on_canvas_click(self,e):
        if not self.hits:return
        x=(self.canvas.canvasx(e.x)-self.offset[0])/self.scale
        y=(self.canvas.canvasy(e.y)-self.offset[1])/self.scale
        for bar,ni,(x0,y0,x1,y1) in self.hits:
            if x0<=x<=x1 and y0<=y<=y1:
                self.selected=(bar,ni)
                self._show_selection();self.redraw()
                self._pulse_selection((x0,y0,x1,y1))
                return

    def _pulse_selection(self, bounds):
        """Short, non-looping selection feedback; never animates the score layout."""
        x0,y0,x1,y1=bounds
        x0=x0*self.scale+self.offset[0];x1=x1*self.scale+self.offset[0]
        y0=y0*self.scale+self.offset[1];y1=y1*self.scale+self.offset[1]
        item=self.canvas.create_rectangle(x0-3,y0-3,x1+3,y1+3,width=2,
                                          outline=('#8BCBFF' if self.theme_mode=='dark' else '#326EB4'),tags='selection-pulse')
        def step(i):
            if not self.canvas.winfo_exists():return
            colors=('#8BCBFF','#A4CAE7','#C4D5E5') if self.theme_mode=='dark' else ('#326EB4','#72A0D1','#B8CEE6')
            if i>=len(colors):
                self.canvas.delete(item)
            else:
                self.canvas.itemconfigure(item,outline=colors[i])
                self.root.after(65,lambda:step(i+1))
        step(0)

    def redraw(self):
        self._redraw_job=None
        try:
            img,hits=render_score(self.score_model,bars_per_row=int(self.bars.get()),selected=self.selected,width=1200,theme=self.theme_mode)
            self.hits=hits
            self.scale, self.offset, display_size, scrollregion = score_preview_layout(
                img.size, (self.canvas.winfo_width(), self.canvas.winfo_height()))
            if img.size != display_size:
                img = img.resize(display_size, Image.Resampling.LANCZOS)
            self.photo=ImageTk.PhotoImage(img)
            self.canvas.delete('all')
            self.canvas.create_image(*self.offset,image=self.photo,anchor='nw')
            self.canvas.configure(scrollregion=scrollregion)
            self.score_meta.set(f'1={self.score_model.key.upper()}   ·   {self.score_model.numerator}/{self.score_model.denominator}   ·   ♩ {self.score_model.bpm}')
            self.file_label.set(self.path.name if self.path else (f"{self.score_model.title} · 示例（未保存）" if self.is_sample else self.score_model.title))
            issues=self.score_model.validate()
            if issues:
                self.status.set(f'{self.score_model.title} · {len(issues)} 个待修正问题：{issues[0]}')
                self.status_right.set(f'{len(issues)} 个节拍问题')
            elif not self.source_dirty:
                self.status.set(f'{self.score_model.title} · {len(self.score_model.measures)} 小节 · 选中音符后修改属性（自动更新谱面）')
                self.status_right.set(f'{len(self.score_model.measures)} 小节 · 已校验')
        except Exception as exc:
            self.status.set('无法渲染谱面：'+str(exc))

    def apply_source(self):
        try:
            new=parse_text(self.edit.get('1.0','end'),strict=False)
            if new.to_dict()!=self.score_model.to_dict():
                self._modified=True
                self._invalidate_preview()
                self.undo_stack.append(deepcopy(self.score_model));self.redo_stack.clear()
            self.score_model=new;self.selected=None;self.slur_anchor=None
            self._set_source_text();self._show_selection();self.redraw()
            self._render_tabs()
            return True
        except Exception as exc:
            messagebox.showerror('简谱源码错误',str(exc))
            return False

    def undo(self):
        if not self._ready() or not self.undo_stack:return
        self._invalidate_preview()
        self.redo_stack.append(deepcopy(self.score_model))
        self.score_model=self.undo_stack.pop()
        self._modified=True
        self.selected=None;self.slur_anchor=None;self._set_source_text();self._show_selection();self.redraw()
        self._render_tabs()

    def redo(self):
        if not self._ready() or not self.redo_stack:return
        self._invalidate_preview()
        self.undo_stack.append(deepcopy(self.score_model))
        self.score_model=self.redo_stack.pop()
        self._modified=True
        self.selected=None;self.slur_anchor=None;self._set_source_text();self._show_selection();self.redraw()
        self._render_tabs()

    def open(self):
        return self.open_score_tab()

    def save(self):
        if self.source_dirty and not self.apply_source():return False
        if self.path is None:return self.save_as()
        return self.save_current_to(self.path)

    def validate(self):
        if self.source_dirty and not self.apply_source():return
        issues=self.score_model.validate()
        if issues:messagebox.showwarning('需要修正', '\n'.join(issues[:15]))
        else:messagebox.showinfo('校验通过',f'{len(self.score_model.measures)} 个小节已检查，全部符合 {self.score_model.numerator}/{self.score_model.denominator} 拍。')

    def _on_speed_changed(self, event=None):
        """Keep the relative musical playhead when adjusting speed in-flight."""
        fraction=0.0
        was_playing=False
        if self._player is not None:
            try:
                was_playing = self._player.state == 'playing'
                fraction = self._player.position / max(0.001,self._player.duration)
            except Exception:
                pass
        self._invalidate_preview()
        if was_playing:
            self._pending_play_fraction=max(0.0,min(.999,fraction))
            self.listen()
        else:
            self.status.set(f'试听速度已设为 {self.speed_label.get()} · 点击试听即可生效')

    def _preview_identity(self):
        # Use value comparison, never object identity. Never resume an old tune
        # after the score or selected instrument has changed.
        return (self.score_model.to_dict(), self.instrument.get(), self.speed_label.get())

    def _update_transport(self):
        if self._player is None:
            self.time_label.set('0:00 / 0:00')
            if not self._progress_dragging:self.playback_progress.set(0)
            self.playback_scale.configure(to=1)
            if self._preview_future is None:self.play_button.configure(text='▶  播放')
            return
        state=self._player.state
        duration=self._player.duration
        position=self._player.position
        self.playback_scale.configure(to=max(0.1,duration))
        if not self._progress_dragging:
            self.playback_progress.set(position)
        self.time_label.set(f'{clock_label(position)} / {clock_label(duration)}')
        self.play_button.configure(text='Ⅱ  暂停' if state=='playing' else
                                       ('▶  继续' if state=='paused' else '▶  重播'))
        if state=='stopped' and self._last_player_state=='playing':
            self.status.set('试听结束 · 可点击重播')
        self._last_player_state=state

    def _playback_tick(self):
        # Tk callbacks only on the UI thread, including when playback finishes.
        try:
            self._update_transport()
            self.root.after(140, self._playback_tick)
        except tk.TclError:
            pass

    def _begin_seek(self,event=None):
        self._progress_dragging=True

    def _finish_seek(self,event=None):
        self._progress_dragging=False
        if self._player is None or self._preview_future is not None:
            return
        try:
            self._player.seek(self.playback_progress.get())
            self._update_transport()
        except Exception as exc:
            messagebox.showerror('定位播放失败',str(exc))

    def _invalidate_preview(self):
        self._preview_token+=1
        self._preview_signature=None
        self._preview_future=None
        self._pending_play_fraction=0.0
        if self._player is not None:
            try:self._player.close()
            except Exception:pass
            self._player=None
        if hasattr(self,'playback_progress'):
            self._progress_dragging=False
            self._last_player_state='stopped'
            self.play_button.configure(text='▶  播放',state='normal')
            self.time_label.set('0:00 / 0:00')
            self.playback_progress.set(0)
            self.playback_scale.configure(to=1)

    def listen(self):
        if self.source_dirty and not self.apply_source():return
        try:
            self.score_model.validate(strict=True)
            signature=self._preview_identity()
            if self._player is not None and signature==self._preview_signature:
                state=self._player.state
                if state=='playing':
                    self._player.pause()
                    self.status.set('试听已暂停 · 点击继续播放')
                else:
                    self._player.play()
                    self.status.set(f'正在试听 · {self.instrument.get()} · {self.speed_label.get()}')
                self._update_transport()
                return
            if self._preview_future is not None:
                return
            resume_fraction=self._pending_play_fraction
            self._invalidate_preview()
            self._pending_play_fraction=resume_fraction
            self._preview_token+=1
            token=self._preview_token
            if self._preview_executor is None:
                self._preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='melody-preview')
            score=deepcopy(self.score_model)
            instrument=self.instrument.get()
            self._preview_future=self._preview_executor.submit(
                synthesize,score,instrument,SAMPLE_RATE,SPEED_LABELS[self.speed_label.get()])
            self.play_button.configure(text='合成中…',state='disabled')
            self.status.set('正在生成试听音频…')
            self.root.after(80,lambda:self._finish_synth(token,signature))
        except Exception as exc:
            messagebox.showerror('试听失败',str(exc))

    def _finish_synth(self, token, signature):
        if token!=self._preview_token:
            return  # score changed or user pressed Stop during synthesis
        future=self._preview_future
        if future is None:
            return
        if not future.done():
            self.root.after(80,lambda:self._finish_synth(token,signature))
            return
        self._preview_future=None
        self.play_button.configure(state='normal')
        try:
            samples=future.result()
            self._player=create_player()
            self._player.load(samples,SAMPLE_RATE)
            self._preview_signature=signature
            if self._pending_play_fraction:
                self._player.seek(self._player.duration*self._pending_play_fraction)
                self._pending_play_fraction=0.0
            self._player.play()
            self.status.set(f'正在试听 · {self.instrument.get()} · {self.speed_label.get()}')
            self._update_transport()
        except Exception as exc:
            if self._player is not None:
                try:self._player.close()
                except Exception:pass
                self._player=None
            self._preview_signature=None
            self._update_transport()
            messagebox.showerror('内置试听失败',str(exc))

    def stop_listen(self):
        if self._preview_future is not None:
            self._invalidate_preview()
            self.status.set('已取消试听生成')
            return
        if self._player is None:
            return
        try:
            self._player.stop()
            self._last_player_state='stopped'
            self.status.set('试听已停止 · 可点击重播')
            self._update_transport()
        except Exception as exc:
            messagebox.showerror('停止试听失败',str(exc))

    def on_close(self):
        for editor in getattr(self,'_asset_editors',{}).values():
            if editor.window.winfo_exists() and not editor.close():
                return
        if not self.close_workspace_window():return
        self._invalidate_preview()
        if self._preview_executor is not None:
            self._preview_executor.shutdown(wait=False,cancel_futures=True)
            self._preview_executor=None
        self.root.destroy()

    def export(self,ext):
        if self.source_dirty and not self.apply_source():return
        try:
            self.score_model.validate(strict=True)
            p=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[(ext.upper(),f'*{ext}')])
            if not p:return
            if ext=='.png':export_png(self.score_model,p)
            elif ext=='.mid':export_midi(self.score_model,p,self.instrument.get())
            else:export_audio(self.score_model,p,self.instrument.get())
            self.status.set('已导出 '+p)
            messagebox.showinfo('导出完成',p)
        except Exception as exc:messagebox.showerror('导出失败',str(exc))

    def ocr(self):
        p=filedialog.askopenfilename(filetypes=[('图片','*.png *.jpg *.jpeg *.webp')])
        if not p:return
        if not messagebox.askyesno('视觉识谱 Beta','识谱会将图片发送到你配置的视觉模型 API；确定继续吗？'):return
        try:
            score,uncertainty=transcribe_image(p)
            self._invalidate_preview()
            self.undo_stack.append(deepcopy(self.score_model));self.redo_stack.clear()
            self.score_model=score;self.path=None;self.selected=None;self.slur_anchor=None
            self._set_source_text();self._show_selection();self.redraw()
            messagebox.showwarning('请校对识谱草稿',f'请逐小节与原图核对高低音点、连音线和时值。\n不确定项：{uncertainty or "模型未提供"}')
        except Exception as exc:messagebox.showerror('识谱失败',str(exc))


def main():
    root=tk.Tk();Editor(root);root.mainloop()

if __name__=='__main__': main()
