import asyncio


from sqlalchemy.orm import scoped_session, sessionmaker
from settings import DATABASE_SETTINGS
from sqlalchemy import create_engine
from core.apps import Bot


async def main():
    engine = create_engine(**DATABASE_SETTINGS)

    session_factory = sessionmaker(engine)
    Session = scoped_session(session_factory)

    bot = Bot(Session, 'BTCUSDT')

    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
