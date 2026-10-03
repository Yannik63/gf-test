class CompanionState:
    def __init__(self):
        self.values = {'mood': .60, 'energy': .65, 'curiosity': .75, 'playfulness': .60, 'closeness': .30}

    def update(self, text):
        t = text.lower()
        if any(x in t for x in ['haha', 'lol', '😂', 'joke']):
            self.values['playfulness'] = min(1, self.values['playfulness'] + .03)
        if 'thank' in t or 'appreciate' in t:
            self.values['closeness'] = min(1, self.values['closeness'] + .015)
        if len(text) > 700:
            self.values['energy'] = max(0, self.values['energy'] - .01)

    def snapshot(self):
        return {k: round(v, 3) for k, v in self.values.items()}
