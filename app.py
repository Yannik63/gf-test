import asyncio
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from companion import Companion
from scheduler import ProactiveScheduler

class CompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Companion')
        self.root.geometry('700x600')
        self.companion = Companion()
        self.events = queue.Queue()
        self.generation_id = 0
        self.worker = None
        self.stop_event = None
        self.response_start = None
        self.generating = False

        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
        self.chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, padx=10, pady=10)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind('<Return>', lambda event: self.send())
        tk.Button(bottom, text='Send', command=self.send).pack(side=tk.RIGHT, padx=(8, 0))
        self.status = tk.Label(root, text='Ready', anchor='w')
        self.status.pack(fill=tk.X, padx=10)

        self.scheduler = ProactiveScheduler(self.companion, interval_seconds=60)
        self.loop = asyncio.new_event_loop()
        self.root.after(30, self.process_events)
        self.loop.create_task(self.proactive_loop())
        self.write('System', f'{self.companion.name} is here.')
        self.entry.focus_set()

    def write(self, speaker, message):
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{speaker}: {message}\n\n')
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def begin_response(self, generation_id):
        if generation_id != self.generation_id: return
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{self.companion.name}: ')
        self.response_start = self.chat.index('end-1c')
        self.chat.insert(tk.END, '\n\n')
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def replace_response(self, generation_id, value):
        if generation_id != self.generation_id or not self.response_start: return
        self.chat.configure(state='normal')
        end = self.chat.index('end-1c')
        self.chat.delete(self.response_start, end)
        self.chat.insert(self.response_start, value + '\n\n')
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def send(self):
        text = self.entry.get().strip()
        if not text: return
        self.entry.delete(0, tk.END)
        if self.generating and self.stop_event:
            self.stop_event.set()
        self.generation_id += 1
        generation_id = self.generation_id
        self.write('You', text)
        self.generating = True
        self.status.configure(text='Typing...')
        self.response_start = None
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.generate, args=(generation_id, text, self.stop_event), daemon=True)
        self.worker.start()

    def generate(self, generation_id, text, stop_event):
        try:
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
                    current = self.chat.get(self.response_start, 'end-1c') if self.response_start else ''
                    self.replace_response(generation_id, current + value)
                elif kind == 'error':
                    self.write('Error', value)
                    self.generating = False
                    self.status.configure(text='Ready')
                elif kind == 'done':
                    self.generating = False
                    self.status.configure(text='Ready')
        except queue.Empty:
            pass
        self.root.after(30, self.process_events)

    async def proactive_loop(self):
        async def emit(message):
            self.root.after(0, lambda value=message: self.write(self.companion.name, value))
        await self.scheduler.run(lambda message: self.loop.create_task(emit(message)))

    def process_asyncio(self):
        try:
            self.loop.run_until_complete(asyncio.sleep(0))
        finally:
            self.root.after(50, self.process_asyncio)

    def close(self):
        self.scheduler.stop()
        if self.stop_event: self.stop_event.set()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = CompanionApp(root)
    root.protocol('WM_DELETE_WINDOW', app.close)
    root.mainloop()
