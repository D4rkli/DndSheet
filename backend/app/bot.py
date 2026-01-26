import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, WebAppInfo, ReplyKeyboardMarkup
from .config import settings

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🧙 Открыть лист персонажа",
                    web_app=WebAppInfo(
                        url="https://dnd-bot-backend.onrender.com/webapp/?v=113"
                    )
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer("Открываем WebApp 👇", reply_markup=kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
