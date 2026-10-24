"""
Vox "Nova AI" Edition — Modern High-Fidelity UI
==============================================
Inspired by Nova AI design. Featuring:
- Animated Central Orb (Canvas-based)
- Glassmorphism Aesthetic
- 3-Column Pro Layout
- CustomTkinter Integration
"""

from rlottie_python import LottieAnimation
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import time
import math
import os
import re
from datetime import datetime
from tkinter import messagebox

# ══════════════ DESIGN TOKENS ══════════════
BG_COLOR       = "#060810"
SIDEBAR_COLOR  = "#0B0E1A"
CARD_COLOR     = "#12182B"
ACCENT_BLUE    = "#4D94FF"
ACCENT_PURPLE  = "#A64DFF"
TEXT_MAIN      = "#E6E6E6"
TEXT_MUTED     = "#8E97B0"
USER_BUBBLE    = "#1A2A4D"
VOX_BUBBLE     = "#111827"
SUCCESS_GREEN  = "#4CAF50"
WARNING_AMBER  = "#FFC107"
ERROR_RED      = "#FF5252"

# Fonts
FONT_MAIN      = ("Segoe UI", 11)
FONT_BOLD      = ("Segoe UI", 11, "bold")
FONT_HEADING   = ("Segoe UI", 18, "bold")
FONT_LOGO      = ("Segoe UI", 22, "bold")

ctk.set_appearance_mode("dark")

class AnimatedOrb(tk.Canvas):
    """
    Central animated orb using pre-cached Lottie animation frames.
    Zero CPU impact during playback for smooth, professional results.
    """
    def __init__(self, parent, size=450, **kwargs):
        super().__init__(parent, width=size, height=size, bg=BG_COLOR, 
                         highlightthickness=0, **kwargs)
        self.size = size
        self.center = size // 2
        
        # Load and cache animation frames
        asset_path = os.path.join(os.path.dirname(__file__), "..", "assets", "orb.json")
        self.frames = []
        self._load_and_cache(asset_path)
            
        self.current_frame = 0
        self.running = True
        self.state = "idle" 
        
        self.image_id = self.create_image(self.center, self.center, image=self.frames[0])
        self._animate()

    def _load_and_cache(self, path):
        try:
            anim = LottieAnimation.from_file(path)
            total_frames = anim.lottie_animation_get_totalframe()
            self.fps = anim.lottie_animation_get_framerate()
            
            # Pre-render all frames to memory
            for i in range(total_frames):
                pil_img = anim.render_pillow_frame(i)
                # Resize once during caching
                if pil_img.size != (self.size, self.size):
                    pil_img = pil_img.resize((self.size, self.size), Image.Resampling.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(pil_img))
        except Exception as e:
            print(f"Error caching Lottie frames: {e}")
            # Fallback if loading fails
            self.frames = [ImageTk.PhotoImage(Image.new("RGB", (self.size, self.size), BG_COLOR))]

    def set_state(self, state):
        self.state = state

    def _animate(self):
        if not self.running: return
        
        # Update image
        self.itemconfig(self.image_id, image=self.frames[self.current_frame])
        
        # Next frame
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        # Adjust speed based on state
        delay = int(1000 / self.fps)
        if self.state == "listening": delay = max(10, int(delay * 0.8))
        elif self.state == "thinking": delay = int(delay * 1.2)
        
        self.after(delay, self._animate)

