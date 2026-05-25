"""
Vox v3.0 — Main Window
Professional dark UI. Auto-login. Settings. Voice/Face enrol.
Tray on close — voice keeps running.
"""
import tkinter as tk
from tkinter import messagebox
import threading, time, os
from datetime import datetime

# ══════════════ DESIGN TOKENS ══════════════
BG      = '#080c18'
PANEL   = '#0e1628'
CARD    = '#121e38'
TOPBAR  = '#0a1220'
INPUT   = '#0c1830'
BORDER  = '#1a2f58'
BLUE    = '#2979ff'
CYAN    = '#00e5ff'
TEAL    = '#1de9b6'
WHITE   = '#dce8ff'
MUTED   = '#5a7aaa'
DIM     = '#2e4470'
GREEN   = '#00e676'
AMBER   = '#ffab40'
RED     = '#ff5252'
UBUB    = '#0d2144'   # user bubble
JBUB    = '#091830'   # Vox bubble

FH  = ('Segoe UI', 11)
FB  = ('Segoe UI', 11, 'bold')
FS  = ('Segoe UI', 9)
FT  = ('Segoe UI', 16, 'bold')
FM  = ('Consolas', 10)
FXL = ('Segoe UI', 28, 'bold')


def _btn(parent, text, cmd, bg=BLUE, fg=WHITE, **kw):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  font=FB, relief='flat', cursor='hand2',
                  activebackground=BORDER, activeforeground=WHITE, **kw)
    return b

def _entry(parent, var, show='', width=30, **kw):
    e = tk.Entry(parent, textvariable=var, width=width, show=show,
                 bg=INPUT, fg=WHITE, font=FH,
                 insertbackground=CYAN, relief='flat', bd=0,
                 highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=BLUE, **kw)
    return e


