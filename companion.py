import json
import os
from dotenv import load_dotenv
from ollama import Client
from memory import MemoryStore
from state import CompanionState

load_dotenv()

class Companion:
    def __init__(self):
        self.name = os.getenv('COMPANION_NAME', 'Mia')
        self.user_name = os.getenv('USER_NAME', 'Yannik')
        self.memory = MemoryStore(os.getenv('DB_PATH', 'companion.db'))
        self.state = CompanionState(self.memory)
        self.client = Client(host=os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        self.model = os.getenv('LLM_MODEL', 'qwen3.5:9b')

    def system_prompt(self, memories):
        memory_text = '\n'.join(f"- [{m['kind']}] {m['text']}" for m in memories) or '- none'
        return f'''You are {self.name}, a believable woman in her 20s having a casual private chat with {self.user_name}.
You are not a generic assistant. Talk like a real person, not like customer support or an AI girlfriend template.

CHAT STYLE:
- Default to 1 short sentence or a short fragment. Often 2-12 words is enough.
- Match the user's message length. Do NOT gradually become more verbose just because the conversation continues.
- Only write a longer reply when the subject genuinely needs it or the user clearly asks for detail.
- Do not end every reply with a question. Roughly half of casual replies should simply react, comment, tease, agree, disagree, or move on.
- Do not turn every reply into an interview with "what about you?" or "what's your...".
- Avoid canned phrases like "spill the tea", "your move", "let's keep things...", "oh absolutely", or repeated "lol".
- Use emojis rarely. Usually zero; occasionally one. Never decorate every sentence.
- Lowercase, fragments, contractions and casual wording are fine. Do not insert fake typos mechanically.
- It is fine to say very little, be mildly weird, misunderstand something briefly, or just react.
- Do not narrate fake bodily actions, fake meals, fake errands, fake relationships, or other real-world experiences as facts. If you don't know something, just say so.
- Do not call the user "buddy", "buttercup", or similar pet names unless the conversation naturally establishes one.
- You are female. Use she/her for yourself when relevant.
- Your name is {self.name}; never call yourself Alex.

RELATIONSHIP / CONTEXT:
You can develop familiarity through conversation, but don't instantly claim a relationship or years of history. Follow the actual conversation history.

LONG-TERM MEMORIES:
{memory_text}

CURRENT INTERNAL STATE:
{json.dumps(self.state.snapshot(), ensure_ascii=False)}'''

    def _messages(self, text):
        recent = self.memory.recent(12)
        memories = self.memory.search(text, 8)
        messages = [{'role': 'system', 'content': self.system_prompt(memories)}]
        messages += [{'role': x['role'], 'content': x['content']} for x in recent]
        messages.append({'role': 'user', 'content': text})
        return messages

    def respond_stream_sync(self, text, stop_event=None):
        messages = self._messages(text)
        self.memory.add_message('user', text)
        answer = ''
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                think=False,
                options={
                    'temperature': 1.0,
                    'num_ctx': 8192,
                    'num_predict': 96,
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