class VoxWindow:
    def __init__(self, Vox):
        self.Vox = Vox
        self.root = ctk.CTk()
        self.root.title("Vox")
        self.root.geometry("1280x800")
        self.root.configure(fg_color=BG_COLOR)
        
        self.current_screen = None
        
        # Logic state
        self.last_status = "idle"
        
        # Setup UI
        auto = self.Vox.db.get_auto_login_user()
        if auto:
            self.Vox.set_user(auto)
            self._show_chat()
        else:
            self._show_login()

    def _clear(self):
        for slave in self.root.grid_slaves():
            slave.destroy()
        for slave in self.root.pack_slaves():
            slave.destroy()

    def _show_login(self):
        self._clear()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        login_frame = ctk.CTkFrame(self.root, fg_color=BG_COLOR)
        login_frame.grid(row=0, column=0)

        # Logo
        logo_label = ctk.CTkLabel(login_frame, text="Nova AI", font=FONT_LOGO, text_color=ACCENT_BLUE)
        logo_label.pack(pady=(0, 10))
        
        sub_label = ctk.CTkLabel(login_frame, text="Your AI Assistant. Your Thinking Partner.", 
                                font=FONT_MAIN, text_color=TEXT_MUTED)
        sub_label.pack(pady=(0, 30))

        # Login Card
        card = ctk.CTkFrame(login_frame, fg_color=SIDEBAR_COLOR, corner_radius=15, width=400, height=450)
        card.pack(padx=20, pady=10)
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="Welcome Back", font=FONT_HEADING, text_color=TEXT_MAIN).pack(pady=(40, 20))

        self.u_var = tk.StringVar()
        self.p_var = tk.StringVar()

        u_entry = ctk.CTkEntry(card, placeholder_text="Username", textvariable=self.u_var, 
                               width=300, height=45, fg_color=BG_COLOR, border_color=ACCENT_BLUE)
        u_entry.pack(pady=10)

        p_entry = ctk.CTkEntry(card, placeholder_text="Password", textvariable=self.p_var, 
                               show="●", width=300, height=45, fg_color=BG_COLOR, border_color=ACCENT_BLUE)
        p_entry.pack(pady=10)

        self.login_status = ctk.CTkLabel(card, text="", font=FONT_MAIN, text_color=ERROR_RED)
        self.login_status.pack(pady=5)

        login_btn = ctk.CTkButton(card, text="Sign In", command=self._login, 
                                  width=300, height=45, fg_color=ACCENT_BLUE, hover_color="#3D7BD9")
        login_btn.pack(pady=20)

        face_btn = ctk.CTkButton(card, text="Face Recognition Login", command=self._face_login,
                                 width=300, height=45, fg_color="transparent", border_width=1, border_color=ACCENT_BLUE)
        face_btn.pack(pady=5)

        # Register link
        reg_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        reg_frame.pack(pady=20)
        ctk.CTkLabel(reg_frame, text="Don't have an account?", font=FONT_MAIN, text_color=TEXT_MUTED).pack(side="left")
        reg_btn = ctk.CTkButton(reg_frame, text="Register", font=FONT_BOLD, text_color=ACCENT_BLUE, 
                                fg_color="transparent", width=50, command=self._show_register)
        reg_btn.pack(side="left")

    def _show_register(self):
        # Minimal implementation for now, mirroring the layout of login
        self._clear()
        reg_frame = ctk.CTkFrame(self.root, fg_color=BG_COLOR)
        reg_frame.pack(expand=True)
        ctk.CTkLabel(reg_frame, text="Create Account", font=FONT_LOGO, text_color=ACCENT_BLUE).pack(pady=20)
        # ... simplified for brevity, user can use old UI if needed or I can fill this later
        back_btn = ctk.CTkButton(reg_frame, text="Back to Login", command=self._show_login)
        back_btn.pack(pady=10)

    def _login(self):
        u, p = self.u_var.get(), self.p_var.get()
        ok, user = self.Vox.db.login(u, p)
        if ok:
            self.Vox.set_user(user)
            self._show_chat()
        else:
            self.login_status.configure(text="Invalid credentials")

    def _face_login(self):
        if not self.Vox.face.available:
            messagebox.showinfo("Face Login", "Face recognition not installed.")
            return
        def cb(ok, ud):
            if ok:
                self.Vox.set_user(ud)
                self.root.after(0, self._show_chat)
            else:
                self.root.after(0, lambda: self.login_status.configure(text="Face not recognized"))
        self.Vox.face.start_recognition_thread(cb)

    def _show_chat(self):
        self._clear()
        self.root.grid_columnconfigure(0, weight=0) # Sidebar
        self.root.grid_columnconfigure(1, weight=1) # Main Orb
        self.root.grid_columnconfigure(2, weight=0) # Conversation
        self.root.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        sidebar = ctk.CTkFrame(self.root, fg_color=SIDEBAR_COLOR, width=240, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(sidebar, text="VOX AI", font=FONT_LOGO, text_color=ACCENT_BLUE)
        logo.pack(pady=(30, 20))

        # Status Pill in Sidebar
        self.sidebar_status = ctk.CTkLabel(sidebar, text="  🟢  Voice Active  ", 
                                          fg_color="#061806", text_color=SUCCESS_GREEN,
                                          corner_radius=15, font=FONT_BOLD)
        self.sidebar_status.pack(fill="x", padx=20, pady=(0, 20))

        # Quick Actions (The "Phely Jasa" Part)
        ctk.CTkLabel(sidebar, text="QUICK ACTIONS", font=("Segoe UI", 9, "bold"), 
                    text_color=TEXT_MUTED, anchor="w").pack(fill="x", padx=20, pady=(10, 5))

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
            btn = ctk.CTkButton(sidebar, text=lbl, font=FONT_MAIN, 
                                anchor="w", fg_color="transparent", text_color=TEXT_MAIN, 
                                hover_color=CARD_COLOR, height=35,
                                command=lambda c=cmd: self._quick(c))
            btn.pack(fill="x", padx=10, pady=2)

        # Bottom User Card
        user = self.Vox.current_user or {'full_name': 'Guest', 'username': 'guest'}
        user_card = ctk.CTkFrame(sidebar, fg_color=CARD_COLOR, height=70, corner_radius=10)
        user_card.pack(side="bottom", fill="x", padx=15, pady=20)
        user_card.pack_propagate(False)
        
        ctk.CTkLabel(user_card, text=user['full_name'][0].upper(), font=FONT_BOLD, 
                    fg_color=ACCENT_BLUE, corner_radius=20, width=40, height=40).pack(side="left", padx=10)
        
        user_info = ctk.CTkFrame(user_card, fg_color="transparent")
        user_info.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(user_info, text=user['full_name'], font=FONT_BOLD, text_color=TEXT_MAIN, anchor="w").pack(fill="x")
        ctk.CTkLabel(user_info, text="Online", font=FONT_MAIN, text_color=SUCCESS_GREEN, anchor="w").pack(fill="x")

        # 2. MAIN CENTER AREA
        main_area = ctk.CTkFrame(self.root, fg_color=BG_COLOR, corner_radius=0)
        main_area.grid(row=0, column=1, sticky="nsew")
        
        # Center Orb
        self.orb = AnimatedOrb(main_area, size=450)
        self.orb.pack(expand=True)
        
        # Dynamic Status Label
        self.status_label = ctk.CTkLabel(main_area, text="Ready", font=("Segoe UI", 16, "bold"), text_color=ACCENT_BLUE)
        self.status_label.pack(pady=(10, 40))

        # Bottom Control Bar
        controls = ctk.CTkFrame(main_area, fg_color=SIDEBAR_COLOR, height=80, corner_radius=20)
        controls.pack(fill="x", padx=40, pady=(0, 30))
        controls.pack_propagate(False)
        
        ctk.CTkButton(controls, text="Voice Input ⌵", width=120, fg_color="transparent").pack(side="left", padx=20)
        self.stop_btn = ctk.CTkButton(controls, text="Stop Listening", fg_color=ACCENT_PURPLE, 
                                     hover_color="#8A2BE2", width=160, corner_radius=10)
        self.stop_btn.pack(side="left", expand=True)
        ctk.CTkButton(controls, text="English (US) ⌵", width=120, fg_color="transparent").pack(side="right", padx=20)

        # 3. CONVERSATION PANEL (Right side)
        conv_panel = ctk.CTkFrame(self.root, fg_color=SIDEBAR_COLOR, width=350, corner_radius=0)
        conv_panel.grid(row=0, column=2, sticky="nsew")
        conv_panel.grid_propagate(False)

        ctk.CTkLabel(conv_panel, text="Conversation", font=FONT_HEADING, text_color=TEXT_MAIN).pack(pady=20, padx=20, anchor="w")

        # Chat display area
        self.chat_frame = ctk.CTkScrollableFrame(conv_panel, fg_color="transparent", 
                                                scrollbar_button_color=CARD_COLOR)
        self.chat_frame.pack(fill="both", expand=True, padx=10)

        # Input Area
        input_area = ctk.CTkFrame(conv_panel, fg_color=CARD_COLOR, height=60, corner_radius=15)
        input_area.pack(fill="x", padx=15, pady=20)
        input_area.pack_propagate(False)

        self.msg_var = tk.StringVar()
        self.msg_entry = ctk.CTkEntry(input_area, textvariable=self.msg_var, placeholder_text="Type your message...", 
                                     fg_color="transparent", border_width=0, font=FONT_MAIN)
        self.msg_entry.pack(side="left", fill="both", expand=True, padx=10)
        self.msg_entry.bind("<Return>", lambda _: self._send_msg())

        send_btn = ctk.CTkButton(input_area, text="➔", width=40, height=40, 
                                corner_radius=10, fg_color=ACCENT_BLUE, command=self._send_msg)
        send_btn.pack(side="right", padx=10)

        self._add_Vox_msg("Hello! I am Vox. How can I assist you today?")

    def update_status(self, text):
        self.status_label.configure(text=text)

    def _quick(self, cmd):
        """Execute a quick action from the sidebar."""
        self._add_user_msg(cmd)
        threading.Thread(target=self._process_command, args=(cmd,), daemon=True).start()

    def _send_msg(self):
        text = self.msg_var.get().strip()
        if not text: return
        self.msg_var.set("")
        self._add_user_msg(text)
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    def _process_command(self, text):
        self.set_voice_status("Thinking...", WARNING_AMBER)
        res = self.Vox.process_command(text)
        self.root.after(0, lambda: self._add_Vox_msg(res))
        self.root.after(0, lambda: self.set_voice_status("Listening", SUCCESS_GREEN))

    def _add_user_msg(self, text):
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color=USER_BUBBLE, corner_radius=10)
        msg_frame.pack(fill="x", padx=10, pady=5, anchor="e")
        ctk.CTkLabel(msg_frame, text=text, font=FONT_MAIN, text_color=TEXT_MAIN, 
                    wraplength=250, justify="left").pack(padx=10, pady=8)
        self.root.after(100, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    def _add_Vox_msg(self, text):
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color=VOX_BUBBLE, corner_radius=10)
        msg_frame.pack(fill="x", padx=10, pady=5, anchor="w")
        ctk.CTkLabel(msg_frame, text=text, font=FONT_MAIN, text_color=TEXT_MAIN, 
                    wraplength=250, justify="left").pack(padx=10, pady=8)
        self.root.after(100, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    # Compatibility methods for Vox logic
    def set_voice_status(self, msg, color=SUCCESS_GREEN):
        lower_msg = msg.lower()
        self.root.after(0, lambda: self._update_pills(lower_msg))
        
        # Update status label
        # Map various status messages to the desired UI labels
        if any(keyword in lower_msg for keyword in ["listen", "say", "microphone"]): 
            self.update_status("Listening...")
        elif any(keyword in lower_msg for keyword in ["think", "process", "performing", "⚙"]): 
            self.update_status("Performing Task...")
        elif "speak" in lower_msg: 
            self.update_status("Speaking...")
        else: 
            self.update_status("Ready")
        
        # Update Orb state
        if "listen" in lower_msg: self.orb.set_state("listening")
        elif "think" in lower_msg or "process" in lower_msg: self.orb.set_state("thinking")
        elif "speak" in lower_msg: self.orb.set_state("speaking")
        else: self.orb.set_state("idle")

    def _update_pills(self, msg):
        pass

    def _on_close(self):
        self.Vox.shutdown()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def close(self):
        self.root.destroy()
