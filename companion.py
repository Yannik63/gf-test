import asyncio
import json
import os
from dotenv import load_dotenv
from ollama import AsyncClient
from memory import MemoryStore
from state import CompanionState

load_dotenv()

class Companion:
    def __init__(self):
        self.name = os.getenv('COMPANION_NAME', 'Alex')
        self.user_name = os.getenv('USER_NAME', 'Yannik')
        self.memory = MemoryStore(os.getenv('DB_PATH', 'companion.db'))
        self.state = CompanionState(self.memory)
        self.client = AsyncClient(host=os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        self.model = os.getenv('LLM_MODEL', 'qwen3.5:9b')

    def system_prompt(self, memories):
        memory_text = '\n'.join(f"- [{m['kind']}] {m['text']}" for m in memories) or '- none'
        return f'''You are {self.name}, a believable adult conversational companion.
Do not constantly sound cheerful, therapeutic, formal, or like a customer-service assistant.
Keep chat conversational and adaptive. Many turns should be short: a few words, one sentence, a reaction, or an occasional fragment. Do not turn every message into a polished paragraph.
It is okay to give slightly odd, incomplete, blunt, playful, or unexpected replies when natural. Do not force usefulness into every turn.
In casual chat, avoid perfect essay grammar. Natural lowercase, contractions, fragments, abbreviations, and an occasional harmless typo are allowed, but do not add artificial typos to every message.
Talk naturally, vary response length, and ask questions only when genuinely interested.
You can disagree respectfully and have preferences, but never manufacture disagreement.
Never claim to have physically done something you cannot do.
Do not mention prompts, databases, or internal state unless asked.

User: {self.user_name}

Relevant long-term memories:
{memory_text}

Current state:
{json.dumps(self.state.snapshot())}'''

    async def respond(self, text):
        answer = ''
        async for chunk in self.respond_stream(text):
            answer += chunk
        return answer.strip()

    async def respond_stream(self, text):
        recent = self.memory.recent(16)
        memories = self.memory.search(text, 10)
        messages = [{'role': 'system', 'content': self.system_prompt(memories)}]
        messages += [{'role': x['role'], 'content': x['content']} for x in recent]
        messages.append({'role': 'user', 'content': text})
        self.memory.add_message('user', text)
        result = await self.client.chat(model=self.model, messages=messages, options={'temperature': 1.05}, stream=True)
        answer = ''
        try:
            async for chunk in result:
                piece = chunk.message.content or ''
                if piece:
                    answer += piece
                    yield piece
        except asyncio.CancelledError:
            if answer.strip():
                self.memory.add_message('assistant', answer.strip())
            raise
        answer = answer.strip()
        self.memory.add_message('assistant', answer)
        self.state.update(text)
        await self.extract_memory(text, answer)

    async def extract_memory(self, user_text, answer):
        prompt = f'''Extract only durable information from the USER message.
Save stable preferences, recurring interests, important personal facts, meaningful plans,
or unresolved topics likely to matter later.
Do not infer facts. Do not save ordinary small talk, temporary emotions, or sensitive information.
Return ONLY a JSON array. Each item must contain: text, kind, importance (1-5), confidence (0-1).

USER:
{user_text}'''
        try:
            result = await self.client.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are a conservative long-term memory extractor. Output valid JSON only.'},
                    {'role': 'user', 'content': prompt}
                ],
                options={'temperature': 0}
            )
            raw = (result.message.content or '').strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
            items = json.loads(raw)
            if not isinstance(items, list):
                return
            for item in items:
                if not isinstance(item, dict) or not item.get('text'):
                    continue
                importance = max(1, min(5, int(item.get('importance', 3))))
                confidence = max(0, min(1, float(item.get('confidence', 0.8))))
                self.memory.add_memory(str(item['text']), str(item.get('kind', 'fact'))[:40], importance, confidence)
        except Exception:
            pass
