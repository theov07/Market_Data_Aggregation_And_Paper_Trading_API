import sqlite3
from tabulate import tabulate

def view_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("  PAPER TRADING DATABASE")
    print("="*80)
    
    cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
    users = cursor.fetchall()
    
    print("\nUSERS")
    print("-" * 80)
    if users:
        print(tabulate(users, headers=["ID", "Username", "Created At"], tablefmt="simple"))
        print(f"\nTotal: {len(users)} users")
    else:
        print("No users found")
    
    cursor.execute("""
        SELECT b.id, u.username, b.asset, b.total, b.available, b.reserved, b.updated_at
        FROM balances b
        JOIN users u ON b.user_id = u.id
        ORDER BY u.id, b.asset
    """)
    balances = cursor.fetchall()
    
    print("\n\nBALANCES")
    print("-" * 80)
    if balances:
        print(tabulate(balances, 
                      headers=["ID", "Username", "Asset", "Total", "Available", "Reserved", "Updated"],
                      tablefmt="simple",
                      floatfmt=".4f"))
        print(f"\nTotal: {len(balances)} balances")
    else:
        print("No balances found")
    
    cursor.execute("""
        SELECT o.id, u.username, o.token_id, o.symbol, o.side, o.price, o.quantity, o.status, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 50
    """)
    orders = cursor.fetchall()
    
    print("\n\nORDERS (Last 50)")
    print("-" * 80)
    if orders:
        print(tabulate(orders,
                      headers=["ID", "Username", "Token ID", "Symbol", "Side", "Price", "Quantity", "Status", "Created"],
                      tablefmt="simple",
                      floatfmt=".6f"))
        print(f"\nShowing last 50 orders")
    else:
        print("No orders found")
    
    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    order_stats = cursor.fetchall()
    
    if order_stats:
        print("\n\nORDER STATISTICS")
        print("-" * 80)
        print(tabulate(order_stats, headers=["Status", "Count"], tablefmt="simple"))
    
    print("\n" + "="*80 + "\n")
    
    conn.close()

if __name__ == "__main__":
    view_database()