class VoxWindow:
    def __init__(self, Vox):
        self.Vox    = Vox
        self.screen = None
        self._tray  = None

        self.root = tk.Tk()
        self.root.title("Vox — AI Desktop Assistant")
        self.root.geometry("1160x740")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # icon
        try:
            ico = os.path.join(os.path.dirname(__file__), '..', 'assets', 'Vox_icon.ico')
            if os.path.exists(ico): self.root.iconbitmap(ico)
        except Exception: pass

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self._mf = tk.Frame(self.root, bg=BG)
        self._mf.grid(row=0, column=0, sticky='nsew')
        self._mf.rowconfigure(0, weight=1)
        self._mf.columnconfigure(0, weight=1)

        # auto-login?
        auto = self.Vox.db.get_auto_login_user()
        if auto:
            self.Vox.set_user(auto)
            self._show_chat()
        else:
            self._show_login()

        self._tick()

    # ══════════════════════════════════════
    #  LOGIN
    # ══════════════════════════════════════
    def _show_login(self):
        self._clear(); self.screen = 'login'

        f = tk.Frame(self._mf, bg=BG)
        f.grid(row=0, column=0, sticky='nsew')
        f.rowconfigure(0, weight=1); f.columnconfigure(0, weight=1)

        ctr = tk.Frame(f, bg=BG)
        ctr.place(relx=.5, rely=.5, anchor='center')

        # Logo
        tk.Label(ctr, text='◉', font=('Segoe UI', 56), bg=BG, fg=CYAN).pack()
        tk.Label(ctr, text='Vox', font=FXL, bg=BG, fg=WHITE).pack()
        tk.Label(ctr, text='Advanced AI Desktop Assistant',
                 font=('Segoe UI', 12), bg=BG, fg=MUTED).pack(pady=(2, 4))

        badge = tk.Label(ctr, text="  🎤  Say 'Hey Vox' anytime — no button needed  ",
                         font=FS, bg='#061a06', fg=GREEN, padx=12, pady=5,
                         highlightthickness=1, highlightbackground=GREEN)
        badge.pack(pady=(0, 22))

        card = tk.Frame(ctr, bg=CARD, padx=44, pady=36,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack()

        tk.Label(card, text='Welcome Back', font=FT, bg=CARD, fg=WHITE).pack(anchor='w', pady=(0,20))

        self._lu = tk.StringVar()
        self._lp = tk.StringVar()
        for lbl, var, hide in [('Username', self._lu, ''), ('Password', self._lp, '●')]:
            tk.Label(card, text=lbl, font=FS, bg=CARD, fg=MUTED).pack(anchor='w')
            e = _entry(card, var, show=hide)
            e.pack(fill='x', pady=(3,14))
            if lbl == 'Username': e.focus()
            if lbl == 'Password': e.bind('<Return>', lambda _: self._login())

        self._lstat = tk.Label(card, text='', font=FS, bg=CARD, fg=RED)
        self._lstat.pack(pady=(0, 10))

        _btn(card, '  Sign In  →', self._login, pady=10).pack(fill='x', pady=(0,8))
        _btn(card, '  ◉  Face Recognition Login', self._face_login,
             bg=PANEL, pady=10,
             highlightthickness=1, highlightbackground=BORDER).pack(fill='x')

        bot = tk.Frame(ctr, bg=BG); bot.pack(pady=14)
        tk.Label(bot, text="New here?  ", font=FS, bg=BG, fg=MUTED).pack(side='left')
        lk = tk.Label(bot, text='Create Account', font=('Segoe UI',9,'underline'),
                      bg=BG, fg=CYAN, cursor='hand2')
        lk.pack(side='left')
        lk.bind('<Button-1>', lambda _: self._show_register())

        self._tlbl = tk.Label(ctr, text='', font=FS, bg=BG, fg=DIM)
        self._tlbl.pack(pady=(8,0))

    def _login(self):
        u, p = self._lu.get().strip(), self._lp.get().strip()
        if not u or not p:
            self._lstat.config(text='Enter username and password.', fg=AMBER); return
        self._lstat.config(text='Signing in…', fg=CYAN); self.root.update()
        ok, user = self.Vox.db.login(u, p)
        if ok:
            self.Vox.set_user(user); self._show_chat()
        else:
            self._lstat.config(text='Wrong username or password.', fg=RED)

    def _face_login(self):
        if not self.Vox.face.available:
            messagebox.showinfo('Face Login',
                'Install face recognition:\npip install face_recognition opencv-python')
            return
        self._lstat.config(text='📷 Looking for your face…', fg=CYAN); self.root.update()
        def cb(ok, ud):
            if ok:
                self.Vox.set_user(ud); self.root.after(0, self._show_chat)
            else:
                self.root.after(0, lambda: self._lstat.config(
                    text='Face not recognised. Try manual login.', fg=RED))
        self.Vox.face.start_recognition_thread(cb)

    # ══════════════════════════════════════
    #  REGISTER
    # ══════════════════════════════════════
    def _show_register(self):
        self._clear(); self.screen = 'register'

        f = tk.Frame(self._mf, bg=BG)
        f.grid(row=0, column=0, sticky='nsew')

        ctr = tk.Frame(f, bg=BG)
        ctr.place(relx=.5, rely=.5, anchor='center')

        tk.Label(ctr, text='◉', font=('Segoe UI', 42), bg=BG, fg=CYAN).pack()
        tk.Label(ctr, text='Create Account', font=('Segoe UI',22,'bold'),
                 bg=BG, fg=WHITE).pack()
        tk.Label(ctr, text='Join Vox — Your Personal AI Assistant',
                 font=('Segoe UI',11), bg=BG, fg=MUTED).pack(pady=(0,22))

        card = tk.Frame(ctr, bg=CARD, padx=44, pady=32,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack()

        self._rv = {}
        for lbl, key, hide in [('Full Name','name',''), ('Username','user',''),
                                ('Email (optional)','email',''),
                                ('Password','pass','●'), ('Confirm Password','pass2','●')]:
            tk.Label(card, text=lbl, font=FS, bg=CARD, fg=MUTED).pack(anchor='w')
            v = tk.StringVar(); self._rv[key] = v
            _entry(card, v, show=hide).pack(fill='x', pady=(3,10))

        self._rstat = tk.Label(card, text='', font=FS, bg=CARD, fg=RED)
        self._rstat.pack(pady=(0,8))
        _btn(card, 'Create Account', self._register, bg=TEAL, fg='#050d1a', pady=10).pack(fill='x')

        bot = tk.Frame(ctr, bg=BG); bot.pack(pady=12)
        tk.Label(bot, text='Have an account?  ', font=FS, bg=BG, fg=MUTED).pack(side='left')
        lk = tk.Label(bot, text='Sign In', font=('Segoe UI',9,'underline'),
                      bg=BG, fg=CYAN, cursor='hand2')
        lk.pack(side='left')
        lk.bind('<Button-1>', lambda _: self._show_login())

    def _register(self):
        rv = self._rv
        name = rv['name'].get().strip()
        user = rv['user'].get().strip()
        email= rv['email'].get().strip()
        pw   = rv['pass'].get()
        pw2  = rv['pass2'].get()
        if not name or not user or not pw:
            self._rstat.config(text='Name, username and password required.', fg=AMBER); return
        if len(user) < 3:
            self._rstat.config(text='Username must be 3+ characters.', fg=AMBER); return
        if len(pw) < 6:
            self._rstat.config(text='Password must be 6+ characters.', fg=AMBER); return
        if pw != pw2:
            self._rstat.config(text="Passwords don't match.", fg=RED); return
        self._rstat.config(text='Creating…', fg=CYAN); self.root.update()
        ok, msg = self.Vox.db.register(user, pw, name, email)
        if ok:
            messagebox.showinfo('Account Created', msg)
            self._show_login()
        else:
            self._rstat.config(text=msg, fg=RED)

    # ══════════════════════════════════════
    #  CHAT MAIN SCREEN
    # ══════════════════════════════════════
    def _show_chat(self):
        self._clear(); self.screen = 'chat'

        outer = tk.Frame(self._mf, bg=BG)
        outer.grid(row=0, column=0, sticky='nsew')
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        # ── SIDEBAR ──────────────────────────────
        sb = tk.Frame(outer, bg=PANEL, width=245)
        sb.grid(row=0, column=0, sticky='nsew')
        sb.grid_propagate(False)

        # branding
        br = tk.Frame(sb, bg=PANEL, pady=20)
        br.pack(fill='x')
        tk.Label(br, text='◉ Vox', font=('Segoe UI',16,'bold'),
                 bg=PANEL, fg=CYAN).pack()
        tk.Label(br, text='AI Desktop Assistant', font=FS,
                 bg=PANEL, fg=DIM).pack()

        # voice status pill
        self._vi = tk.Label(sb,
            text="  🟢  Listening for 'Hey Vox'  ",
            font=FS, bg='#061806', fg=GREEN, padx=8, pady=5,
            highlightthickness=1, highlightbackground=GREEN)
        self._vi.pack(fill='x', padx=12, pady=(0,10))

        tk.Frame(sb, bg=BORDER, height=1).pack(fill='x', padx=16)

        # user card
        user = self.Vox.current_user or {}
        name = user.get('full_name') or user.get('username','User')
        uname= user.get('username','')
        uf   = tk.Frame(sb, bg=PANEL, pady=14, padx=14); uf.pack(fill='x')
        av   = tk.Frame(uf, bg=BLUE, width=40, height=40)
        av.pack_propagate(False); av.pack(side='left', padx=(0,10))
        tk.Label(av, text=name[0].upper(), font=('Segoe UI',16,'bold'),
                 bg=BLUE, fg=WHITE).place(relx=.5,rely=.5,anchor='center')
        nf = tk.Frame(uf, bg=PANEL); nf.pack(side='left')
        tk.Label(nf, text=name[:20], font=FB, bg=PANEL, fg=WHITE).pack(anchor='w')
        tk.Label(nf, text=f'@{uname}', font=FS, bg=PANEL, fg=MUTED).pack(anchor='w')

        tk.Frame(sb, bg=BORDER, height=1).pack(fill='x', padx=16)

        # quick actions
        tk.Label(sb, text='QUICK ACTIONS', font=('Segoe UI',8,'bold'),
                 bg=PANEL, fg=DIM).pack(anchor='w', padx=16, pady=(12,4))

        qa = [
            ('▶   YouTube', 'play music on youtube'),
            ('🔍   Google Search', 'search '),
            ('📱   WhatsApp', 'open whatsapp'),
            ('📸   Screenshot', 'take a screenshot'),
            ('🕐   Time & Date', 'what time is it'),
            ('📰   Latest News', 'latest news'),
            ('🌤   Weather', 'weather today'),
            ('🔢   Calculator', 'calculate '),
            ('😄   Tell a Joke', 'tell me a joke'),
        ]
        for lbl, cmd in qa:
            b = tk.Label(sb, text=f'   {lbl}', font=FH, bg=PANEL,
                         fg=MUTED, cursor='hand2', pady=6, anchor='w')
            b.pack(fill='x')
            b.bind('<Enter>', lambda e, w=b: w.config(bg=CARD, fg=CYAN))
            b.bind('<Leave>', lambda e, w=b: w.config(bg=PANEL, fg=MUTED))
            b.bind('<Button-1>', lambda e, c=cmd: self._quick(c))

        tk.Frame(sb, bg=PANEL).pack(expand=True)
        tk.Frame(sb, bg=BORDER, height=1).pack(fill='x', padx=16)

        for lbl, fn in [('⚙   Settings',       self._settings),
                         ('👤   Register Face',  self._reg_face),
                         ('🎤   Enrol Voice',    self._enrol_voice),
                         ('🚪   Logout',         self._logout)]:
            b = tk.Label(sb, text=f'   {lbl}', font=FH, bg=PANEL,
                         fg=MUTED, cursor='hand2', pady=6, anchor='w')
            b.pack(fill='x')
            b.bind('<Enter>', lambda e, w=b: w.config(fg=WHITE))
            b.bind('<Leave>', lambda e, w=b: w.config(fg=MUTED))
            b.bind('<Button-1>', lambda e, f2=fn: f2())

        # ── MAIN AREA ────────────────────────────
        ma = tk.Frame(outer, bg=BG)
        ma.grid(row=0, column=1, sticky='nsew')
        ma.rowconfigure(1, weight=1)
        ma.columnconfigure(0, weight=1)

        # topbar
        tb = tk.Frame(ma, bg=TOPBAR, height=54); tb.grid(row=0, column=0, sticky='ew')
        tb.grid_propagate(False)
        tk.Label(tb, text='  💬  Chat with Vox', font=('Segoe UI',13,'bold'),
                 bg=TOPBAR, fg=WHITE).pack(side='left', padx=14, pady=14)
        self._clk = tk.Label(tb, text='', font=FM, bg=TOPBAR, fg=MUTED)
        self._clk.pack(side='right', padx=14)
        self._stl = tk.Label(tb, text="🟢 Listening for 'Hey Vox'",
                             font=FS, bg=TOPBAR, fg=GREEN)
        self._stl.pack(side='right', padx=14)

        # chat canvas
        cw = tk.Frame(ma, bg=BG); cw.grid(row=1, column=0, sticky='nsew')
        cw.rowconfigure(0, weight=1); cw.columnconfigure(0, weight=1)

        self._cv = tk.Canvas(cw, bg=BG, highlightthickness=0)
        self._cv.grid(row=0, column=0, sticky='nsew')
        vsb = tk.Scrollbar(cw, orient='vertical', command=self._cv.yview,
                           bg=PANEL, troughcolor=PANEL)
        vsb.grid(row=0, column=1, sticky='ns')
        self._cv.configure(yscrollcommand=vsb.set)
        self._ci = tk.Frame(self._cv, bg=BG)
        self._cw = self._cv.create_window((0,0), window=self._ci, anchor='nw')
        self._ci.bind('<Configure>',
                      lambda e: self._cv.configure(scrollregion=self._cv.bbox('all')))
        self._cv.bind('<Configure>',
                      lambda e: self._cv.itemconfig(self._cw, width=e.width))
        self._cv.bind_all('<MouseWheel>',
                          lambda e: self._cv.yview_scroll(int(-1*(e.delta/120)), 'units'))

        # welcome
        first = name.split()[0]
        self._add_Vox_msg(
            f"Hello {first}! I'm Vox, your always-on AI assistant.\n\n"
            f"Just say 'Hey Vox' and give your command — I'll speak the answer too.\n"
            f"Or type below and press Enter.\n\n"
            f"Try: 'play a song on youtube' · 'what is machine learning' · 'open notepad'"
        )

        # input bar
        ib = tk.Frame(ma, bg=TOPBAR, pady=12); ib.grid(row=2, column=0, sticky='ew')
        ii = tk.Frame(ib, bg=TOPBAR); ii.pack(fill='x', padx=14)

        self._iv = tk.StringVar()
        self._ie = tk.Entry(ii, textvariable=self._iv, font=('Segoe UI',12),
                            bg=INPUT, fg=WHITE, insertbackground=CYAN,
                            relief='flat', bd=0,
                            highlightthickness=1,
                            highlightbackground=BORDER,
                            highlightcolor=BLUE)
        self._ie.pack(side='left', fill='x', expand=True, ipady=7)
        self._ie.bind('<Return>', lambda _: self._send())
        self._ie.focus()

        _btn(ii, 'Send  →', self._send, pady=7, padx=16).pack(side='left', padx=(10,0))

        tk.Label(ib, text="🎤 Say 'Hey Vox' anytime  |  Type here + Enter",
                 font=FS, bg=TOPBAR, fg=DIM).pack(pady=(5,0))

        # start pulse animation
        threading.Thread(target=self._pulse, daemon=True).start()

    # ── CHAT HELPERS ──────────────────────────
    def _add_user_msg(self, text: str):
        f = tk.Frame(self._ci, bg=BG, pady=5); f.pack(fill='x', padx=16)
        r = tk.Frame(f, bg=BG); r.pack(side='right')
        b = tk.Frame(r, bg=UBUB, padx=14, pady=8,
                     highlightthickness=1, highlightbackground=BLUE)
        b.pack(side='right')
        tk.Label(b, text=text, font=FH, bg=UBUB, fg=WHITE,
                 wraplength=520, justify='left').pack()
        tk.Label(r, text=f"You  {datetime.now().strftime('%I:%M %p')}",
                 font=FS, bg=BG, fg=DIM).pack(anchor='e', pady=(3,0))
        self._scroll()

    def _add_Vox_msg(self, text: str):
        f = tk.Frame(self._ci, bg=BG, pady=5); f.pack(fill='x', padx=16)
        l = tk.Frame(f, bg=BG); l.pack(side='left')
        tk.Label(l, text='◉', font=('Segoe UI',17), bg=BG,
                 fg=CYAN).pack(side='left', padx=(0,10), anchor='n', pady=3)
        c = tk.Frame(l, bg=BG); c.pack(side='left')
        tk.Label(c, text='Vox', font=('Segoe UI',9,'bold'),
                 bg=BG, fg=CYAN).pack(anchor='w')
        b = tk.Frame(c, bg=JBUB, padx=14, pady=8,
                     highlightthickness=1, highlightbackground=BORDER)
        b.pack(anchor='w')
        tk.Label(b, text=text, font=FH, bg=JBUB, fg=WHITE,
                 wraplength=600, justify='left').pack(anchor='w')
        tk.Label(c, text=datetime.now().strftime('%I:%M %p'),
                 font=FS, bg=BG, fg=DIM).pack(anchor='w', pady=(3,0))
        self._scroll()

    def _add_user_message(self, t):
        self.root.after(0, lambda: self._add_user_msg(t))

    def _add_Vox_message(self, t):
        self.root.after(0, lambda: self._add_Vox_msg(t))

    def add_message(self, t, is_Vox=True):
        (self._add_Vox_msg if is_Vox else self._add_user_msg)(t)

    def _scroll(self):
        self.root.after(120, lambda: self._cv.yview_moveto(1.0))

    def _send(self):
        txt = self._iv.get().strip()
        if not txt: return
        self._iv.set('')
        self._add_user_msg(f'⌨️  {txt}')
        self.set_voice_status('⚙️  Processing…', AMBER)
        threading.Thread(target=self._proc, args=(txt,), daemon=True).start()

    def _proc(self, txt):
        try:
            r = self.Vox.process_command(txt)
            self.root.after(0, lambda: self._add_Vox_msg(r))
        except Exception as e:
            self.root.after(0, lambda: self._add_Vox_msg(f'Error: {e}'))
        finally:
            self.root.after(0, lambda: self.set_voice_status(
                "🟢 Listening for 'Hey Vox'", GREEN))

    def _quick(self, cmd: str):
        if cmd.endswith(' '):
            self._iv.set(cmd); self._ie.focus()
        else:
            self._add_user_msg(f'🖱️  {cmd}')
            self.set_voice_status('⚙️  Processing…', AMBER)
            threading.Thread(target=self._proc, args=(cmd,), daemon=True).start()

    # ── STATUS ────────────────────────────────
    def _set_status(self, t: str, c: str):   # kept for voice engine compat
        self.set_voice_status(t, c)

    def set_voice_status(self, msg: str, color: str = GREEN):
        def _do():
            try:
                if hasattr(self, '_stl') and self._stl.winfo_exists():
                    self._stl.config(text=msg, fg=color)
                if hasattr(self, '_vi') and self._vi.winfo_exists():
                    if 'listen' in msg.lower() or 'hey' in msg.lower():
                        bg, br = '#061806', GREEN
                    elif 'command' in msg.lower() or 'say' in msg.lower():
                        bg, br = '#001826', CYAN
                    elif 'process' in msg.lower():
                        bg, br = '#1a1000', AMBER
                    else:
                        bg, br = PANEL, BORDER
                    self._vi.config(text=f'  {msg}  ', fg=color, bg=bg,
                                    highlightbackground=br)
            except Exception:
                pass
        self.root.after(0, _do)

    def _pulse(self):
        s = True
        while self.screen == 'chat':
            try:
                if hasattr(self, '_vi') and self._vi.winfo_exists():
                    c = GREEN if s else '#007a40'
                    self.root.after(0, lambda col=c: self._vi.config(fg=col))
            except Exception: break
            s = not s; time.sleep(1.1)

    # ── SETTINGS ──────────────────────────────
    def _settings(self):
        win = tk.Toplevel(self.root)
        win.title('Vox Settings')
        win.geometry('540x520')
        win.configure(bg=BG); win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text='⚙  Settings', font=FT, bg=BG, fg=WHITE).pack(pady=20)

        card = tk.Frame(win, bg=CARD, padx=30, pady=24,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=(0,10))

        user = self.Vox.current_user or {}
        uid  = user.get('id', 0)

        # ── Auto-Login ──
        def _section(title, subtitle):
            tk.Frame(card, bg=BORDER, height=1).pack(fill='x', pady=(0,10))
            tk.Label(card, text=title, font=FB, bg=CARD, fg=WHITE).pack(anchor='w')
            tk.Label(card, text=subtitle, font=FS, bg=CARD, fg=MUTED,
                     wraplength=440).pack(anchor='w', pady=(2,8))

        _section('Auto-Login',
                 'Skip login screen on every launch — stays signed in permanently.')
        al_var = tk.BooleanVar(value=bool(user.get('auto_login', 0)))
        def _al():
            self.Vox.db.set_auto_login(uid, al_var.get())
            messagebox.showinfo('Auto-Login',
                f"Auto-Login {'enabled' if al_var.get() else 'disabled'}.")
        tk.Checkbutton(card, text='Enable Auto-Login (no login screen next time)',
                       variable=al_var, command=_al,
                       bg=CARD, fg=WHITE, selectcolor=BLUE,
                       activebackground=CARD, font=FH, cursor='hand2').pack(anchor='w', pady=(0,10))

        _section('Voice Recognition',
                 'Only respond to your enrolled voice. Requires enrolment first.')
        import config as cfg
        vr_var = tk.BooleanVar(value=cfg.ENABLE_VOICE_RECOGNITION)
        def _vr():
            cfg.ENABLE_VOICE_RECOGNITION = vr_var.get()
            messagebox.showinfo('Voice Recognition',
                f"Voice recognition {'enabled' if vr_var.get() else 'disabled'}.")
        tk.Checkbutton(card, text="Only respond to my enrolled voice",
                       variable=vr_var, command=_vr,
                       bg=CARD, fg=WHITE, selectcolor=BLUE,
                       activebackground=CARD, font=FH, cursor='hand2').pack(anchor='w', pady=(0,10))

        tk.Frame(card, bg=BORDER, height=1).pack(fill='x', pady=(0,10))
        info = [
            ('Wake Word',    "'Hey Vox'"),
            ('AI Model',     'Gemini 1.5 Flash + Ollama fallback'),
            ('Face Recog.',  'Installed' if self.Vox.face.available else 'Not installed (optional)'),
            ('Voice Enrolled', 'Yes' if user.get('voice_enrolled') else 'No'),
            ('Theme',        'Dark — Vox Blue'),
        ]
        for lbl, val in info:
            r = tk.Frame(card, bg=CARD); r.pack(fill='x', pady=3)
            tk.Label(r, text=lbl, font=FB, bg=CARD, fg=MUTED, width=18, anchor='w').pack(side='left')
            tk.Label(r, text=val, font=FH, bg=CARD, fg=CYAN).pack(side='left')

        _btn(win, 'Close', win.destroy, pady=8, padx=24).pack(pady=10)

    # ── FACE ENROL ────────────────────────────
    def _reg_face(self):
        if not self.Vox.current_user:
            messagebox.showinfo('Face', 'Log in first.'); return
        if not self.Vox.face.available:
            messagebox.showinfo('Face',
                'Install:\npip install face_recognition opencv-python cmake dlib'); return
        if messagebox.askyesno('Register Face',
                               'Your webcam will capture your face.\nProceed?'):
            self.set_voice_status('📷 Capturing face…', AMBER)
            uid, un = self.Vox.current_user['id'], self.Vox.current_user['username']
            def go():
                ok, msg = self.Vox.face.capture(uid, un)
                self.root.after(0, lambda: messagebox.showinfo('Face Registration', msg))
                self.root.after(0, lambda: self.set_voice_status(
                    "🟢 Listening for 'Hey Vox'", GREEN))
            threading.Thread(target=go, daemon=True).start()

    # ── VOICE ENROL ───────────────────────────
    def _enrol_voice(self):
        if not self.Vox.current_user:
            messagebox.showinfo('Voice', 'Log in first.'); return
        if not self.Vox.voice_engine:
            messagebox.showinfo('Voice', 'Voice engine not running.'); return
        un = self.Vox.current_user.get('username','user')
        if messagebox.askyesno('Enrol Voice',
            f'Vox will record your voice for 5 seconds.\n'
            f'Speak naturally after the beep. Proceed?'):
            self.set_voice_status('🎤 Recording…', CYAN)
            def go():
                ok, msg = self.Vox.voice_engine.enrol_voice(un, 5)
                if ok:
                    self.Vox.db.set_voice_enrolled(self.Vox.current_user['id'], True)
                self.root.after(0, lambda: messagebox.showinfo('Voice Enrolment', msg))
                self.root.after(0, lambda: self.set_voice_status(
                    "🟢 Listening for 'Hey Vox'", GREEN))
            threading.Thread(target=go, daemon=True).start()

    # ── LOGOUT ────────────────────────────────
    def _logout(self):
        if messagebox.askyesno('Logout',
            'Logout? Vox will keep listening in the background.'):
            self.Vox.current_user = None
            self._show_login()

    # ── UTILS ─────────────────────────────────
    def _clear(self):
        for w in self._mf.winfo_children(): w.destroy()

    def _tick(self):
        now = datetime.now().strftime('%I:%M:%S %p   %a %b %d')
        try:
            if hasattr(self, '_clk') and self._clk.winfo_exists():
                self._clk.config(text=now)
            if hasattr(self, '_tlbl') and self.screen == 'login':
                if self._tlbl.winfo_exists(): self._tlbl.config(text=now)
        except Exception: pass
        self.root.after(1000, self._tick)

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.mainloop()

    def _on_close(self):
        """Hide to system tray — voice engine keeps running."""
        self.root.withdraw()
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (64,64), (0,0,0,0))
            d   = ImageDraw.Draw(img)
            d.ellipse([4,4,60,60], fill='#00e5ff')
            d.ellipse([18,18,46,46], fill='#080c18')

            def _show(icon, item):
                icon.stop(); self._tray = None
                self.root.after(0, self.root.deiconify)

            def _quit(icon, item):
                icon.stop()
                self.Vox.shutdown()

            menu = pystray.Menu(
                pystray.MenuItem('Open Vox', _show, default=True),
                pystray.MenuItem('Exit Vox', _quit),
            )
            self._tray = pystray.Icon('Vox', img, 'Vox — Listening', menu)
            threading.Thread(target=self._tray.run, daemon=True).start()
        except Exception:
            pass  # pystray not installed — window just hides

    def close(self):
        try: self.root.quit(); self.root.destroy()
        except Exception: pass


