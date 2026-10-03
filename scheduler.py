from datetime import datetime, timezone
import asyncio

class ProactiveScheduler:
    def __init__(self, companion, interval_seconds=60):
        self.companion = companion
        self.interval_seconds = interval_seconds
        self.running = False

    async def run(self, emit):
        self.running = True
        while self.running:
            await asyncio.sleep(self.interval_seconds)
            if not self.running:
                break
            message = await self.maybe_initiate()
            if message:
                emit(message)

    def stop(self):
        self.running = False

    async def maybe_initiate(self):
        state = self.companion.state.snapshot()
        threads = state.get('unfinished_threads', [])
        interests = state.get('interests', {})
        if not threads and not interests:
            return None
        prompt = 'Decide whether to initiate a short natural conversation right now. Only do so if there is a genuinely useful or interesting reason based on the saved context. Return JSON with initiate (true/false) and message. Never invent events or claims about the user.'
        context = {'threads': threads[-5:], 'interests': interests}
        try:
            result = await self.companion.client.chat.completions.create(
                model=self.companion.model,
                messages=[
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': str(context)}
                ],
                temperature=.8
            )
            import json
            raw = (result.choices[0].message.content or '').strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
            data = json.loads(raw)
            if data.get('initiate') and data.get('message'):
                message = str(data['message']).strip()
                self.companion.memory.add_message('assistant', message)
                return message
        except Exception:
            return None
        return None
