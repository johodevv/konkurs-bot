import asyncio
from pyrogram import Client

async def main():
    api_id = 28466899
    api_hash = "2f1948ccca564e8973e8cf9c3204d2e9"
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        print("\nMANA BU SENING SESSIYA KODING (NUSXALAB OL):\n")
        print(await app.export_session_string())
        print("\n-------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
