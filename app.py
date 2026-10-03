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
        self.response_mark = None
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
        self.write('System', f'{self.companion.name} is here.')
        self.entry.focus_set()
        self.root.after(30, self.process_events)
        self.root.after(1000, self.start_scheduler)

    def start_scheduler(self):
        # Proactive behavior is deliberately kept separate from response generation.
        threading.Thread(target=self.scheduler_thread, daemon=True).start()

    def scheduler_thread(self):
        asyncio.run(self.proactive_loop())

    def write(self, speaker, message):
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{speaker}: {message}\n\n')
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def begin_response(self, generation_id):
        if generation_id != self.generation_id:
            return
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{self.companion.name}: ')
        self.response_mark = self.chat.index('end-1c')
        self.chat.mark_set('response', self.response_mark)
        self.chat.mark_gravity('response', tk.RIGHT)
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def append_response(self, generation_id, value):
        if generation_id != self.generation_id or not self.response_mark:
            return
        self.chat.configure(state='normal')
        self.chat.insert('response', value)
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def finish_response(self, generation_id):
        if generation_id != self.generation_id:
            return
        self.chat.configure(state='normal')
        self.chat.insert('response', '\n\n')
        self.chat.configure(state='disabled')
        self.response_mark = None
        self.generating = False
        self.status.configure(text='Ready')
        self.chat.see(tk.END)

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
        self.worker = threading.Thread(target=self.generate, args=(generation_id, text, self.stop_event), daemon=True)
        self.worker.start()

    def generate(self, generation_id, text, stop_event):
        try:
            # Give longer replies a little more "thinking/typing" time.
            # Keep the delay randomized so it does not feel like a fixed timer.
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
            self.root.after(0, lambda value=message: self.write(self.companion.name, value))
        await self.scheduler.run(lambda message: asyncio.create_task(emit(message)))

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
