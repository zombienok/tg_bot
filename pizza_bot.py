# pizza_bot.py
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

def get_embedding(text: str):
    """Generate embedding for text using spaCy's word vectors"""
    doc = nlp(text)
    # Use the spaCy document vector
    return doc


def find_best_pizza_match(user_input: str) -> str:
    """Find the best matching pizza from the menu using spaCy similarity"""
    from pizza import MENU
    
    # Create spaCy doc for user input
    user_doc = nlp(user_input.lower())
    
    best_match = None
    best_similarity = 0.0
    
    # Compare with each menu item
    for pizza in MENU:
        menu_doc = nlp(pizza["name"].lower())
        
        # Calculate similarity using spaCy's built-in similarity function
        try:
            similarity = user_doc.similarity(menu_doc)
        except:
            # Fallback if similarity calculation fails
            similarity = 0.0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pizza["name"]
    
    # Return the best match if similarity is above threshold
    if best_similarity >= 0.88:
        return best_match
    else:
        return None

def extract_pizza_type(text: str) -> str:
    doc = nlp(text.lower())
    for token in doc:
        if token.lemma_ == "pizza":
            modifiers = []
            for left in token.lefts:
                if left.dep_ in ("amod", "compound"):
                    modifiers.append(left.text)
            if modifiers:
                candidate_type = " ".join(modifiers + ["pizza"]).title()
                # Check if this candidate matches any menu item using embeddings
                matched_pizza = find_best_pizza_match(candidate_type)
                if matched_pizza:
                    return matched_pizza
                return " ".join(modifiers).title()
            else:
                return "Custom Pizza"
    
    # If no "pizza" token found, try to match the entire text against menu items
    matched_pizza = find_best_pizza_match(text)
    if matched_pizza:
        return matched_pizza
        
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
    await message.answer(
        "🍕 Great! Let's order pizza.\n"
        "What type would you like? (e.g., *pepperoni*, *vegetarian*, *margherita*)",
        parse_mode="Markdown"
    )

# === Шаг 1: Тип пиццы ===
@router.message(PizzaOrder.waiting_for_type, F.text)
async def get_pizza_type(message: Message, state: FSMContext):
    pizza_type = extract_pizza_type(message.text)
    await state.update_data(ptype=pizza_type)
    await state.set_state(PizzaOrder.waiting_for_quantity)
    await message.answer(
        f"Got it: *{pizza_type}*.\n"
        "How many pizzas would you like? (1–10, e.g., *2* or *two*)",
        parse_mode="Markdown"
    )

# === Шаг 2: Количество ===
@router.message(PizzaOrder.waiting_for_quantity, F.text)
async def get_pizza_quantity(message: Message, state: FSMContext):
    try:
        qty = extract_quantity(message.text)
        if qty < 1 or qty > 10:
            qty = 1
        data = await state.get_data()
        pizza_type = data["ptype"]
        
        # Check if pizza type matches menu items with similarity above 0.88
        matched_pizza = find_best_pizza_match(pizza_type)
        if not matched_pizza:
            await message.answer(f"❌ Sorry, we don't have '{pizza_type}' in our menu. Please choose from: Pepperoni, Margherita, or Vegetarian.")
            await state.clear()
            return
        
        # Use the matched pizza name from the menu
        orderdict = {
            "product": "pizza",
            "ptype": matched_pizza,
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