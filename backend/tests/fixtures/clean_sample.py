"""
Deliberately clean, reasonably well-written sample code — used to confirm the agents don't
flag ordinary, non-vulnerable code (a basic false-positive check for Milestone 2, Task 4).
"""
import os


def get_user_by_id(db_connection, user_id: int):
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def calculate_total(cart_items: list) -> float:
    return sum(item.price for item in cart_items)


def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def load_api_key() -> str:
    return os.environ["API_KEY"]


def process_items(items: list, threshold: int = 10) -> list:
    result = []
    for item in items:
        if item.value > threshold:
            result.append(item)
    return result


class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def total(self):
        return sum(item.price for item in self.items)
