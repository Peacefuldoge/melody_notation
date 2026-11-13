"""Project navigator and independent score editor tabs for the Tkinter app.

The music engine stays untouched. The same canvas/Inspector renders whichever
ScoreTab is active; each tab has its own score, history and unapplied text draft.
"""
from __future__ import annotations
from pathlib import Path
from importlib import resources
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from .core import parse_text
from .workspace import ProjectWorkspace, ScoreTab, validate_name, remember_project


class WorkspaceMixin:
    """Project-style navigation that follows Melody Notation's active theme.

    The *layout* borrows familiar project-navigation conventions; color remains
    part of the workstation's own light/dark theme, never a separate dark skin.
    """

    @staticmethod
    def _nav_colors(palette):
        """One source of truth for navigation colors, derived from UI theme."""
        return {
            'BG': palette['surface'],
            'RAIL': palette['window'],
            'HOVER': palette['hover'],
            'SELECT': palette['accent_faint'],
            'TEXT': palette['text'],
            'MUTED': palette['secondary'],
            'SEARCH': palette['raised'],
        }

    def _set_nav_colors(self, palette):
        colors = self._nav_colors(palette)
        for name, value in colors.items():
            setattr(self, 'NAV_' + name, value)
        return colors

    def _style_nav_tree(self):
        style=ttk.Style(self.root)
        style.configure('Nav.Treeview',background=self.NAV_BG,
                        fieldbackground=self.NAV_BG,foreground=self.NAV_TEXT,
                        borderwidth=0,relief='flat',rowheight=31,
                        font=('Microsoft YaHei UI',9))
        style.map('Nav.Treeview',background=[('selected',self.NAV_SELECT)],
                  foreground=[('selected',self.NAV_TEXT)])
        style.configure('Nav.Vertical.TScrollbar', background=self.NAV_RAIL,
                        troughcolor=self.NAV_BG, arrowcolor=self.NAV_MUTED,
                        bordercolor=self.NAV_BG, relief='flat')

    def _theme_project_navigator(self, palette):
        """Retheme existing Tk widgets without rebuilding tabs or score state."""
        old={k:getattr(self,'NAV_'+k) for k in self._nav_colors(palette)}
        new=self._set_nav_colors(palette)
        colors={value.lower():new[key] for key,value in old.items()}
        for widget in self._nav_descendants(self.project_border):
            if isinstance(widget, (tk.Frame, tk.Label, tk.Button, tk.Entry)):
                updates={}
                for option in ('background','foreground','activebackground',
                               'activeforeground','insertbackground','selectbackground',
                               'selectforeground'):
                    try:value=widget.cget(option)
                    except tk.TclError:continue
                    replacement=colors.get(str(value).lower())
                    if replacement is not None:updates[option]=replacement
                if updates:widget.configure(**updates)
        self._style_nav_tree()
        self.nav_scrollbar.configure(background=self.NAV_RAIL,
                                     troughcolor=self.NAV_BG,
                                     activebackground=self.NAV_HOVER)
        # Rebuild the short recents list, preserving active selection and drafts.
        self._render_recent_docs()

    @staticmethod
    def _nav_descendants(parent):
        yield parent
        for widget in parent.winfo_children():
            yield from WorkspaceMixin._nav_descendants(widget)

    def _nav_button(self, parent, text, command, width=None, background=None,
                    foreground=None, font_size=10, anchor='w'):
        bg = background or self.NAV_BG
        role=('RAIL' if bg==self.NAV_RAIL else
              'SELECT' if bg==self.NAV_SELECT else 'BG')
        button = tk.Button(parent, text=text, command=command, bg=bg,
                           fg=foreground or self.NAV_TEXT,
                           activebackground=self.NAV_HOVER, activeforeground=self.NAV_TEXT,
                           relief='flat', borderwidth=0, highlightthickness=0,
                           cursor='hand2', anchor=anchor,
                           font=('Microsoft YaHei UI', font_size),
                           padx=10, pady=7)
        if width is not None:
            button.configure(width=width)
        button.bind('<Enter>', lambda e, b=button: b.configure(bg=self.NAV_HOVER))
        # Resolve the background from current theme at event time, not creation.
        button.bind('<Leave>', lambda e, b=button, r=role: b.configure(bg=getattr(self,'NAV_'+r)))
        return button

    def _build_project_navigator(self, body, palette):
        self._set_nav_colors(palette)
        border=tk.Frame(body,bg=self.NAV_RAIL,width=290,bd=0,highlightthickness=0)
        border.grid(row=0,column=0,sticky='ns',padx=(0,9))
        border.grid_propagate(False)
        self.project_border=border

        self.nav_rail=tk.Frame(border,bg=self.NAV_RAIL,width=43)
        self.nav_rail.pack(side='left',fill='y')
        self.nav_rail.pack_propagate(False)
        self.nav_rail_toggle_button=self._nav_button(
            self.nav_rail, '≡', self.toggle_project_sidebar,
            anchor='center',font_size=15,background=self.NAV_RAIL)
        self.nav_rail_toggle_button.pack(fill='x',pady=(13,14))
        # Compact-rail shortcuts are revealed ONLY when the full panel is hidden.
        # This avoids displaying duplicate New and menu controls in the expanded UI.
        self.nav_rail_new_button=self._nav_button(
            self.nav_rail, '＋', self.new_score,
            anchor='center',font_size=19,background=self.NAV_RAIL)
        self._nav_button(self.nav_rail, '⌕', self.focus_project_search,
                         anchor='center',font_size=19,background=self.NAV_RAIL).pack(fill='x')
        self.nav_rail_menu_button=self._nav_button(
            self.nav_rail, '···', self._nav_all_actions,
            anchor='center',font_size=16,background=self.NAV_RAIL)
        self._nav_button(self.nav_rail, '?', self.show_help,
                         anchor='center',font_size=14,background=self.NAV_RAIL).pack(
                             side='bottom',fill='x',pady=(0,18))

        panel=tk.Frame(border,bg=self.NAV_BG)
        panel.pack(side='left',fill='both',expand=True)
        self.nav_panel=panel
        header=tk.Frame(panel,bg=self.NAV_BG)
        header.pack(fill='x',padx=(9,8),pady=(15,11))
        tk.Label(header,text='Melody Notation',bg=self.NAV_BG,fg=self.NAV_TEXT,
                 font=('Microsoft YaHei UI',11,'bold')).pack(side='left',padx=(4,0))

        # Single action entry point: File/Edit/Export/Tools live in this strip.
        # The title no longer opens a SECOND nested copy of the same menu.
        menu_strip=tk.Frame(panel,bg=self.NAV_BG)
        menu_strip.pack(fill='x',padx=(8,7),pady=(0,8))
        for column,(label,method,attr) in enumerate([
                ('文件',self._nav_file_actions,'nav_file_button'),
                ('编辑',self._nav_edit_actions,'nav_edit_button'),
                ('导出',self._nav_export_actions,'nav_export_button'),
                ('工具',self._nav_tools_actions,'nav_tools_button')]):
            btn=self._nav_button(menu_strip,label+'⌄',method,font_size=9,anchor='center')
            btn.grid(row=0,column=column,sticky='ew',padx=1)
            menu_strip.grid_columnconfigure(column,weight=1)
            setattr(self,attr,btn)
        quick_actions=tk.Frame(panel,bg=self.NAV_BG)
        quick_actions.pack(fill='x',padx=11,pady=(0,4))
        self._nav_button(quick_actions,'＋  新建简谱',self.new_score,
                         font_size=10).pack(fill='x')
        # Save and Save As are available from File, Ctrl+S and Ctrl+Shift+S.
        # No standalone duplicate button occupies the navigation panel.
        search_shell=tk.Frame(panel,bg=self.NAV_SEARCH,bd=0)
        search_shell.pack(fill='x',padx=12,pady=(3,17))
        tk.Label(search_shell,text='⌕',bg=self.NAV_SEARCH,fg=self.NAV_MUTED,
                 font=('Microsoft YaHei UI',15)).pack(side='left',padx=(8,3))
        self.nav_search=tk.StringVar()
        self.nav_search_entry=tk.Entry(search_shell,textvariable=self.nav_search,
                                       relief='flat',bd=0,highlightthickness=0,
                                       bg=self.NAV_SEARCH,fg=self.NAV_TEXT,
                                       insertbackground=self.NAV_TEXT,
                                       font=('Microsoft YaHei UI',9))
        self.nav_search_entry.pack(side='left',fill='x',expand=True,ipady=8,padx=(0,7))
        self.search_hint=tk.Label(self.nav_search_entry,text='搜索项目或简谱',bg=self.NAV_SEARCH,
                                  fg=self.NAV_MUTED,font=('Microsoft YaHei UI',9),cursor='xterm')
        self.search_hint.place(x=2,y=3)
        self.search_hint.bind('<Button-1>',lambda e:self.focus_project_search())
        self.nav_search_entry.bind('<FocusIn>',lambda e:self.search_hint.place_forget())
        self.nav_search_entry.bind('<FocusOut>',lambda e:self._update_search_hint())
        self.nav_search.trace_add('write',lambda *_:self._search_changed())

        recent_row=tk.Frame(panel,bg=self.NAV_BG)
        recent_row.pack(fill='x',padx=15)
        tk.Label(recent_row,text='最近打开',bg=self.NAV_BG,fg=self.NAV_MUTED,
                 font=('Microsoft YaHei UI',9)).pack(side='left')
        self.recent_docs_frame=tk.Frame(panel,bg=self.NAV_BG)
        self.recent_docs_frame.pack(fill='x',padx=11,pady=(6,15))

        projects_heading=tk.Frame(panel,bg=self.NAV_BG)
        projects_heading.pack(fill='x',padx=(15,8),pady=(0,4))
        tk.Label(projects_heading,text='项目',bg=self.NAV_BG,fg=self.NAV_MUTED,
                 font=('Microsoft YaHei UI',9)).pack(side='left')
        self.projects_more_button=self._nav_button(projects_heading,'···',self._nav_project_menu,
                         font_size=13,anchor='center')
        self.projects_more_button.pack(side='right')
        self._nav_button(projects_heading,'＋',self.new_project,
                         font_size=14,anchor='center').pack(side='right')

        tree_wrap=tk.Frame(panel,bg=self.NAV_BG)
        tree_wrap.pack(fill='both',expand=True,padx=(5,4))
        navstyle=ttk.Style(self.root)
        self._style_nav_tree()
        navstyle.layout('Nav.Treeview', [('Treeview.padding', {'sticky':'nswe', 'children':
                    [('Treeview.treearea', {'sticky':'nswe'})]})])
        self.project_tree=ttk.Treeview(tree_wrap,show='tree',selectmode='browse',style='Nav.Treeview')
        self.project_tree.pack(side='left',fill='both',expand=True)
        scroll=tk.Scrollbar(tree_wrap,orient='vertical',command=self.project_tree.yview,
                            width=9,background=self.NAV_RAIL,
                            activebackground=self.NAV_HOVER,
                            troughcolor=self.NAV_BG,
                            relief='flat',borderwidth=0,highlightthickness=0)
        self.nav_scrollbar=scroll
        self.project_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y')
        self.project_tree.bind('<Double-1>',self._on_tree_open)
        self.project_tree.bind('<Return>',self._on_tree_open)
        self.project_tree.bind('<F2>',lambda e:self.rename_project_item())
        self.project_tree.bind('<Button-3>',self._project_context_menu)
        self.project_tree.bind('<Button-2>',self._project_context_menu)
        self.project_tree.bind('<<TreeviewSelect>>',self._on_tree_selection)

        footer=tk.Frame(panel,bg=self.NAV_BG)
        footer.pack(fill='x',padx=10,pady=(8,12))
        self.project_label=tk.StringVar(value='尚未打开项目')
        tk.Label(footer,textvariable=self.project_label,bg=self.NAV_BG,
                 fg=self.NAV_MUTED,font=('Microsoft YaHei UI',9),
                 anchor='w').pack(fill='x',padx=4,pady=(0,6))
        self._nav_button(footer,'＋  新建文件夹',self.new_subproject,
                         font_size=9,foreground=self.NAV_MUTED).pack(fill='x')
        self._render_recent_docs()

    def _search_changed(self):
        self._update_search_hint()
        self.refresh_project_tree()

    def _update_search_hint(self):
        if not self.nav_search.get() and self.root.focus_get() is not self.nav_search_entry:
            self.search_hint.place(x=2,y=3)
        else:
            self.search_hint.place_forget()

    def toggle_project_sidebar(self):
        self._nav_collapsed=not self._nav_collapsed
        if self._nav_collapsed:
            self.nav_panel.pack_forget()
            self.project_border.configure(width=43)
            self.nav_rail_new_button.pack(fill='x', after=self.nav_rail_toggle_button)
            self.nav_rail_menu_button.pack(fill='x')
        else:
            self.nav_rail_new_button.pack_forget()
            self.nav_rail_menu_button.pack_forget()
            self.nav_panel.pack(side='left',fill='both',expand=True)
            self.project_border.configure(width=290)
        self.root.after_idle(self._schedule_redraw)

    def focus_project_search(self):
        if self._nav_collapsed:self.toggle_project_sidebar()
        self.nav_search_entry.focus_set()
        self.nav_search_entry.select_range(0,'end')

    def _build_file_actions_menu(self):
        menu=self._menu(self.root)
        menu.add_command(label='新建项目…',command=self.new_project)
        menu.add_command(label='打开项目文件夹…',command=self.open_project)
        menu.add_separator()
        menu.add_command(label='新建简谱    Ctrl+N',command=self.new_score)
        menu.add_command(label='新建鼓点文件（.drum）',command=self.new_drum)
        menu.add_command(label='新建多音轨文件（.mtrack）',command=self.new_arrangement)
        menu.add_command(label='打开鼓点 / 音轨文件…',command=self.open_music_asset)
        menu.add_command(label='打开简谱…    Ctrl+O',command=self.open_score_tab)
        sample_menu=self._menu(self.root)
        for filename in self.available_samples():
            sample_menu.add_command(label=self.sample_display_name(filename),
                                    command=lambda f=filename:self.load_sample(f))
        menu.add_cascade(label='内置示例',menu=sample_menu)
        menu.add_separator()
        menu.add_command(label='保存    Ctrl+S',command=self.save)
        menu.add_command(label='另存为…    Ctrl+Shift+S',command=self.save_as)
        return menu

    def _build_edit_actions_menu(self):
        menu=self._menu(self.root)
        menu.add_command(label='撤销    Ctrl+Z',command=self.undo)
        menu.add_command(label='重做    Ctrl+Y',command=self.redo)
        menu.add_separator()
        menu.add_command(label='检查节拍',command=self.validate)
        return menu

    def _build_export_actions_menu(self):
        menu=self._menu(self.root)
        for ext,label in [('.mid','MIDI 音符文件'),('.wav','WAV 音频'),
                          ('.mp3','MP3 音频'),('.png','PNG 乐谱图片')]:
            menu.add_command(label=label,command=lambda e=ext:self.export(e))
        return menu

    def _build_tools_actions_menu(self):
        menu=self._menu(self.root)
        menu.add_command(label='图片识谱（Beta）',command=self.ocr)
        menu.add_command(label='展开 / 收起简谱源码',command=self.toggle_source)
        menu.add_command(label='切换浅色 / 深色主题',command=self.toggle_theme)
        menu.add_separator()
        menu.add_command(label='帮助 / 教程    F1',command=self.show_help)
        return menu

    def _nav_file_actions(self):
        self._popup_menu(self.nav_file_button,self._build_file_actions_menu())

    def _nav_edit_actions(self):
        self._popup_menu(self.nav_edit_button,self._build_edit_actions_menu())

    def _nav_export_actions(self):
        self._popup_menu(self.nav_export_button,self._build_export_actions_menu())

    def _nav_tools_actions(self):
        self._popup_menu(self.nav_tools_button,self._build_tools_actions_menu())

    def _nav_all_actions(self):
        # Compact navigation only. The expanded sidebar uses four direct menus.
        self._popup_menu(self.nav_rail_menu_button,self._build_all_actions_menu())

    def _build_all_actions_menu(self):
        menu=self._menu(self.root)
        menu.add_cascade(label='文件',menu=self._build_file_actions_menu())
        menu.add_cascade(label='编辑',menu=self._build_edit_actions_menu())
        menu.add_cascade(label='导出',menu=self._build_export_actions_menu())
        menu.add_cascade(label='工具',menu=self._build_tools_actions_menu())
        return menu

    def _nav_project_menu(self):
        menu=self._menu(self.root)
        menu.add_command(label='新建项目…',command=self.new_project)
        menu.add_command(label='打开项目文件夹…',command=self.open_project)
        menu.add_command(label='新建子文件夹',command=self.new_subproject)
        menu.add_command(label='重命名选中项目项',command=self.rename_project_item)
        menu.add_command(label='刷新项目列表',command=self.refresh_project_tree)
        self._popup_menu(self.projects_more_button,menu)

    def _render_recent_docs(self):
        if not hasattr(self,'recent_docs_frame'):return
        for child in self.recent_docs_frame.winfo_children():child.destroy()
        items=list(reversed(self.documents[-4:]))
        for d in items:
            if d is self.active_document: bg=self.NAV_SELECT
            else:bg=self.NAV_BG
            label=d.title
            if len(label)>25: label=label[:22]+'…'
            self._nav_button(self.recent_docs_frame,'♫  '+label,
                             lambda doc=d:self.switch_tab(doc),background=bg,
                             font_size=9).pack(fill='x',pady=1)
        if not items:
            tk.Label(self.recent_docs_frame,text='暂无打开的简谱',bg=self.NAV_BG,
                     fg=self.NAV_MUTED,anchor='w',font=('Microsoft YaHei UI',9)).pack(fill='x',padx=10)

    def _build_document_tabs(self,score_frame):
        self.tabs_strip=ttk.Frame(score_frame,style='Soft.TFrame',padding=(8,5))
        self.tabs_strip.pack(fill='x')

    def _remember_active(self):
        d=self.active_document
        if d is None:return
        d.score_model=self.score_model
        d.path=self.path
        d.is_sample=self.is_sample
        d.selected=self.selected
        d.slur_anchor=self.slur_anchor
        d.undo_stack=self.undo_stack
        d.redo_stack=self.redo_stack
        d.modified=self._modified
        d.source_dirty=self.source_dirty
        d.source_text=self.edit.get('1.0','end-1c')
        d.instrument=self.instrument.get()
        d.speed_label=self.speed_label.get()
        try:d.scroll_y=self.canvas.yview()[0]
        except (tk.TclError,IndexError):pass

    def _activate(self,d:ScoreTab):
        self._invalidate_preview()
        self.active_document=d
        self.score_model=d.score_model
        self.path=d.path
        self.is_sample=d.is_sample
        self.selected=d.selected
        self.slur_anchor=d.slur_anchor
        self.undo_stack=d.undo_stack
        self.redo_stack=d.redo_stack
        self._modified=d.modified
        self.instrument.set(d.instrument)
        self.speed_label.set(d.speed_label)
        self._set_source_text()
        if d.source_dirty:
            self._source_internal=True
            self.edit.delete('1.0','end')
            self.edit.insert('1.0',d.source_text)
            self._source_internal=False
            self.source_dirty=True
            self.status_right.set('源码未应用')
        self.slur_label.set((f'已选起点：第 {d.slur_anchor[0]} 小节，第 {d.slur_anchor[1]} 音'
                            if d.slur_anchor else '先选择起点，再选终点建立连音线'))
        self._show_selection()
        self.redraw()
        self._render_tabs()
        self._select_tree_path(d.path)
        self.root.after_idle(lambda doc=d:self._restore_scroll(doc))

    def _restore_scroll(self,d):
        if self.active_document is d and self.canvas.winfo_exists():
            self.canvas.yview_moveto(d.scroll_y)

    def _open_untitled_tab(self,score,label='未命名',is_sample=False):
        self._remember_active()
        d=ScoreTab(score_model=score,is_sample=is_sample,label=label)
        self.documents.append(d)
        self._activate(d)
        return d

    def _open_disk_tab(self,path):
        path=Path(path).resolve()
        for d in self.documents:
            if d.path is not None and d.path.resolve()==path:
                self.switch_tab(d)
                return d
        score=parse_text(path.read_text(encoding='utf-8'),strict=False)
        self._remember_active()
        d=ScoreTab(score_model=score,path=path,label=path.name)
        self.documents.append(d)
        self._activate(d)
        return d

    def switch_tab(self,d):
        if d is self.active_document:return
        self._remember_active()
        self._activate(d)

    def _render_tabs(self):
        if not hasattr(self,'tabs_strip'):return
        for child in self.tabs_strip.winfo_children():child.destroy()
        for d in self.documents:
            active=d is self.active_document
            dirty=(self.source_dirty or self._modified) if active else d.dirty
            name=d.title
            if len(name)>23:name=name[:20]+'…'
            cell=ttk.Frame(self.tabs_strip,style='Soft.TFrame');cell.pack(side='left',padx=(0,3))
            ttk.Button(cell,text=('● ' if dirty else '')+name,
                       style='ActiveTab.TButton' if active else 'InactiveTab.TButton',
                       command=lambda doc=d:self.switch_tab(doc)).pack(side='left')
            ttk.Button(cell,text='×',width=2,style='TabClose.TButton',
                       command=lambda doc=d:self.close_tab(doc)).pack(side='left')
        self._render_recent_docs()

    def _ask_save_document(self,d):
        if d is self.active_document:self._remember_active()
        if not d.dirty:return True
        answer=messagebox.askyesnocancel('未保存的修改',
            f'「{d.title}」有未保存更改。\n是：保存　否：不保存　取消：继续编辑')
        if answer is None:return False
        if answer:
            if self.active_document is not d:self.switch_tab(d)
            return bool(self.save())
        return True

    def close_tab(self,d):
        if d not in self.documents:return
        if not self._ask_save_document(d):return
        self.documents.remove(d)
        if self.active_document is d:
            self.active_document=None
            if self.documents:self._activate(self.documents[-1])
            else:self._open_untitled_tab(parse_text(self._blank_score_text()),'未命名')
        else:self._render_tabs()

    def close_current_tab(self):
        if self.active_document:self.close_tab(self.active_document)

    def next_tab(self):
        if len(self.documents)>1:
            i=self.documents.index(self.active_document)
            self.switch_tab(self.documents[(i+1)%len(self.documents)])

    @staticmethod
    def _blank_score_text(title='新乐谱'):
        from .core import blank_score_text
        return blank_score_text(title)

    def new_project(self):
        parent=filedialog.askdirectory(title='选择新项目的父文件夹')
        if not parent:return
        name=simpledialog.askstring('新建 Melody 项目','请输入项目名称：',parent=self.root)
        if name is None:return
        try:
            self.project=ProjectWorkspace.create(Path(parent),name)
            self._register_project(self.project.root)
            self.refresh_project_tree()
            self.status.set('新建项目：'+str(self.project.root))
        except Exception as exc:messagebox.showerror('创建项目失败',str(exc))

    def open_project(self):
        root=filedialog.askdirectory(title='打开已有的 Melody 项目文件夹')
        if not root:return
        try:
            self.project=ProjectWorkspace(Path(root))
            self._register_project(self.project.root)
            self.refresh_project_tree()
            self.status.set('已打开项目 · 双击文件树中的简谱即可添加编辑标签')
        except Exception as exc:messagebox.showerror('打开项目失败',str(exc))

    def _register_project(self,path):
        path=Path(path).resolve()
        if path in self._recent_projects:
            self._recent_projects.remove(path)
        self._recent_projects.insert(0,path)
        self._recent_projects=self._recent_projects[:12]
        try:
            self._recent_projects=remember_project(path)
        except OSError:
            # An unwritable preferences directory must not prevent opening a project.
            pass

    def _project_for_path(self,path):
        if path is None:return None
        path=Path(path).resolve()
        for root in self._recent_projects:
            if path==root or root in path.parents:
                return root
        return None

    def _on_tree_selection(self,event=None):
        selection=self.project_tree.selection()
        if not selection:return
        path=self._tree_paths.get(selection[0])
        root=self._project_for_path(path)
        if root is not None and (self.project is None or self.project.root!=root):
            try:
                self.project=ProjectWorkspace(root)
                self._register_project(root)
                self.project_label.set('当前项目 · '+self.project.name)
            except Exception:
                pass

    def refresh_project_tree(self):
        tree=self.project_tree
        # Retain expansion and current selection during edits/search/refresh.
        selection=tree.selection()
        selected_path=self._tree_paths.get(selection[0]) if selection else None
        expanded={self._tree_paths[i] for i in self._tree_paths if tree.exists(i) and tree.item(i,'open')}
        tree.delete(*tree.get_children())
        self._tree_paths={}
        search=self.nav_search.get().strip().casefold() if hasattr(self,'nav_search') else ''
        roots=list(self._recent_projects)
        if self.project is not None and self.project.root not in roots:
            roots.insert(0,self.project.root)
        for root in roots:
            if not root.is_dir():continue
            try:project=ProjectWorkspace(root)
            except Exception:continue
            dirs=project.list_dirs()
            scores=project.list_assets()
            project_match=search and search in project.name.casefold()
            shown_scores=[s for s in scores if (not search or project_match or
                           search in str(s.relative_to(root)).casefold())]
            shown_dirs={d for d in dirs if not search or project_match or search in d.name.casefold()}
            if search:
                for file in shown_scores:
                    shown_dirs.update(p for p in file.parents if p!=root and root in p.parents)
                for folder in list(shown_dirs):
                    shown_dirs.update(p for p in folder.parents if p!=root and root in p.parents)
                if not shown_scores and not shown_dirs and not project_match:
                    continue
            mark='●  ' if self.project is not None and self.project.root==root else '▸  '
            root_id=tree.insert('', 'end',text=mark+project.name,
                                open=(not expanded or root in expanded or bool(search) or
                                      (self.project is not None and self.project.root==root)))
            self._tree_paths[root_id]=root
            for folder in dirs:
                if search and folder not in shown_dirs:continue
                parent=self._tree_item_for(folder.parent) or root_id
                self._tree_paths[tree.insert(parent,'end',text='▸  '+folder.name,
                                open=(not expanded or folder in expanded or bool(search)))]=folder
            for file in shown_scores:
                parent=self._tree_item_for(file.parent) or root_id
                icon={'.jianpu':'♫  ','.drum':'◉  ','.mtrack':'▤  '}.get(file.suffix.lower(),'  ')
                self._tree_paths[tree.insert(parent,'end',text=icon+file.stem)]=file
        self.project_label.set('当前项目 · '+self.project.name if self.project else '新建或打开一个项目')
        target=selected_path or self.path
        if target is not None:
            self._select_tree_path(target)

    def _tree_item_for(self,path):
        for item,p in self._tree_paths.items():
            if p==path:return item
        return None

    def _select_tree_path(self,path):
        if path is None:return
        item=self._tree_item_for(Path(path).resolve())
        if item:
            self.project_tree.selection_set(item)
            self.project_tree.see(item)

    def _selected_project_folder(self):
        if self.project is None:return None
        selection=self.project_tree.selection()
        if selection:
            path=self._tree_paths.get(selection[0])
            if path is not None:
                return path if path.is_dir() else path.parent
        return self.project.root

    def _on_tree_open(self,event=None):
        selected=self.project_tree.selection()
        if not selected:return
        path=self._tree_paths.get(selected[0])
        if path and path.is_file() and path.suffix.lower() in ('.jianpu','.drum','.mtrack'):
            root=self._project_for_path(path)
            if root is not None and (self.project is None or self.project.root!=root):
                self.project=ProjectWorkspace(root)
                self._register_project(root)
            try:
                if path.suffix.lower()=='.jianpu':self._open_disk_tab(path)
                else:self._open_asset_editor(path)
            except Exception as exc:messagebox.showerror('打开文件失败',str(exc))

    def _project_context_menu(self,event):
        item=self.project_tree.identify_row(event.y)
        if item:self.project_tree.selection_set(item)
        menu=self._menu(self.root)
        menu.add_command(label='打开文件',command=self._on_tree_open)
        menu.add_command(label='新建多音轨工程',command=self.new_arrangement)
        menu.add_command(label='新建鼓点',command=self.new_drum)
        menu.add_command(label='新建简谱',command=self.new_score)
        menu.add_command(label='新建子文件夹',command=self.new_subproject)
        menu.add_command(label='重命名',command=self.rename_project_item)
        menu.add_command(label='刷新',command=self.refresh_project_tree)
        menu.tk_popup(event.x_root,event.y_root)
        menu.grab_release()

    def new_subproject(self):
        if self.project is None:
            messagebox.showinfo('请先打开项目','新建或打开项目后，才能创建子文件夹。')
            return
        parent=self._selected_project_folder()
        name=simpledialog.askstring('新建子文件夹','子文件夹名称：',parent=self.root)
        if name is None:return
        try:
            path=self.project.new_folder(str(parent.relative_to(self.project.root)/validate_name(name)))
            self.refresh_project_tree()
            self._select_tree_path(path)
        except Exception as exc:messagebox.showerror('新建文件夹失败',str(exc))

    def rename_project_item(self):
        if self.project is None:return
        selection=self.project_tree.selection()
        if not selection:return
        old=self._tree_paths.get(selection[0])
        if not old or old==self.project.root:return
        name=simpledialog.askstring('重命名','请输入新名称：',initialvalue=old.name,parent=self.root)
        if name is None:return
        self._remember_active()
        if any(d.path and (d.path==old or old in d.path.parents) and d.dirty for d in self.documents):
            messagebox.showwarning('存在未保存更改','请保存该文件（或子文件夹内的文件）后再重命名。')
            return
        # Asset editors currently use independent windows, so relocating an
        # open file without updating that window would save to a stale path.
        for editor in getattr(self,'_asset_editors',{}).values():
            if editor.window.winfo_exists() and (editor.path==old or
                    (old.is_dir() and editor.path.is_relative_to(old))):
                messagebox.showwarning('请先关闭编辑器','重命名前请关闭包含该文件的鼓点/音轨编辑窗口，避免保存到旧路径。')
                return
        for editor in getattr(self,'_asset_editors',{}).values():
            if not editor.window.winfo_exists() or not hasattr(editor,'arr'):
                continue
            root=editor.path.parent
            try:
                from .arrangement import find_project_root
                root=find_project_root(editor.path)
                for track in editor.arr.tracks:
                    for clip in track.clips:
                        ref=(root/clip.source).resolve()
                        if ref==old or (old.is_dir() and ref.is_relative_to(old)):
                            messagebox.showwarning('请先关闭音轨编辑器',
                                '所选素材已被打开的多轨工程引用。请先保存并关闭多轨窗口，再重命名。')
                            return
            except (OSError,ValueError):pass
        old_is_dir=old.is_dir()
        try:
            dest=self.project.rename(old.relative_to(self.project.root),name)
            for d in self.documents:
                if d.path and (d.path==old or (old_is_dir and old in d.path.parents)):
                    d.path=dest/d.path.relative_to(old) if old_is_dir else dest
            if self.active_document:self.path=self.active_document.path
            self.refresh_project_tree()
            self._select_tree_path(dest)
            self._render_tabs()
        except Exception as exc:messagebox.showerror('重命名失败',str(exc))

    def new_drum(self):
        self._new_asset_dialog('drum','新建鼓点文件','新鼓点.drum')

    def new_arrangement(self):
        self._new_asset_dialog('mtrack','新建多音轨文件','新编排.mtrack')

    def _new_asset_dialog(self,kind,title,default):
        if self.project is None:
            messagebox.showinfo('请先打开项目','请先新建或打开一个 Melody 项目。')
            return
        folder=self._selected_project_folder()
        name=simpledialog.askstring(title,'文件名：',initialvalue=default,parent=self.root)
        if name is None:return
        try:
            name=validate_name(name)
            if not name.lower().endswith('.'+kind):name+='.'+kind
            path=self.project.new_asset(str(folder.relative_to(self.project.root)/name),kind)
            self.refresh_project_tree()
            self._open_asset_editor(path)
            self.status.set('已创建：'+str(path.relative_to(self.project.root)))
        except Exception as exc:messagebox.showerror('新建失败',str(exc))

    def open_music_asset(self):
        path=filedialog.askopenfilename(title='打开音轨或鼓点文件',
                   initialdir=str(self.project.root) if self.project else None,
                   filetypes=[('音轨/鼓点','*.mtrack *.drum')])
        if path:
            try:self._open_asset_editor(Path(path))
            except Exception as exc:messagebox.showerror('打开失败',str(exc))

    def _open_asset_editor(self,path):
        from .multitrack_gui import DrumEditor,ArrangementEditor
        path=Path(path).resolve()
        if not hasattr(self,'_asset_editors'):self._asset_editors={}
        old=self._asset_editors.get(path)
        if old is not None and old.window.winfo_exists():
            old.window.lift();old.window.focus_force()
            return old
        editor_class=DrumEditor if path.suffix.lower()=='.drum' else ArrangementEditor
        editor=editor_class(self.root,path,on_saved=self.refresh_project_tree,theme=self.theme_mode)
        self._asset_editors[path]=editor
        return editor

    def new_score_tab(self):
        if self.project is None:
            self._open_untitled_tab(parse_text(self._blank_score_text()),'未命名')
            return
        folder=self._selected_project_folder()
        name=simpledialog.askstring('新建简谱','简谱文件名：',initialvalue='新乐谱.jianpu',parent=self.root)
        if name is None:return
        try:
            name=validate_name(name)
            if not name.lower().endswith('.jianpu'):name+='.jianpu'
            path=self.project.new_score(str(folder.relative_to(self.project.root)/name),
                                        self._blank_score_text(Path(name).stem))
            self.refresh_project_tree()
            self._open_disk_tab(path)
            self.status.set('已创建项目乐谱：'+str(path.relative_to(self.project.root)))
        except Exception as exc:messagebox.showerror('新建简谱失败',str(exc))

    def open_sample_tab(self,filename):
        if filename not in self.available_samples():
            messagebox.showerror('找不到示例','无效的内置示例文件')
            return
        try:
            source=resources.files(__package__).joinpath('samples', filename).read_text(encoding='utf-8')
            score=parse_text(source)
            self._open_untitled_tab(score,f'{score.title} · 示例',is_sample=True)
            self.status.set('已打开示例副本 · 另存为项目文件不会修改原始示例')
        except Exception as exc:messagebox.showerror('示例读取失败',str(exc))

    def open_score_tab(self):
        path=filedialog.askopenfilename(title='打开简谱文件',filetypes=[('简谱','*.jianpu *.txt'),('所有文件','*.*')],
             initialdir=str(self.project.root) if self.project else None)
        if not path:return
        try:self._open_disk_tab(Path(path))
        except Exception as exc:messagebox.showerror('读取失败',str(exc))

    def save_current_to(self,target):
        try:
            target=Path(target).expanduser().resolve()
            if any(d is not self.active_document and d.path is not None
                   and d.path.resolve()==target for d in self.documents):
                messagebox.showwarning('已有打开的标签',
                    '目标路径已经在另一标签中打开。请切换到该标签或换一个文件名，以免覆盖其未保存修改。')
                return False
            if self.path!=target and target.exists():
                if not messagebox.askyesno('确认覆盖','目标文件已存在，确定覆盖吗？'):
                    return False
            target.parent.mkdir(parents=True,exist_ok=True)
            from .core import text_from_score
            target.write_text(text_from_score(self.score_model),encoding='utf-8')
            self.path=target
            self.is_sample=False
            self._modified=False
            if self.active_document:
                self.active_document.path=target
                self.active_document.is_sample=False
                self.active_document.modified=False
                self.active_document.source_dirty=False
            self.file_label.set(target.name)
            self.status.set('已保存：'+str(target))
            self._render_tabs()
            self.refresh_project_tree()
            return True
        except Exception as exc:
            messagebox.showerror('保存失败',str(exc))
            return False

    def close_workspace_window(self):
        self._remember_active()
        for d in list(self.documents):
            if d.dirty and not self._ask_save_document(d):return False
        return True
