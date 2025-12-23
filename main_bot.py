# main_bot.py
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import spacy
import wikipedia
from dotenv import load_dotenv



load_dotenv()
API_TOKEN = os.getenv('BOT_API_KEY')

logging.basicConfig(level=logging.INFO)
nlp = spacy.load("en_core_web_sm")
wikipedia.set_lang("en")
main_router = Router()

# === Универсальные функции (без изменений) ===
def extract_keyphrase(doc):
    for token in doc:
        if token.dep_ == "pobj":
            tokens = [left for left in token.lefts if left.dep_ in ("amod", "compound")]
            tokens.append(token)
            for child in token.rights:
                if child.dep_ == "prep":
                    tokens.append(child)
                    for gc in child.children:
                        if gc.dep_ == "pobj":
                            tokens.extend([gcl for gcl in gc.lefts if gcl.dep_ in ("amod", "compound")] + [gc])
            if tokens:
                return " ".join(t.text for t in sorted(tokens, key=lambda x: x.i))
    verbs = [t for t in reversed(doc) if t.pos_ == "VERB"]
    for verb in verbs:
        subj = next((c for c in verb.children if c.dep_ == "nsubj"), None)
        if subj:
            subj_part = [left for left in subj.lefts if left.dep_ in ("amod", "compound")]
            subj_part.append(subj)
            phrase = " ".join(t.text for t in sorted(subj_part, key=lambda x: x.i)) + " " + verb.lemma_
            dobj = next((c for c in verb.children if c.dep_ == "dobj"), None)
            if dobj:
                dobj_part = [left for left in dobj.lefts if left.dep_ in ("amod", "compound")]
                dobj_part.append(dobj)
                phrase += " " + " ".join(t.text for t in sorted(dobj_part, key=lambda x: x.i))
            return phrase.strip()
    return " ".join(t.text for t in doc if t.pos_ in ("NOUN", "PROPN", "VERB")) or str(doc)

def search_wikipedia(query: str) -> str:
    try:
        return wikipedia.summary(query, sentences=1)
    except wikipedia.exceptions.DisambiguationError as e:
        return wikipedia.summary(e.options[0], sentences=1) if e.options else f"Too many meanings for '{query}'."
    except wikipedia.exceptions.PageError:
        return f"Nothing found about '{query}' in Wikipedia."
    except Exception:
        return "Sorry, Wikipedia search failed."



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

def detect_pizza_intent(text: str) -> bool:
    """Detect if the user wants to order pizza using spaCy"""
    doc = nlp(text.lower())
    
    # Check for variations of "i want a pizza" and similar phrases
    for token in doc:
        if token.lemma_ in ["want", "would", "like", "need", "order", "get"]:
            # Look for pizza in the sentence
            for child in token.subtree:
                if child.lemma_ in ["pizza", "pizzas"]:
                    return True
    
    # Check for common phrases indicating pizza intent
    lower_text = text.lower()
    pizza_intents = [
        "i want a pizza",
        "i want some pizza",
        "i would like a pizza",
        "i need a pizza",
        "i'd like a pizza",
        "i want pizza",
        "i would like pizza",
        "i need pizza",
        "i'd like pizza",
        "can i get a pizza",
        "can i have a pizza",
        "order pizza",
        "get pizza"
    ]
    
    for intent in pizza_intents:
        if intent in lower_text:
            return True
            
    return False

def extract_pizza_info(text: str):
    """Extract pizza type and quantity from text using spaCy"""
    doc = nlp(text.lower())
    
    # Extract quantity
    quantity = 1  # default
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a": 1, "an": 1
    }
    
    # Look for numbers and number words
    for token in doc:
        if token.text in word_to_num:
            quantity = word_to_num[token.text]
        elif token.text.isdigit():
            quantity = int(token.text)
        elif token.lemma_ in ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]:
            quantity = word_to_num[token.lemma_]
    
    # Extract pizza type by looking for adjectives or nouns before/around "pizza"
    pizza_type = None
    for token in doc:
        if token.lemma_ == "pizza":
            # Look for modifiers (adjectives, compounds) before the pizza token
            modifiers = []
            for left in token.lefts:
                if left.dep_ in ("amod", "compound", "det"):
                    modifiers.append(left.text)
            
            # If no modifiers found, check if there are other nouns nearby that might be pizza types
            if not modifiers:
                # Look at tokens within a certain distance
                for i, t in enumerate(doc):
                    if t != token and t.pos_ in ("NOUN", "ADJ") and abs(t.i - token.i) <= 2:
                        modifiers.append(t.text)
            
            if modifiers:
                pizza_type = " ".join(modifiers).title()
            else:
                pizza_type = "Custom Pizza"
            break
    
    # If we didn't find a specific type but there are adjectives that could be pizza types
    if not pizza_type:
        for token in doc:
            if token.pos_ == "ADJ" and token.lemma_ in ["pepperoni", "margherita", "vegetarian", 
                                                        "hawaiian", "meat", "bbq", "chicken", 
                                                        "supreme", "cheese", "four"]:
                pizza_type = token.text.title()
                break
    
    return quantity, pizza_type

def check_pizza_in_menu(pizza_type: str) -> bool:
    """Check if the pizza type exists in the menu using spaCy similarity"""
    # Import the menu from pizza.py
    from pizza import MENU
    import spacy
    
    nlp = spacy.load("en_core_web_sm")
    
    # Create spaCy doc for the pizza type
    user_doc = nlp(pizza_type.lower())
    
    # Compare with each menu item
    for pizza in MENU:
        menu_doc = nlp(pizza['name'].lower())
        
        # Calculate similarity using spaCy's built-in similarity function
        try:
            similarity = user_doc.similarity(menu_doc)
        except:
            # Fallback if similarity calculation fails
            similarity = 0.0
        
        # Return True if similarity is above threshold
        if similarity >= 0.88:
            return True
    return False

@main_router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    # Check if the user wants to order pizza
    if detect_pizza_intent(message.text):
        quantity, pizza_type = extract_pizza_info(message.text)
        
        # Check if we have enough information to place an order
        if pizza_type and check_pizza_in_menu(pizza_type):
            # We have a valid pizza type from the menu, so place the order directly
            from pizza import save_order_to_db
            
            orderdict = {
                "product": "pizza",
                "ptype": pizza_type,
                "qty": quantity
            }
            
            try:
                save_order_to_db(orderdict)
                summary = "\n".join(f"{k} - {v}" for k, v in orderdict.items())
                await message.answer(f"✅ Your pizza order has been placed:\n{summary}\nThank you! 🍕")
            except Exception as e:
                logging.error(f"Order error: {e}")
                await message.answer("❌ Failed to save order. Please try again with /pizza.")
        else:
            # Need more information, ask the user
            await message.answer(
                f"Great! I can help you order pizza.\n"
                f"I detected you want to order {quantity} pizza(s), but I need to know the type.\n"
                f"Available options: Pepperoni, Margherita, Vegetarian\n"
                f"What type of pizza would you like?"
            )
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
async def handle_photo(message: Message, bot: Bot):
    current_state = await state.get_state()
    if current_state and "PizzaOrder" in current_state:
        await message.answer("Please finish your pizza order first before sending photos.")
        return

    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        os.makedirs("temp", exist_ok=True)
        path = f"temp/{photo.file_id}.jpg"
        await bot.download_file(file.file_path, path)
        
        # Use the image module for tag extraction
        from image import get_photo_tags
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
    dp.include_router(main_router)   # universal fallback
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())