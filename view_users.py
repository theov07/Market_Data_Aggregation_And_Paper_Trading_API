"""
Script simple pour afficher les utilisateurs de users.db
"""
import sqlite3
from tabulate import tabulate

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
users = cursor.fetchall()

print("\n" + tabulate(users, headers=["ID", "Username", "Created At"], tablefmt="pretty"))
print(f"\nTotal: {len(users)} users\n")

conn.close()
