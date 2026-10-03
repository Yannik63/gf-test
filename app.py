import asyncio
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from companion import Companion
from scheduler import ProactiveScheduler


class CompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Companion')
        self.root.geometry('760x680')
        self.root.minsize(560, 480)

        self.companion = Companion()
        self.events = queue.Queue()
        self.generation_id = 0
        self.worker = None
        self.stop_event = None
        self.response_mark = None
        self.generating = False

        self.mode = self.companion.memory.get_state('interface_mode', 'modern')
        self.font_size = int(self.companion.memory.get_state('interface_font_size', '11'))

        self._build_ui()
        self.apply_theme()
        self.write('System', f'{self.companion.name} is here.')

        self.entry.focus_set()
        self.root.after(30, self.process_events)
        self.root.after(1000, self.start_scheduler)

    # ---------- UI ----------

    def _build_ui(self):
        self.header = tk.Frame(self.root)
        self.header.pack(fill=tk.X, padx=14, pady=(12, 6))

        self.title_label = tk.Label(
            self.header,
            text=self.companion.name,
            font=('Segoe UI', 16, 'bold'),
            anchor='w'
        )
        self.title_label.pack(side=tk.LEFT)

        self.settings_button = tk.Button(
            self.header,
            text='⚙  Settings',
            command=self.open_settings,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.settings_button.pack(side=tk.RIGHT)

        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        self.chat = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            state='disabled',
            undo=False,
            padx=14,
            pady=12,
            borderwidth=0,
            highlightthickness=0
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill=tk.X, padx=14, pady=(0, 5))

        self.entry = tk.Entry(
            self.input_frame,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9)
        self.entry.bind('<Return>', lambda event: self.send())

        self.send_button = ttk.Button(
            self.input_frame,
            text='Send',
            command=self.send
        )
        self.send_button.pack(side=tk.RIGHT, padx=(8, 0), ipady=2)

        self.status = tk.Label(
            self.root,
            text='Ready',
            anchor='w',
            padx=14
        )
        self.status.pack(fill=tk.X, pady=(0, 9))

    def apply_theme(self):
        if self.mode == 'classic':
            self._apply_classic()
        else:
            self._apply_modern()

    def _apply_classic(self):
        bg = self.root.cget('bg')
        self.root.configure(bg=bg)

        for widget in (self.header, self.chat_frame, self.input_frame):
            widget.configure(bg=bg)

        self.title_label.configure(
            bg=bg,
            fg='black',
            font=('TkDefaultFont', 12, 'bold')
        )
        self.settings_button.configure(
            bg=bg,
            fg='black',
            activebackground=bg,
            activeforeground='black',
            font=('TkDefaultFont', 9)
        )
        self.chat.configure(
            bg='white',
            fg='black',
            insertbackground='black',
            font=('TkDefaultFont', self.font_size),
            selectbackground='#cce8ff'
        )
        self.entry.configure(
            bg='white',
            fg='black',
            insertbackground='black',
            font=('TkDefaultFont', self.font_size),
            highlightbackground='#aaaaaa',
            highlightcolor='#555555'
        )
        self.send_button.configure(style='Classic.TButton')
        self.status.configure(
            bg=bg,
            fg='#555555',
            font=('TkDefaultFont', 9)
        )

        self._configure_tags(
            user='#333333',
            mia='#333333',
            system='#777777',
            error='#aa3333'
        )

    def _apply_modern(self):
        # A restrained dark theme: cleaner without turning the app into a
        # generic neon "AI dashboard".
        bg = '#17191d'
        panel = '#202329'
        text = '#e7e9ed'
        muted = '#9298a3'
        accent = '#8ab4f8'
        border = '#343941'

        self.root.configure(bg=bg)

        for widget in (self.header, self.chat_frame, self.input_frame):
            widget.configure(bg=bg)

        self.title_label.configure(
            bg=bg,
            fg=text,
            font=('Segoe UI', 16, 'bold')
        )
        self.settings_button.configure(
            bg=bg,
            fg=muted,
            activebackground=bg,
            activeforeground=text,
            font=('Segoe UI', 9)
        )
        self.chat.configure(
            bg=panel,
            fg=text,
            insertbackground=text,
            font=('Segoe UI', self.font_size),
            selectbackground='#3b4c68'
        )
        self.entry.configure(
            bg=panel,
            fg=text,
            insertbackground=text,
            font=('Segoe UI', self.font_size),
            highlightbackground=border,
            highlightcolor=accent
        )
        self.send_button.configure(style='Modern.TButton')
        self.status.configure(
            bg=bg,
            fg=muted,
            font=('Segoe UI', 9)
        )

        self._configure_tags(
            user='#b9d6ff',
            mia='#f0f1f4',
            system='#7f8793',
            error='#ff8f8f'
        )

    def _configure_tags(self, user, mia, system, error):
        self.chat.tag_configure(
            'user',
            foreground=user,
            font=(self.chat.cget('font').split()[0], self.font_size, 'bold')
        )
        self.chat.tag_configure(
            'mia',
            foreground=mia,
            font=(self.chat.cget('font').split()[0], self.font_size)
        )
        self.chat.tag_configure(
            'system',
            foreground=system,
            font=(self.chat.cget('font').split()[0], max(9, self.font_size - 1))
        )
        self.chat.tag_configure(
            'error',
            foreground=error,
            font=(self.chat.cget('font').split()[0], self.font_size)
        )

    def write(self, speaker, message):
        self.chat.configure(state='normal')
        tag = (
            'user' if speaker == 'You'
            else 'mia' if speaker == self.companion.name
            else 'error' if speaker == 'Error'
            else 'system'
        )
        self.chat.insert(tk.END, f'{speaker}: ', tag)
        self.chat.insert(tk.END, f'{message}\n\n', tag)
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def begin_response(self, generation_id):
        if generation_id != self.generation_id:
            return
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{self.companion.name}: ', 'mia')
        self.response_mark = self.chat.index('end-1c')
        self.chat.mark_set('response', self.response_mark)
        self.chat.mark_gravity('response', tk.RIGHT)
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def append_response(self, generation_id, value):
        if generation_id != self.generation_id or not self.response_mark:
            return

        # The UI already writes "Mia:". Qwen occasionally repeats the speaker
        # label itself, so remove only a leading standalone label.
        if self.response_mark == self.chat.index('end-1c'):
            cleaned = value.lstrip()
            if cleaned.lower().startswith('mia:'):
                value = cleaned[4:].lstrip()
            elif cleaned.lower().startswith(self.companion.name.lower() + ':'):
                value = cleaned[len(self.companion.name) + 1:].lstrip()

        if value:
            self.chat.configure(state='normal')
            self.chat.insert('response', value, 'mia')
            self.chat.configure(state='disabled')
            self.chat.see(tk.END)

    def finish_response(self, generation_id):
        if generation_id != self.generation_id:
            return
        self.chat.configure(state='normal')
        self.chat.insert('response', '\n\n', 'mia')
        self.chat.configure(state='disabled')
        self.response_mark = None
        self.generating = False
        self.status.configure(text='Ready')
        self.chat.see(tk.END)

    # ---------- Settings ----------

    def open_settings(self):
        window = tk.Toplevel(self.root)
        window.title('Companion settings')
        window.geometry('340x270')
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        bg = '#17191d' if self.mode == 'modern' else self.root.cget('bg')
        fg = '#e7e9ed' if self.mode == 'modern' else 'black'
        muted = '#9298a3' if self.mode == 'modern' else '#555555'
        panel = '#202329' if self.mode == 'modern' else 'white'

        window.configure(bg=bg)

        tk.Label(
            window,
            text='Appearance',
            bg=bg,
            fg=fg,
            font=('Segoe UI' if self.mode == 'modern' else 'TkDefaultFont', 13, 'bold')
        ).pack(anchor='w', padx=22, pady=(20, 14))

        mode_var = tk.StringVar(value=self.mode)
        font_var = tk.IntVar(value=self.font_size)

        mode_frame = tk.Frame(window, bg=bg)
        mode_frame.pack(fill=tk.X, padx=22)

        tk.Label(
            mode_frame,
            text='Interface',
            bg=bg,
            fg=muted,
            font=('Segoe UI' if self.mode == 'modern' else 'TkDefaultFont', 9)
        ).pack(anchor='w')

        for value, label in (
            ('modern', 'Modern'),
            ('classic', 'Classic'),
        ):
            tk.Radiobutton(
                mode_frame,
                text=label,
                value=value,
                variable=mode_var,
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                selectcolor=panel,
                highlightthickness=0
            ).pack(side=tk.LEFT, padx=(0, 16), pady=(6, 12))

        tk.Label(
            window,
            text='Chat font size',
            bg=bg,
            fg=muted,
            font=('Segoe UI' if self.mode == 'modern' else 'TkDefaultFont', 9)
        ).pack(anchor='w', padx=22)

        font_menu = tk.OptionMenu(
            window,
            font_var,
            9, 10, 11, 12, 13, 14
        )
        font_menu.configure(
            bg=panel,
            fg=fg,
            activebackground=panel,
            activeforeground=fg,
            highlightthickness=0,
            relief=tk.GROOVE,
            bd=1,
            font=('Segoe UI' if self.mode == 'modern' else 'TkDefaultFont', 9)
        )
        font_menu['menu'].configure(
            bg=panel,
            fg=fg,
            activebackground='#3b4c68' if self.mode == 'modern' else '#cce8ff',
            activeforeground=fg
        )
        font_menu.pack(anchor='w', padx=22, pady=(5, 18))

        def save():
            self.mode = mode_var.get()
            self.font_size = int(font_var.get())
            self.companion.memory.set_state('interface_mode', self.mode)
            self.companion.memory.set_state('interface_font_size', self.font_size)
            self.apply_theme()
            window.destroy()

        button_font = ('Segoe UI', 9) if self.mode == 'modern' else ('TkDefaultFont', 9)
        button_bg = '#2a2e35' if self.mode == 'modern' else '#e6e6e6'
        button_active = '#363b44' if self.mode == 'modern' else '#d4d4d4'

        tk.Button(
            window,
            text='Apply',
            command=save,
            bg=button_bg,
            fg=fg,
            activebackground=button_active,
            activeforeground=fg,
            relief=tk.GROOVE,
            bd=1,
            padx=12,
            pady=4,
            font=button_font
        ).pack(side=tk.RIGHT, padx=(0, 22), pady=(0, 18))

        tk.Button(
            window,
            text='Cancel',
            command=window.destroy,
            bg=button_bg,
            fg=fg,
            activebackground=button_active,
            activeforeground=fg,
            relief=tk.GROOVE,
            bd=1,
            padx=12,
            pady=4,
            font=button_font
        ).pack(side=tk.RIGHT, padx=8, pady=(0, 18))

    # ---------- Conversation ----------

    def start_scheduler(self):
        threading.Thread(target=self.scheduler_thread, daemon=True).start()

    def scheduler_thread(self):
        asyncio.run(self.proactive_loop())

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        if self.generating and self.stop_event:
            self.stop_event.set()
        self.generation_id += 1
        generation_id = self.generation_id
        self.write('You', text)
        self.generating = True
        self.status.configure(text='Typing...')
        self.response_mark = None
        self.stop_event = threading.Event()
        self.worker = threading.Thread(
            target=self.generate,
            args=(generation_id, text, self.stop_event),
            daemon=True
        )
        self.worker.start()

    def generate(self, generation_id, text, stop_event):
        try:
            import random

            word_count = len(text.split())
            if word_count <= 4:
                delay = random.uniform(0.6, 1.1)
            elif word_count <= 12:
                delay = random.uniform(1.0, 1.7)
            elif word_count <= 25:
                delay = random.uniform(1.6, 2.5)
            else:
                delay = random.uniform(2.4, 4.0)

            if stop_event.wait(delay):
                self.events.put(('done', generation_id, None))
                return

            self.events.put(('begin', generation_id, None))
            for piece in self.companion.respond_stream_sync(text, stop_event):
                self.events.put(('piece', generation_id, piece))
            self.events.put(('done', generation_id, None))
        except Exception as exc:
            self.events.put(('error', generation_id, str(exc)))

    def process_events(self):
        try:
            while True:
                kind, generation_id, value = self.events.get_nowait()
                if generation_id != self.generation_id:
                    continue
                if kind == 'begin':
                    self.begin_response(generation_id)
                elif kind == 'piece':
                    self.append_response(generation_id, value)
                elif kind == 'error':
                    self.write('Error', value)
                    self.generating = False
                    self.status.configure(text='Ready')
                elif kind == 'done':
                    self.finish_response(generation_id)
        except queue.Empty:
            pass
        self.root.after(30, self.process_events)

    async def proactive_loop(self):
        async def emit(message):
            self.root.after(
                0,
                lambda value=message: self.write(self.companion.name, value)
            )
        await self.scheduler.run(
            lambda message: asyncio.create_task(emit(message))
        )

    def close(self):
        self.scheduler.stop()
        if self.stop_event:
            self.stop_event.set()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = CompanionApp(root)
    root.protocol('WM_DELETE_WINDOW', app.close)
    root.mainloop()
