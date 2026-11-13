"""Tkinter drum step sequencer and multitrack timeline editors.

Separate project-document windows for v0.3: both use the same serialized files,
renderers, and MCP functions as the rest of Melody Notation. No fake controls.
"""
from __future__ import annotations
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from .ui_theme import PALETTES
from .playback import create_player
from .audio import SAMPLE_RATE
from .midi import INSTRUMENTS
from .drums import (DrumPattern, DRUM_VOICES, DRUM_LABELS, DRUM_KITS,
                    KIT_LABELS, render_drum_pattern, export_drum_midi, export_drum_audio)
from .arrangement import (Arrangement, add_clip, source_beats, resolve_source,
                          synthesize_arrangement, export_arrangement_midi, export_arrangement_audio)

FONT = ('Microsoft YaHei UI', 10)


class BaseMusicDocument:
    def __init__(self, master, path: str | Path, on_saved=None, theme='light'):
        self.path=Path(path).resolve()
        self.on_saved=on_saved
        self.theme=theme
        self.colors=PALETTES[theme]
        self._style_fields(master)
        self.window=tk.Toplevel(master)
        self.window.configure(bg=self.colors['window'])
        self.window.geometry('1150x710')
        self.window.minsize(760,490)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.dirty=False
        self.player=None
        self.status=tk.StringVar(value='就绪')
        self.window.bind('<Control-s>',lambda e:self.save())
        self.window.bind('<Escape>',lambda e:self.stop())

    def _style_fields(self,master):
        p=self.colors
        style=ttk.Style(master)
        style.configure('Multi.TEntry',foreground=p['text'],fieldbackground=p['raised'],
                        background=p['raised'],insertcolor=p['text'],padding=(7,5),
                        bordercolor=p['line'],lightcolor=p['line'],darkcolor=p['line'])
        style.map('Multi.TEntry',fieldbackground=[('disabled',p['soft'])],
                  foreground=[('disabled',p['muted'])])
        style.configure('Multi.Treeview',background=p['raised'],fieldbackground=p['raised'],
                        foreground=p['text'],borderwidth=0,relief='flat',rowheight=29,font=FONT)
        style.map('Multi.Treeview',background=[('selected',p['accent_faint'])],
                  foreground=[('selected',p['text'])])
        style.configure('Multi.TCheckbutton',background=p['surface'],foreground=p['text'],
                        font=FONT)
        style.map('Multi.TCheckbutton',background=[('active',p['hover'])])

    def mark_dirty(self):
        self.dirty=True
        self._update_title()

    def _update_title(self):
        self.window.title(('● ' if self.dirty else '')+self.path.name+' — Melody Notation')

    def _frame(self,parent,**kwargs):
        return tk.Frame(parent,bg=self.colors['surface'],**kwargs)

    def _button(self,parent,text,command):
        return ttk.Button(parent,text=text,command=command,style='Soft.TButton')

    def _header(self,label):
        bar=self._frame(self.window)
        bar.pack(fill='x',padx=12,pady=(12,8))
        ttk.Label(bar,text=label,style='PanelTitle.TLabel').pack(side='left',padx=(8,18))
        return bar

    def _footer(self):
        ttk.Label(self.window,textvariable=self.status,style='Status.TLabel',anchor='w').pack(
            side='bottom',fill='x',padx=16,pady=8)

    def _audio(self, data):
        try:
            if self.player is None:self.player=create_player()
            self.player.stop()
            self.player.load(data,SAMPLE_RATE)
            self.player.play()
            self.status.set('正在软件内试听 · 按「停止」结束')
        except Exception as exc:
            messagebox.showerror('试听失败',str(exc),parent=self.window)

    def stop(self):
        if self.player:
            try:self.player.stop()
            except Exception:pass
        self.status.set('已停止')

    def set_theme(self, mode):
        self.theme=mode
        self.colors=PALETTES[mode]
        self._style_fields(self.window)
        for widget in self.window.winfo_children():
            self._retheme_widgets(widget)
        self.window.configure(bg=self.colors['window'])
        self.draw()

    def _retheme_widgets(self, widget):
        if isinstance(widget,tk.Frame):
            widget.configure(bg=self.colors['surface'])
        elif isinstance(widget,tk.Canvas):
            widget.configure(bg=self.colors['canvas'])
        for child in widget.winfo_children():self._retheme_widgets(child)

    def close(self):
        if self.dirty:
            answer=messagebox.askyesnocancel('尚未保存',f'{self.path.name} 有未保存更改，是否保存？',parent=self.window)
            if answer is None:return False
            if answer and not self.save():return False
        if self.player:
            try:self.player.close()
            except Exception:pass
        self.window.destroy()
        return True

    def _export_dialog(self,extension, callback):
        target=filedialog.asksaveasfilename(parent=self.window,initialdir=str(self.path.parent),
                     initialfile=self.path.stem+extension,defaultextension=extension,
                     filetypes=[(extension.upper()+' 文件','*'+extension)])
        if not target:return
        try:
            if Path(target).exists() and not messagebox.askyesno('覆盖确认','目标文件已存在，确定覆盖吗？',parent=self.window):return
            callback(Path(target))
            self.status.set('已导出：'+target)
        except Exception as exc:messagebox.showerror('导出失败',str(exc),parent=self.window)


