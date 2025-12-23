# main.py
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from pizza_bot import router as pizza_router
from search import extract_keyphrase, search_wikipedia, nlp
from image import get_photo_tags

load_dotenv()
API_TOKEN = os.getenv('BOT_API_KEY')

logging.basicConfig(level=logging.INFO)
main_router = Router()

# === Хендлеры ===

@main_router.message(Command("start"))
async def universal_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🤖 Hi! I'm your smart assistant.\n\n"
        "Use:\n"
        "— /pizza to order pizza 🍕\n"
        "— Any question for Wikipedia answers 🧠\n"
        "— Send a photo for AI description 🖼️\n\n"
        "Just start!"
    )

@main_router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    # Если пользователь в универсальном режиме, но пишет про пиццу — дадим подсказку
    if "pizza" in message.text.lower():
        await message.answer("Would you like to order pizza? Use the command /pizza 🍕")
        return

    # Проверка состояния: если в заказе — игнорируем (pizza_router обработает)
    current_state = await state.get_state()
    if current_state and "PizzaOrder" in current_state:
        return

    # Универсальный режим
    try:
        doc = nlp(message.text)
        phrase = extract_keyphrase(doc).strip()
        answer = search_wikipedia(phrase) if phrase else "I didn't get that."
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Text error: {e}")
        await message.answer("I couldn't understand. Try rephrasing.")

@main_router.message(F.photo)
async def handle_photo(message: Message, bot: Bot, state: FSMContext):
    current_state = await state.get_state()
    if current_state and "PizzaOrder" in current_state:
        await message.answer("Please finish your pizza order first (send quantity).")
        return

    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        os.makedirs("temp", exist_ok=True)
        path = f"temp/{photo.file_id}.jpg"
        await bot.download_file(file.file_path, path)
        tag = get_photo_tags(path)
        desc = search_wikipedia(tag)
        await message.answer(f"🖼️ This looks like: *{tag}*\n\n{desc}", parse_mode="Markdown")
        os.remove(path)
    except Exception as e:
        logging.error(f"Photo error: {e}")
        await message.answer("Sorry, I couldn't analyze this image.")

# === Запуск ===
async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(pizza_router)  # pizza FSM
    dp.include_router(main_router)   # universal fallback
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())