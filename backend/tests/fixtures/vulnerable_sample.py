"""
Deliberately vulnerable/smelly sample code — used ONLY to validate that the Code Analysis and
Security Vulnerability agents actually detect known issues (Milestone 2, Task 4). Never import
or execute this file's functions; it exists purely as static text for the agents to analyze.
"""
import hashlib
import pickle
import sqlite3

from django.views.decorators.csrf import csrf_exempt

AWS_ACCESS_KEY = "AKIAFAKETESTKEY0"
db_password = "SuperSecret123!"


def get_user_by_id(request, user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()


def get_order(request, order_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM orders WHERE id = {order_id}")
    return cursor.fetchone()


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def load_session(data):
    return pickle.loads(data)


@csrf_exempt
def webhook_handler(request):
    process_payment(request.POST)


def deeply_nested_and_over_parameterized(a, b, c, d, e, f, g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            return g
    try:
        risky_operation()
    except:
        pass
    return None


def duplicate_one(items):
    total = 0
    for item in items:
        total += item.value
    return total


def duplicate_two(entries):
    total = 0
    for item in entries:
        total += item.value
    return total


class GodObject:
    def method_one(self): pass
    def method_two(self): pass
    def method_three(self): pass
    def method_four(self): pass
    def method_five(self): pass
    def method_six(self): pass
    def method_seven(self): pass
    def method_eight(self): pass
    def method_nine(self): pass
    def method_ten(self): pass
    def method_eleven(self): pass
    def method_twelve(self): pass
    def method_thirteen(self): pass
    def method_fourteen(self): pass
    def method_fifteen(self): pass
    def method_sixteen(self): pass


def bad_default(items=[]):
    items.append(1)
    return items
