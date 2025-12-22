# pizza.py
import asyncio
import logging
import json
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import spacy
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')

nlp = spacy.load("en_core_web_sm")
logging.basicConfig(level=logging.INFO)
router = Router()

# === FSM: только для заказа пиццы ===
class PizzaOrder(StatesGroup):
    waiting_for_type = State()
    waiting_for_quantity = State()

MENU = [
    {"name": "Pepperoni"},
    {"name": "Margherita"},
    {"name": "Vegetarian"},
    {"name": "Hawaiian"},
    {"name": "Meat Lovers"},
    {"name": "BBQ Chicken"},
    {"name": "Supreme"},
    {"name": "Four Cheese"}
]

def extract_pizza_type(text: str) -> str:
    doc = nlp(text.lower())
    for token in doc:
        if token.lemma_ == "pizza":
            modifiers = []
            for left in token.lefts:
                if left.dep_ in ("amod", "compound"):
                    modifiers.append(left.text)
            if modifiers:
                return " ".join(modifiers + ["pizza"]).title()
            else:
                return "Custom Pizza"
    return text.strip().title()

def extract_quantity(text: str) -> int:
    """Извлекает число из текста (поддержка слов и цифр)"""
    text = text.lower().strip()
    # Простой парсинг: поддержка цифр и базовых слов
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    if text.isdigit():
        return max(1, min(10, int(text)))  # ограничим от 1 до 10
    if text in word_to_num:
        return word_to_num[text]
    # По умолчанию — 1
    return 1

def save_order_to_db(orderdict: dict):
    required_keys = {'qty', 'product', 'ptype'}
    if not required_keys.issubset(orderdict):
        raise ValueError("Missing required keys")

    cnx = mysql.connector.connect(
        user='root',
        password=DB_PASSWORD,
        host='127.0.0.1',
        database='mybot'
    )
    query = """
        INSERT INTO orders (product, ptype, qty)
        SELECT product, ptype, qty FROM
        JSON_TABLE(%s, "$" COLUMNS(
            qty INT PATH '$.qty',
            product VARCHAR(30) PATH "$.product",
            ptype VARCHAR(30) PATH "$.ptype"
        )) AS jt1
    """
    cursor = cnx.cursor()
    cursor.execute(query, (json.dumps(orderdict),))
    cnx.commit()
    cursor.close()
    cnx.close()

# === ЕДИНСТВЕННАЯ команда для входа в заказ ===
@router.message(Command("pizza"))
async def start_pizza_order(message: Message, state: FSMContext):
    await state.set_state(PizzaOrder.waiting_for_type)
    # Show the menu options to the user
    menu_list = "\n".join([f"- {pizza['name']}" for pizza in MENU])
    await message.answer(
        "🍕 Great! Let's order pizza.\n"
        f"What type would you like?\n\nMenu:\n{menu_list}",
        parse_mode="Markdown"
    )

# === Шаг 1: Тип пиццы ===
@router.message(PizzaOrder.waiting_for_type, F.text)
async def get_pizza_type(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    # Check if the user's input matches any pizza in the menu
    matched_pizza = None
    for pizza in MENU:
        if user_input == pizza['name'].lower():
            matched_pizza = pizza['name']
            break
    
    if matched_pizza:
        await state.update_data(ptype=matched_pizza)
        await state.set_state(PizzaOrder.waiting_for_quantity)
        await message.answer(
            f"Got it: *{matched_pizza}*\n"
            "How many pizzas would you like? (1–10, e.g., *2* or *two*)",
            parse_mode="Markdown"
        )
    else:
        # Show the menu and ask again
        menu_list = "\n".join([f"- {pizza['name']}" for pizza in MENU])
        await message.answer(
            f"Please select a pizza from the menu:\n{menu_list}"
        )

# === Шаг 2: Количество ===
@router.message(PizzaOrder.waiting_for_quantity, F.text)
async def get_pizza_quantity(message: Message, state: FSMContext):
    try:
        qty = extract_quantity(message.text)
        if qty < 1 or qty > 10:
            qty = 1
        data = await state.get_data()
        orderdict = {
            "product": "pizza",
            "ptype": data["ptype"],
            "qty": qty
        }
        save_order_to_db(orderdict)

        summary = "\n".join(f"{k} - {v}" for k, v in orderdict.items())
        await message.answer(f"✅ Your order:\n{summary}\nThank you! 🍕")
        await state.clear()  # Возврат в универсальный режим
    except ValueError as e:
        await message.answer("⚠️ Please specify a valid number (1–10).")
        await state.set_state(PizzaOrder.waiting_for_quantity)
    except Exception as e:
        logging.error(f"Order error: {e}")
        await message.answer("❌ Failed to save order. Please try again with /pizza.")
        await state.clear()

# === Отмена в любой момент (необязательно, но удобно) ===
@router.message(Command("cancel"))
async def cancel_pizza(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and "PizzaOrder" in current_state:
        await state.clear()
        await message.answer("🍕 Order cancelled. You're back to general mode.\nAsk anything or use /pizza to order again.")
    # Иначе — игнорируем (универсальный бот сам обработает)