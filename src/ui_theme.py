"""Quiet, high-contrast Tkinter theme for the notation workstation.

Tk/ttk has no portable backdrop blur. 'Frost' here means layered muted panels,
soft borders and restrained focus/hover states, NOT an OS acrylic blur effect.
"""
from __future__ import annotations
from tkinter import ttk

PALETTES = {
    'light': {
        'window':'#EBF0F4', 'surface':'#F8FAFC', 'raised':'#FFFFFF',
        'soft':'#F1F5F8', 'line':'#DCE3EB', 'text':'#213044',
        'secondary':'#5F7186', 'muted':'#8392A3', 'accent':'#326EB4',
        'accent_hover':'#245A98', 'accent_faint':'#E6F0FB',
        'hover':'#EAF1F7', 'canvas':'#E9EEF3', 'danger':'#B44343',
    },
    'dark': {
        'window':'#1B232D', 'surface':'#252F3B', 'raised':'#2D3947',
        'soft':'#222C38', 'line':'#3A4859', 'text':'#F1F5F8',
        'secondary':'#B8C5D2', 'muted':'#90A1B2', 'accent':'#8EB8E9',
        'accent_hover':'#A6C8F0', 'accent_faint':'#314860',
        'hover':'#394A5E', 'canvas':'#1F2934', 'danger':'#F2A9A9',
    }
}


def apply_theme(root, mode='light'):
    p = PALETTES[mode]
    style = ttk.Style(root)
    style.theme_use('clam')
    root.configure(background=p['window'])
    style.configure('.', font=('Microsoft YaHei UI', 10), background=p['surface'], foreground=p['text'])
    style.configure('Root.TFrame', background=p['window'])
    style.configure('Surface.TFrame', background=p['surface'])
    style.configure('Raised.TFrame', background=p['raised'])
    style.configure('Soft.TFrame', background=p['soft'])
    style.configure('Hairline.TFrame', background=p['line'])
    style.configure('Brand.TLabel', background=p['surface'], foreground=p['text'], font=('Microsoft YaHei UI', 16, 'bold'))
    style.configure('Subtitle.TLabel', background=p['surface'], foreground=p['secondary'], font=('Microsoft YaHei UI', 9))
    style.configure('Meta.TLabel', background=p['soft'], foreground=p['secondary'], font=('Microsoft YaHei UI', 9))
    style.configure('PanelTitle.TLabel', background=p['surface'], foreground=p['text'], font=('Microsoft YaHei UI', 12, 'bold'))
    style.configure('Subheading.TLabel', background=p['surface'], foreground=p['text'], font=('Microsoft YaHei UI', 10, 'bold'))
    style.configure('Quiet.TLabel', background=p['surface'], foreground=p['secondary'], font=('Microsoft YaHei UI', 9))
    style.configure('Surface.TLabel', background=p['surface'], foreground=p['text'])
    style.configure('Selected.TLabel', background=p['accent_faint'], foreground=p['accent'], font=('Microsoft YaHei UI', 10, 'bold'), padding=(9, 7))
    style.configure('Status.TLabel', background=p['surface'], foreground=p['secondary'], font=('Microsoft YaHei UI', 9))
    style.configure('StatusRight.TLabel', background=p['surface'], foreground=p['muted'], font=('Microsoft YaHei UI', 9))
    style.configure('ContextTitle.TLabel', background=p['soft'], foreground=p['text'],
                    font=('Microsoft YaHei UI', 11, 'bold'))
    style.configure('Transport.Horizontal.TScale', background=p['surface'],
                    troughcolor=p['soft'])
    style.configure('Toolbar.TButton', padding=(7, 8), background=p['surface'], borderwidth=0,
                    relief='flat', foreground=p['text'], focusthickness=0)
    style.map('Toolbar.TButton', background=[('pressed',p['accent_faint']),('active',p['hover'])],
              foreground=[('disabled',p['muted'])])
    style.configure('Primary.TButton', padding=(10, 8), borderwidth=0, background=p['accent'],
                    foreground=('#FFFFFF' if mode=='light' else '#142231'), relief='flat', focusthickness=0)
    style.map('Primary.TButton', background=[('pressed',p['accent_hover']),('active',p['accent_hover'])])
    style.configure('Soft.TButton', padding=(10, 7), background=p['soft'], foreground=p['text'],
                    borderwidth=0, relief='flat', focusthickness=0)
    style.map('Soft.TButton', background=[('pressed',p['accent_faint']),('active',p['hover'])])
    style.configure('Small.TButton', padding=(9, 5), background=p['surface'], foreground=p['secondary'],
                    borderwidth=0, relief='flat', focusthickness=0)
    style.map('Small.TButton', background=[('active',p['hover'])])
    style.configure('ActiveTab.TButton', padding=(12,9), background=p['raised'],
                    foreground=p['accent'], borderwidth=0, relief='flat')
    style.map('ActiveTab.TButton', background=[('active',p['raised'])])
    style.configure('InactiveTab.TButton', padding=(12,9), background=p['soft'],
                    foreground=p['secondary'], borderwidth=0, relief='flat')
    style.map('InactiveTab.TButton',background=[('active',p['hover'])])
    style.configure('TabClose.TButton',padding=(3,8),background=p['soft'],
                    foreground=p['muted'],borderwidth=0,relief='flat')
    style.map('TabClose.TButton',background=[('active',p['hover'])],foreground=[('active',p['text'])])
    style.configure('Workspace.Treeview',background=p['surface'],fieldbackground=p['surface'],
                    foreground=p['text'],rowheight=31,borderwidth=0,relief='flat',
                    font=('Microsoft YaHei UI',10))
    style.map('Workspace.Treeview',background=[('selected',p['accent_faint'])],
              foreground=[('selected',p['text'])])
    style.configure('Toolbar.TMenubutton', background=p['surface'], foreground=p['text'],
                    borderwidth=0, relief='flat', padding=(12,8))
    style.map('Toolbar.TMenubutton', background=[('active',p['hover'])])
    style.configure('Primary.TMenubutton', background=p['accent'],
                    foreground=('#FFFFFF' if mode=='light' else '#142231'), borderwidth=0,
                    relief='flat', padding=(15,8))
    style.map('Primary.TMenubutton', background=[('active',p['accent_hover'])])
    style.configure('Modern.TCombobox', padding=(8,5), background=p['raised'], foreground=p['text'],
                    fieldbackground=p['raised'], borderwidth=1, bordercolor=p['line'], lightcolor=p['line'],
                    darkcolor=p['line'], arrowcolor=p['secondary'])
    style.map('Modern.TCombobox', fieldbackground=[('readonly',p['raised'])],
              foreground=[('readonly',p['text'])], background=[('readonly',p['raised'])])
    style.configure('Modern.Horizontal.TScrollbar', background=p['soft'], troughcolor=p['canvas'],
                    bordercolor=p['canvas'], arrowcolor=p['muted'])
    style.configure('Modern.Vertical.TScrollbar', background=p['soft'], troughcolor=p['canvas'],
                    bordercolor=p['canvas'], arrowcolor=p['muted'])
    return p
