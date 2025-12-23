# test.py
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def find_best_pizza_match(user_input: str, menu) -> str:
    """Find the best matching pizza from the menu using spaCy similarity"""
    
    # Create spaCy doc for user input
    user_doc = nlp(user_input.lower())
    
    best_match = None
    best_similarity = 0.0
    
    # Compare with each menu item
    for pizza in menu:
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

# Test the function with the new menu
MENU = [
    {"name": "Pepperoni"},
    {"name": "Margherita"},
    {"name": "Vegetarian"}
]

# Test cases
test_cases = [
    "pepperoni pizza",
    "margherita pizza", 
    "vegetarian pizza",
    "pepperoni",
    "margherita",
    "vegetarian",
    "peperoni",  # typo
    "meat lovers",  # should not match
    "hawaiian",  # should not match
    "supreme"  # should not match
]

print("Testing pizza matching with spaCy similarity:")
print(f"Menu: {[pizza['name'] for pizza in MENU]}")
print()

for test_case in test_cases:
    matched = find_best_pizza_match(test_case, MENU)
    user_doc = nlp(test_case.lower())
    
    # Calculate similarity with each menu item
    similarities = []
    for pizza in MENU:
        menu_doc = nlp(pizza["name"].lower())
        similarity = user_doc.similarity(menu_doc)
        similarities.append((pizza["name"], similarity))
    
    print(f"Input: '{test_case}' -> Matched: {matched}")
    for pizza_name, sim in similarities:
        print(f"  vs '{pizza_name}': {sim:.4f}")
    print()