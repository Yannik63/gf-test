import asyncio
from companion import Companion

async def main():
    companion = Companion()
    print(f'{companion.name}: I\'m here. Type /help for commands.')
    while True:
        try:
            user = input('\nYou: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye.')
            break
        if not user:
            continue
        if user == '/quit':
            break
        if user == '/help':
            print('/memory - show saved memories')
            print('/state - show current state')
            print('/quit - exit')
            continue
        if user == '/memory':
            for m in companion.memory.all(20):
                print(f"- [{m['importance']}] {m['text']}")
            continue
        if user == '/state':
            print(companion.state.snapshot())
            continue
        try:
            print(f'\n{companion.name}: {await companion.respond(user)}')
        except Exception as exc:
            print(f'\n[error] {exc}')

if __name__ == '__main__':
    asyncio.run(main())
