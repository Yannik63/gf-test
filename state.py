import json

class CompanionState:
    def __init__(self, store=None):
        self.store = store
        self.values = {'mood': .60, 'energy': .65, 'curiosity': .75, 'playfulness': .60, 'closeness': .30, 'irritation': .05}
        self.interests = {}
        self.unfinished_threads = []
        self._load()

    def _load(self):
        if not self.store:
            return
        try:
            raw = self.store.get_state('companion_state')
            if raw:
                data = json.loads(raw)
                self.values.update(data.get('values', {}))
                self.interests = data.get('interests', {})
                self.unfinished_threads = data.get('unfinished_threads', [])
        except Exception:
            pass

    def _save(self):
        if self.store:
            self.store.set_state('companion_state', json.dumps({'values': self.values, 'interests': self.interests, 'unfinished_threads': self.unfinished_threads}, ensure_ascii=False))

    def update(self, text):
        t = text.lower()
        if any(x in t for x in ['haha', 'lol', '😂', 'joke']):
            self.values['playfulness'] = min(1, self.values['playfulness'] + .03)
        if any(x in t for x in ['thank', 'appreciate']):
            self.values['closeness'] = min(1, self.values['closeness'] + .015)
        if any(x in t for x in ['stupid', 'annoying', 'shut up']):
            self.values['irritation'] = min(1, self.values['irritation'] + .03)
        if len(text) > 700:
            self.values['energy'] = max(0, self.values['energy'] - .01)
        self._save()

    def add_interest(self, name, weight=1):
        key = str(name).strip().lower()
        if key:
            self.interests[key] = min(10, self.interests.get(key, 0) + weight)
            self._save()

    def add_thread(self, text):
        text = str(text).strip()
        if text and text not in self.unfinished_threads:
            self.unfinished_threads.append(text)
            self.unfinished_threads = self.unfinished_threads[-20:]
            self._save()

    def snapshot(self):
        return {'values': {k: round(v, 3) for k, v in self.values.items()}, 'interests': self.interests, 'unfinished_threads': self.unfinished_threads[-10:]}
