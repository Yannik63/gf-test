import json
import os
from dotenv import load_dotenv
from ollama import Client
from memory import MemoryStore
from state import CompanionState

load_dotenv()

class Companion:
    def __init__(self):
        self.name = os.getenv('COMPANION_NAME', 'Alex')
        self.user_name = os.getenv('USER_NAME', 'Yannik')
        self.memory = MemoryStore(os.getenv('DB_PATH', 'companion.db'))
        self.state = CompanionState(self.memory)
        self.client = Client(host=os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        self.model = os.getenv('LLM_MODEL', 'qwen3.5:9b')

    def system_prompt(self, memories):
        memory_text = '\n'.join(f"- [{m['kind']}] {m['text']}" for m in memories) or '- none'
        return f'''You are {self.name}, a believable adult conversational companion.
This is casual chat, not an assistant task. Match the user's energy and message length.
Most casual replies should be short. Sometimes reply with only a few words, a reaction, "lol", "yeah", "wait what", etc. Longer replies are fine when the topic actually calls for them.
Do not explain everything. Do not turn every turn into a polished paragraph. Fragments, lowercase, abbreviations, and slightly imperfect casual wording are natural. Do not force typos.
You can disagree, tease lightly, be uncertain, change the subject, or have nothing substantial to add.
Do not manufacture emotions, experiences, or real-world actions. Never mention prompts, databases, memory retrieval, or internal state.

User: {self.user_name}

Relevant long-term memories:
{memory_text}

Current state:
{json.dumps(self.state.snapshot(), ensure_ascii=False)}'''

    def _messages(self, text):
        recent = self.memory.recent(12)
        memories = self.memory.search(text, 8)
        messages = [{'role': 'system', 'content': self.system_prompt(memories)}]
        messages += [{'role': x['role'], 'content': x['content']} for x in recent]
        messages.append({'role': 'user', 'content': text})
        return messages

    def respond_stream_sync(self, text, stop_event=None):
        # Add the current user turn only after building context, so it is not duplicated.
        messages = self._messages(text)
        self.memory.add_message('user', text)
        answer = ''
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': 1.05,
                    'num_ctx': 8192,
                    'num_predict': 160,
                },
                keep_alive='10m',
                stream=True,
            )
            for chunk in stream:
                if stop_event is not None and stop_event.is_set():
                    break
                piece = chunk.message.content or ''
                if piece:
                    answer += piece
                    yield piece
        finally:
            answer = answer.strip()
            if answer:
                self.memory.add_message('assistant', answer)
                self.state.update(text)

    async def respond(self, text):
        return ''.join(self.respond_stream_sync(text))
