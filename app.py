import asyncio
import tkinter as tk
import random
from tkinter import scrolledtext
from companion import Companion
from scheduler import ProactiveScheduler

class CompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Companion')
        self.root.geometry('700x600')
        self.companion = Companion()

        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
        self.chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, padx=10, pady=10)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind('<Return>', lambda event: self.send())
        self.status = tk.Label(root, text='Ready', anchor='w')
        self.status.pack(fill=tk.X, padx=10)
        tk.Button(bottom, text='Send', command=self.send).pack(side=tk.RIGHT, padx=(8, 0))

        self.scheduler = ProactiveScheduler(self.companion, interval_seconds=60)
        self.loop = asyncio.new_event_loop()
        self.root.after(50, self.process_asyncio)
        self.loop.create_task(self.proactive_loop())

        self.write('System', f'{self.companion.name} is here.')
        self.entry.focus_set()

    def write(self, speaker, message):
        self.chat.configure(state='normal')
        self.chat.insert(tk.END, f'{speaker}: {message}\n\n')
        self.chat.configure(state='disabled')
        self.chat.see(tk.END)

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.write('You', text)
        self.entry.configure(state='disabled')
        self.status.configure(text='Thinking...')
        self.loop.create_task(self.respond(text))

    async def respond(self, text):
        try:
            await asyncio.sleep(random.uniform(0.25, 0.9))
            answer = await self.companion.respond(text)
            delay = min(2.5, max(0.15, len(answer) / 70))
            await asyncio.sleep(delay)
            self.root.after(0, lambda: self.finish_response(answer))
        except Exception as exc:
            self.root.after(0, lambda: self.finish_response('Error: ' + str(exc), error=True))

    def finish_response(self, answer, error=False):
        self.write(self.companion.name if not error else 'Error', answer)
        self.entry.configure(state='normal')
        self.status.configure(text='Ready')
        self.entry.focus_set()

    async def proactive_loop(self):
        async def emit(message):
            self.root.after(0, lambda: self.write(self.companion.name, message))
        await self.scheduler.run(lambda message: self.loop.create_task(emit(message)))

    def process_asyncio(self):
        try:
            self.loop.run_until_complete(asyncio.sleep(0))
        finally:
            self.root.after(50, self.process_asyncio)

    def close(self):
        self.scheduler.stop()
        self.loop.stop()
        self.loop.close()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = CompanionApp(root)
    root.protocol('WM_DELETE_WINDOW', app.close)
    root.mainloop()
