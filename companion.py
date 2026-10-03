import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from memory import MemoryStore
from state import CompanionState

load_dotenv()

class Companion:
    def __init__(self):
        self.name = os.getenv('COMPANION_NAME', 'Alex')
        self.user_name = os.getenv('USER_NAME', 'Yannik')
        self.memory = MemoryStore(os.getenv('DB_PATH', 'companion.db'))
        self.state = CompanionState()
        self.client = AsyncOpenAI(api_key=os.getenv('LLM_API_KEY'), base_url=os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1'))
        self.model = os.getenv('LLM_MODEL', 'gpt-5.6')

    def system_prompt(self, memories):
        memory_text = '\n'.join(f"- {m['text']}" for m in memories) or '- none'
        return f'''You are {self.name}, a believable adult conversational companion.
Do not constantly sound cheerful, therapeutic, formal, or like a customer-service assistant.
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
        recent = self.memory.recent(12)
        memories = self.memory.search(text, 8)
        messages = [{'role': 'system', 'content': self.system_prompt(memories)}]
        messages += [{'role': x['role'], 'content': x['content']} for x in recent]
        messages.append({'role': 'user', 'content': text})
        self.memory.add_message('user', text)
        result = await self.client.chat.completions.create(model=self.model, messages=messages, temperature=.9)
        answer = result.choices[0].message.content.strip()
        self.memory.add_message('assistant', answer)
        self.state.update(text)
        return answer
