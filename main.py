import asyncio
from companion import Companion
from scheduler import ProactiveScheduler

async def main():
    companion = Companion()
    scheduler = ProactiveScheduler(companion, interval_seconds=60)
    async def emit(message):
        print(f'\n{companion.name}: {message}\nYou: ', end='', flush=True)
    scheduler_task = asyncio.create_task(scheduler.run(lambda message: asyncio.create_task(emit(message))))
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
            scheduler.stop()
            scheduler_task.cancel()
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