class DrumEditor(BaseMusicDocument):
    STEP_W=30
    LEFT=132
    TOP=68
    ROW_H=78

    def __init__(self, master, path, on_saved=None, theme='light'):
        super().__init__(master,path,on_saved,theme)
        self.pattern=DrumPattern.load(self.path)
        self._update_title()
        bar=self._header('鼓点步进编辑器   ·   .drum')
        self._button(bar,'保存',self.save).pack(side='left',padx=4)
        self._button(bar,'▶ 试听',self.play).pack(side='left',padx=4)
        self._button(bar,'■ 停止',self.stop).pack(side='left',padx=4)
        for ext,label,fun in [('.mid','MIDI',export_drum_midi),('.wav','WAV',export_drum_audio),('.mp3','MP3',export_drum_audio)]:
            self._button(bar,'导出 '+label,lambda e=ext,f=fun:self._export_dialog(e,lambda path:(self._validate_fields() and f(self.pattern,path)))).pack(side='left',padx=2)
        options=self._frame(self.window)
        options.pack(fill='x',padx=12,pady=3)
        self.title_var=tk.StringVar(value=self.pattern.title)
        self.bpm_var=tk.StringVar(value=str(self.pattern.bpm))
        self.bars_var=tk.StringVar(value=str(self.pattern.bars))
        self.kit_var=tk.StringVar(value=self.pattern.kit)
        for text,var,width in [('名称',self.title_var,21),('BPM',self.bpm_var,6),('小节数',self.bars_var,5)]:
            ttk.Label(options,text=text,style='Surface.TLabel').pack(side='left',padx=(11,5))
            ttk.Entry(options,textvariable=var,width=width,style='Multi.TEntry').pack(side='left')
        ttk.Label(options,text='鼓组',style='Surface.TLabel').pack(side='left',padx=(14,5))
        kit=ttk.Combobox(options,textvariable=self.kit_var,values=DRUM_KITS,width=12,state='readonly',style='Modern.TCombobox')
        kit.pack(side='left')
        kit.bind('<<ComboboxSelected>>',lambda e:self.apply_settings())
        self._button(options,'应用设置',self.apply_settings).pack(side='left',padx=9)
        hint=ttk.Label(self.window,text='点击方格切换鼓点 · 点击轨道下方 + 新增 · 右键轨道名可重命名、切换鼓声或删除 · 每小节 16 步',
                       style='Quiet.TLabel')
        hint.pack(anchor='w',padx=24,pady=(3,7))
        frame=self._frame(self.window)
        frame.pack(fill='both',expand=True,padx=12,pady=(0,12))
        self.canvas=tk.Canvas(frame,bg=self.colors['canvas'],highlightthickness=0)
        self.canvas.pack(side='top',fill='both',expand=True)
        scroll=ttk.Scrollbar(frame,orient='horizontal',command=self.canvas.xview)
        scroll.pack(side='bottom',fill='x')
        self.canvas.configure(xscrollcommand=scroll.set)
        self.canvas.bind('<Button-1>',self._on_click)
        self.canvas.bind('<Button-3>',self._on_right_click)
        self.canvas.bind('<Double-Button-1>',self._on_double_click)
        self._footer()
        self.draw()

    def apply_settings(self):
        try:
            title=self.title_var.get().strip();bpm=int(self.bpm_var.get());bars=int(self.bars_var.get())
            if not title:raise ValueError('请输入鼓点标题')
            if bars<self.pattern.bars and any(i>=bars*16 for v in self.pattern.hits.values() for i in v):
                if not messagebox.askyesno('截断确认','缩短小节数会删除末尾鼓点，确定继续吗？',parent=self.window):return
            self.pattern.title=title
            self.pattern.bpm=bpm
            self.pattern.kit=self.kit_var.get()
            self.pattern.resize_bars(bars)
            self.pattern.validate()
            self.mark_dirty();self.draw()
            return True
        except Exception as exc:
            messagebox.showerror('设置无效',str(exc),parent=self.window)
            return False

    def draw(self):
        cv=self.canvas;p=self.colors
        cv.delete('all')
        w=self.LEFT+self.pattern.steps*self.STEP_W+32
        h=self.TOP+(len(self.pattern.tracks)+1)*self.ROW_H+15
        cv.configure(scrollregion=(0,0,w,h))
        for b in range(self.pattern.bars):
            x=self.LEFT+b*16*self.STEP_W
            cv.create_text(x+8,34,text=f'{b+1} 小节',anchor='w',font=FONT,fill=p['secondary'])
        for vi,track in enumerate(self.pattern.tracks):
            y=self.TOP+vi*self.ROW_H
            cv.create_text(16,y+27,text=track.name,anchor='w',font=FONT,fill=p['text'])
            for step in range(self.pattern.steps):
                x=self.LEFT+step*self.STEP_W
                active=step in self.pattern.hits[track.id]
                fill=p['accent'] if active else (p['raised'] if step//4%2==0 else p['soft'])
                cv.create_rectangle(x+2,y+3,x+self.STEP_W-3,y+52,fill=fill,
                                    outline=p['line'],width=1,tags=(f'cell-{track.id}-{step}',))
                if active:
                    cv.create_oval(x+12,y+19,x+18,y+25,fill=p['raised'],outline='')
                if step%4==0:
                    cv.create_line(x,y,x,y+57,fill=p['secondary'],width=1)
            cv.create_line(10,y+59,w-20,y+59,fill=p['line'])
        add_y=self.TOP+len(self.pattern.tracks)*self.ROW_H
        cv.create_text(18,add_y+27,text='＋ 添加鼓轨',anchor='w',font=FONT,fill=p['accent'],tags=('drum-add',))
        cv.create_text(self.LEFT,12,text='1 拍 = 4 步 · 点击方格编辑',anchor='w',fill=p['muted'],font=FONT)

    def _on_click(self,event):
        x=self.canvas.canvasx(event.x);y=self.canvas.canvasy(event.y)
        step=int((x-self.LEFT)//self.STEP_W)
        row=int((y-self.TOP)//self.ROW_H)
        if 0<=x<self.LEFT and row==len(self.pattern.tracks):
            try:
                track=self.pattern.add_track()
                self.mark_dirty();self.draw()
                self.status.set('新增鼓轨：'+track.name)
            except Exception as exc:messagebox.showerror('无法新增音轨',str(exc),parent=self.window)
            return
        if 0<=step<self.pattern.steps and 0<=row<len(self.pattern.tracks) and self.TOP+row*self.ROW_H<=y<self.TOP+row*self.ROW_H+57:
            track=self.pattern.tracks[row]
            self.pattern.toggle(track.id,step)
            self.mark_dirty();self.draw()
            self.status.set(f'{track.name} · 小节 {step//16+1} · 第 {step%16+1} 步')

    def _track_at(self,event):
        x=self.canvas.canvasx(event.x);y=self.canvas.canvasy(event.y)
        row=int((y-self.TOP)//self.ROW_H)
        if x<self.LEFT and 0<=row<len(self.pattern.tracks):
            return self.pattern.tracks[row]
        return None

    def _rename_track(self,track_id):
        track=self.pattern.track(track_id)
        name=simpledialog.askstring('重命名鼓轨','音轨名称',initialvalue=track.name,parent=self.window)
        if name is None:return
        try:
            self.pattern.rename_track(track_id,name)
            self.mark_dirty();self.draw()
        except Exception as exc:messagebox.showerror('无法重命名',str(exc),parent=self.window)

    def _delete_track(self,track_id):
        if self.pattern.hits[track_id] and not messagebox.askyesno('删除鼓轨',
            '删除音轨也会删除其所有节奏点，确定继续吗？',parent=self.window):return
        try:
            self.pattern.remove_track(track_id)
            self.mark_dirty();self.draw()
        except Exception as exc:messagebox.showerror('无法删除',str(exc),parent=self.window)

    def _on_double_click(self,event):
        track=self._track_at(event)
        if track:self._rename_track(track.id)

    def _on_right_click(self,event):
        track=self._track_at(event)
        if not track:return
        menu=tk.Menu(self.window,tearoff=0)
        menu.add_command(label='重命名',command=lambda:self._rename_track(track.id))
        sound_menu=tk.Menu(menu,tearoff=0)
        for sound in DRUM_VOICES:
            sound_menu.add_command(label=DRUM_LABELS[sound],
                command=lambda snd=sound,tid=track.id:self._set_track_sound(tid,snd))
        menu.add_cascade(label='鼓声类型',menu=sound_menu)
        menu.add_separator()
        menu.add_command(label='删除鼓轨',command=lambda:self._delete_track(track.id))
        menu.tk_popup(event.x_root,event.y_root)
        menu.grab_release()

    def _set_track_sound(self,track_id,sound):
        try:
            self.pattern.set_track_sound(track_id,sound)
            self.mark_dirty();self.draw()
        except Exception as exc:messagebox.showerror('无法设置鼓声',str(exc),parent=self.window)

    def play(self):
        if not self._validate_fields():return
        self._audio(render_drum_pattern(self.pattern))

    def _validate_fields(self):
        try:
            if (self.title_var.get()!=self.pattern.title or self.bpm_var.get()!=str(self.pattern.bpm)
                or self.bars_var.get()!=str(self.pattern.bars) or self.kit_var.get()!=self.pattern.kit):
                if not self.apply_settings():return False
            self.pattern.validate();return True
        except Exception as exc:
            messagebox.showerror('请先修正参数',str(exc),parent=self.window)
            return False

    def save(self):
        if not self._validate_fields():return False
        try:
            self.pattern.save(self.path)
            self.dirty=False;self._update_title()
            if self.on_saved:self.on_saved()
            self.status.set('鼓点已保存')
            return True
        except Exception as exc:
            messagebox.showerror('保存失败',str(exc),parent=self.window);return False


class ArrangementEditor(BaseMusicDocument):
    TRACK_HEIGHT=71
    LEFT=178
    SCALE=31
    TOP=51

    def __init__(self,master,path,on_saved=None,theme='light'):
        super().__init__(master,path,on_saved,theme)
        self.arr=Arrangement.load(self.path)
        self.selected_track=None
        self.selected_clip=None
        self._update_title()
        top=self._header('多音轨编排   ·   .mtrack')
        self._button(top,'保存',self.save).pack(side='left',padx=3)
        self._button(top,'加入乐谱 / 鼓点',self.import_file).pack(side='left',padx=3)
        self._button(top,'追加片段',self.append_clip).pack(side='left',padx=3)
        self._button(top,'▶ 试听',self.play).pack(side='left',padx=3)
        self._button(top,'■ 停止',self.stop).pack(side='left',padx=3)
        for ext,label,callback in [('.mid','MIDI',export_arrangement_midi),('.wav','WAV',export_arrangement_audio),('.mp3','MP3',export_arrangement_audio)]:
            self._button(top,label,lambda e=ext,f=callback:self._export_dialog(e,lambda out:f(self.arr,self.path,out))).pack(side='left',padx=2)
        settings=self._frame(self.window)
        settings.pack(fill='x',padx=12,pady=(0,7))
        self.title_var=tk.StringVar(value=self.arr.title);self.bpm_var=tk.StringVar(value=str(self.arr.bpm))
        ttk.Label(settings,text='工程名称',style='Surface.TLabel').pack(side='left',padx=(8,4))
        ttk.Entry(settings,textvariable=self.title_var,width=23,style='Multi.TEntry').pack(side='left')
        ttk.Label(settings,text='BPM',style='Surface.TLabel').pack(side='left',padx=(15,4))
        ttk.Entry(settings,textvariable=self.bpm_var,width=7,style='Multi.TEntry').pack(side='left')
        self._button(settings,'应用',self.apply_header).pack(side='left',padx=(8,23))
        for label,callback in [('轨道上移',lambda:self.move_track(-1)),('轨道下移',lambda:self.move_track(1)),
                               ('静音',self.toggle_mute),('Solo',self.toggle_solo),('删除轨道',self.delete_track)]:
            self._button(settings,label,callback).pack(side='left',padx=2)

        body=self._frame(self.window)
        body.pack(fill='both',expand=True,padx=12,pady=(0,12))
        body.columnconfigure(1,weight=1)
        body.rowconfigure(0,weight=1)
        left=self._frame(body,width=265)
        left.grid(row=0,column=0,sticky='ns',padx=(0,6))
        left.grid_propagate(False)
        ttk.Label(left,text='音轨 / 片段',style='PanelTitle.TLabel').pack(anchor='w',padx=8,pady=(7,10))
        self.tree=ttk.Treeview(left,show='tree',selectmode='browse',height=16,style='Multi.Treeview')
        self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self._on_tree_select)
        cv_frame=self._frame(body)
        cv_frame.grid(row=0,column=1,sticky='nsew')
        self.canvas=tk.Canvas(cv_frame,bg=self.colors['canvas'],highlightthickness=0)
        self.canvas.pack(fill='both',expand=True)
        xscroll=ttk.Scrollbar(cv_frame,orient='horizontal',command=self.canvas.xview)
        xscroll.pack(fill='x')
        self.canvas.configure(xscrollcommand=xscroll.set)
        self.canvas.bind('<Button-1>',self._on_canvas_click)
        inspector=self._frame(body,width=248)
        inspector.grid(row=0,column=2,sticky='ns',padx=(8,0))
        inspector.grid_propagate(False)
        ttk.Label(inspector,text='片段属性',style='PanelTitle.TLabel').pack(anchor='w',pady=(7,12))
        self.clip_info=tk.StringVar(value='点击片段进行编辑')
        ttk.Label(inspector,textvariable=self.clip_info,style='Quiet.TLabel',wraplength=230).pack(anchor='w',pady=(0,9))
        self.start_var=tk.StringVar(value='0')
        self.trim_a_var=tk.StringVar(value='0')
        self.trim_b_var=tk.StringVar(value='')
        self.gain_var=tk.StringVar(value='1.00')
        self.reverse_var=tk.BooleanVar(value=False)
        self.inst_var=tk.StringVar(value='piano')
        for label,var in [('起点（拍）',self.start_var),('裁剪起点（拍）',self.trim_a_var),
                          ('裁剪终点（留空=全长）',self.trim_b_var),('音量 0–2',self.gain_var)]:
            ttk.Label(inspector,text=label,style='Quiet.TLabel').pack(anchor='w',pady=(6,2))
            ttk.Entry(inspector,textvariable=var,width=23,style='Multi.TEntry').pack(fill='x',pady=(0,2))
        ttk.Checkbutton(inspector,text='反转片段中的音符顺序',variable=self.reverse_var,style='Multi.TCheckbutton').pack(anchor='w',pady=(10,3))
        ttk.Label(inspector,text='旋律轨音色',style='Quiet.TLabel').pack(anchor='w',pady=(6,2))
        self.instrument_box=ttk.Combobox(inspector,textvariable=self.inst_var,values=list(INSTRUMENTS),state='readonly',style='Modern.TCombobox')
        self.instrument_box.pack(fill='x',pady=(0,12))
        self._button(inspector,'应用片段修改',self.apply_clip).pack(fill='x',pady=2)
        move_row=self._frame(inspector)
        move_row.pack(fill='x',pady=(8,4))
        self._button(move_row,'◀ 4 拍',lambda:self.shift_clip(-4)).pack(side='left',expand=True,fill='x',padx=(0,3))
        self._button(move_row,'4 拍 ▶',lambda:self.shift_clip(4)).pack(side='left',expand=True,fill='x',padx=(3,0))
        self._button(inspector,'删除选中片段',self.delete_clip).pack(fill='x',pady=4)
        ttk.Label(inspector,text='裁剪不会改写原 .jianpu/.drum；反转只改变事件时间顺序，不倒放音频波形。',
                  style='Quiet.TLabel',wraplength=235).pack(anchor='w',pady=(18,0))
        self._footer()
        self.draw()

    def _selected(self):
        if self.selected_track is None or self.selected_track>=len(self.arr.tracks):
            return None,None
        t=self.arr.tracks[self.selected_track]
        c=t.clips[self.selected_clip] if self.selected_clip is not None and self.selected_clip<len(t.clips) else None
        return t,c

    def _select_clip(self,ti,ci=None):
        self.selected_track=ti
        self.selected_clip=ci
        track,clip=self._selected()
        if clip is not None:
            self.clip_info.set(f'{track.name} / {Path(clip.source).name}')
            self.start_var.set(f'{clip.start_beat:g}')
            self.trim_a_var.set(f'{clip.trim_start:g}')
            self.trim_b_var.set('' if clip.trim_end is None else f'{clip.trim_end:g}')
            self.gain_var.set(f'{clip.gain:g}')
            self.reverse_var.set(clip.reversed)
        elif track is not None:self.clip_info.set(f'选中轨道：{track.name}')
        else:self.clip_info.set('请选择片段')
        self.inst_var.set(track.instrument if track else 'piano')
        self.draw()

    def _on_tree_select(self,event=None):
        sel=self.tree.selection()
        if not sel:return
        parts=sel[0].split(':')
        try:
            ti=int(parts[1]);ci=int(parts[2]) if len(parts)>2 else None
            if ti != self.selected_track or ci != self.selected_clip:
                self._select_clip(ti,ci)
        except (ValueError,IndexError):pass

    def _on_canvas_click(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        ti=int((y-self.TOP)//self.TRACK_HEIGHT)
        if not 0<=ti<len(self.arr.tracks):return
        for ci,clip in enumerate(self.arr.tracks[ti].clips):
            try:
                src=resolve_source(self.path,clip.source)
                end=source_beats(src) if clip.trim_end is None else clip.trim_end
                width=(end-clip.trim_start)*self.SCALE
            except Exception:continue
            x1=self.LEFT+clip.start_beat*self.SCALE
            if x1<=x<=x1+width:
                self._select_clip(ti,ci)
                key=f't:{ti}:{ci}'
                if self.tree.exists(key):self.tree.selection_set(key)
                return
        self._select_clip(ti)
        key=f't:{ti}'
        if self.tree.exists(key):self.tree.selection_set(key)

    def draw(self):
        p=self.colors;cv=self.canvas;cv.delete('all')
        tree=self.tree
        tree.delete(*tree.get_children())
        max_beat=16.
        for ti,t in enumerate(self.arr.tracks):
            key=f't:{ti}'
            tags=('🔇' if t.muted else '')+('★' if t.solo else '')
            tree.insert('','end',iid=key,text=f'{ti+1:02d}  {t.name}  {tags}',open=True)
            for ci,c in enumerate(t.clips):
                tree.insert(key,'end',iid=f't:{ti}:{ci}',text=f'↳ {Path(c.source).name} @ {c.start_beat:g}')
                try:
                    src=resolve_source(self.path,c.source)
                    end=source_beats(src) if c.trim_end is None else c.trim_end
                    max_beat=max(max_beat,c.start_beat+end-c.trim_start+4)
                except Exception:pass
        width=self.LEFT+max_beat*self.SCALE+36
        height=max(270,self.TOP+max(1,len(self.arr.tracks))*self.TRACK_HEIGHT+30)
        cv.configure(scrollregion=(0,0,width,height))
        for beat in range(int(max_beat)+1):
            x=self.LEFT+beat*self.SCALE
            color=p['secondary'] if beat%4==0 else p['line']
            cv.create_line(x,30,x,height,fill=color,width=1)
            if beat%4==0:
                cv.create_text(x+3,13,text=f'{beat//4+1}',anchor='nw',fill=p['secondary'],font=FONT)
        cv.create_text(14,14,text='音轨 / 小节',anchor='nw',fill=p['secondary'],font=FONT)
        for ti,t in enumerate(self.arr.tracks):
            y=self.TOP+ti*self.TRACK_HEIGHT
            cv.create_rectangle(0,y,self.LEFT-2,y+self.TRACK_HEIGHT-2,
                                fill=p['soft'],outline=p['line'])
            cv.create_text(12,y+13,anchor='nw',text=f'{ti+1:02d}  {t.name[:15]}',font=FONT,fill=p['text'])
            flags=('静音 ' if t.muted else '')+('Solo ' if t.solo else '')
            cv.create_text(12,y+42,anchor='nw',text=(flags or ('鼓点' if t.kind=='drum' else t.instrument)),
                           font=('Microsoft YaHei UI',9),fill=p['secondary'])
            cv.create_line(self.LEFT,y+self.TRACK_HEIGHT-2,width,y+self.TRACK_HEIGHT-2,fill=p['line'])
            for ci,clip in enumerate(t.clips):
                try:
                    src=resolve_source(self.path,clip.source)
                    length=(source_beats(src) if clip.trim_end is None else clip.trim_end)-clip.trim_start
                except Exception:length=1
                x=self.LEFT+clip.start_beat*self.SCALE
                color=p['accent_faint'] if t.kind=='melody' else p['hover']
                if self.selected_track==ti and self.selected_clip==ci:color=p['accent']
                selected=(self.selected_track==ti and self.selected_clip==ci)
                cv.create_rectangle(x+1,y+9,x+max(12,length*self.SCALE)-3,y+57,
                                    fill=color,outline=p['accent'] if selected else p['line'],width=2 if selected else 1)
                cv.create_text(x+9,y+22,text=('↶ ' if clip.reversed else '')+Path(clip.source).stem[:24],
                               anchor='w',font=('Microsoft YaHei UI',9),fill=('#FFFFFF' if selected and self.theme=='light' else p['text']))
                cv.create_text(x+9,y+42,text=f'{length:g} 拍',anchor='w',
                               font=('Microsoft YaHei UI',8),fill=('#FFFFFF' if selected and self.theme=='light' else p['secondary']))
        key = (f't:{self.selected_track}:{self.selected_clip}' if self.selected_clip is not None else f't:{self.selected_track}')
        if self.selected_track is not None and tree.exists(key):
            tree.selection_set(key)
        if not self.arr.tracks:
            cv.create_text(self.LEFT+24,self.TOP+52,text='点击「加入乐谱 / 鼓点」，开始多轨编排',
                           anchor='w',fill=p['muted'],font=FONT)

    def apply_header(self):
        try:
            title=self.title_var.get().strip();bpm=int(self.bpm_var.get())
            if not title or not 20<=bpm<=400:raise ValueError('标题或 BPM 不合法')
            self.arr.title=title;self.arr.bpm=bpm
            self.mark_dirty();self.draw()
        except Exception as exc:messagebox.showerror('设置失败',str(exc),parent=self.window)

    def _choose_source(self):
        return filedialog.askopenfilename(parent=self.window,title='加入项目内的简谱或鼓点',
                    initialdir=str(self.path.parent),
                    filetypes=[('Melody 乐谱及鼓点','*.jianpu *.drum'),('简谱','*.jianpu'),('鼓点','*.drum')])

    def _add(self,append=False):
        selected=self.selected_track if append else None
        candidate=self._choose_source()
        if not candidate:return
        try:
            target=Path(candidate).resolve()
            from .arrangement import find_project_root
            root=find_project_root(self.path)
            if not target.is_relative_to(root):
                if not messagebox.askyesno('导入外部文件',
                    '此文件不在当前项目内。是否将副本复制到项目的「导入素材」文件夹，再作为音轨？\n原文件不会修改。',
                    parent=self.window):return
                import shutil
                imported=root/'导入素材'
                imported.mkdir(exist_ok=True)
                destination=imported/target.name
                counter=2
                while destination.exists():
                    destination=imported/f'{target.stem}_{counter}{target.suffix}'
                    counter+=1
                shutil.copy2(target,destination)
                target=destination
                if self.on_saved:self.on_saved()
            # Reject malformed sources before adding a clip.
            if target.suffix.lower()=='.jianpu':
                from .core import parse_text
                parse_text(target.read_text(encoding='utf-8'),strict=True)
            else:
                DrumPattern.load(target)
            if append:
                if selected is None:raise ValueError('请先选择要追加片段的音轨')
                t=self.arr.tracks[selected]
                if t.kind!=('drum' if target.suffix.lower()=='.drum' else 'melody'):
                    raise ValueError('追加的片段必须与选中音轨同类型')
                # Default to the right side of the last clip.
                start=max((c.start_beat+(source_beats(resolve_source(self.path,c.source)) if c.trim_end is None else c.trim_end)-c.trim_start
                           for c in t.clips),default=0)
            else:start=0
            ti=add_clip(self.arr,self.path,target,track_index=selected,start_beat=start)
            self._select_clip(ti,len(self.arr.tracks[ti].clips)-1)
            self.mark_dirty()
        except Exception as exc:messagebox.showerror('导入失败',str(exc),parent=self.window)

    def import_file(self):self._add(False)
    def append_clip(self):self._add(True)

    def apply_clip(self):
        t,c=self._selected()
        if c is None:return
        try:
            start=float(self.start_var.get());a=float(self.trim_a_var.get())
            b=float(self.trim_b_var.get()) if self.trim_b_var.get().strip() else None
            gain=float(self.gain_var.get())
            full=source_beats(resolve_source(self.path,c.source))
            if start<0 or a<0 or (b is not None and b>full) or (b or full)<=a or not 0<=gain<=2:
                raise ValueError(f'片段源长度为 {full:g} 拍；起点/裁剪/音量超出允许范围')
            c.start_beat=start;c.trim_start=a;c.trim_end=b;c.gain=gain;c.reversed=self.reverse_var.get()
            if t.kind=='melody':t.instrument=self.inst_var.get()
            self.arr.validate();self.mark_dirty();self.draw()
            self.status.set('片段参数已更新，源文件未改动')
        except Exception as exc:messagebox.showerror('片段编辑失败',str(exc),parent=self.window)

    def shift_clip(self,beats):
        _,c=self._selected()
        if c is None:return
        c.start_beat=max(0,c.start_beat+beats)
        self.start_var.set(f'{c.start_beat:g}')
        self.mark_dirty();self.draw()

    def delete_clip(self):
        t,c=self._selected()
        if c is None:return
        t.clips.pop(self.selected_clip)
        self._select_clip(self.selected_track)
        self.mark_dirty()

    def move_track(self,delta):
        if self.selected_track is None:return
        try:
            new=self.selected_track+delta
            self.arr.move_track(self.selected_track,delta)
            self._select_clip(new,None)
            self.mark_dirty()
        except IndexError:pass

    def delete_track(self):
        if self.selected_track is None:return
        t=self.arr.tracks[self.selected_track]
        if messagebox.askyesno('删除轨道',f'删除音轨「{t.name}」及其片段？\n不会删除源文件。',parent=self.window):
            self.arr.tracks.pop(self.selected_track)
            self.selected_track=None;self.selected_clip=None
            self.mark_dirty();self.draw()

    def toggle_mute(self):
        t,_=self._selected()
        if t:
            t.muted=not t.muted;self.mark_dirty();self.draw()

    def toggle_solo(self):
        t,_=self._selected()
        if t:
            t.solo=not t.solo;self.mark_dirty();self.draw()

    def _validate(self):
        try:
            if self.title_var.get()!=self.arr.title or self.bpm_var.get()!=str(self.arr.bpm):
                title=self.title_var.get().strip();bpm=int(self.bpm_var.get())
                if not title or not 20<=bpm<=400:raise ValueError('标题或 BPM 不合法')
                self.arr.title=title;self.arr.bpm=bpm;self.mark_dirty()
            self.arr.validate()
            return True
        except Exception as exc:messagebox.showerror('工程参数错误',str(exc),parent=self.window);return False

    def play(self):
        if not self._validate():return
        try:self._audio(synthesize_arrangement(self.arr,self.path))
        except Exception as exc:messagebox.showerror('混音失败',str(exc),parent=self.window)

    def save(self):
        if not self._validate():return False
        try:
            self.arr.save(self.path)
            self.dirty=False;self._update_title()
            if self.on_saved:self.on_saved()
            self.status.set('编排已保存')
            return True
        except Exception as exc:messagebox.showerror('保存失败',str(exc),parent=self.window);return False
