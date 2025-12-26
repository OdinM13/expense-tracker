import sqlite3
import random
from datetime import datetime, timedelta

def seed_database():
    # Configuration
    db_path = "finance.db"
    user_id = 1  # Ensure this matches your user ID in the database
    starting_balance = 10000.00
    
    # Categories for expenses
    categories = ["Food", "Rent", "Leisure", "Travel", "Health", "Subscriptions"]
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        db = conn.cursor()
        
        print(f"Cleaning old data for User ID {user_id}...")
        db.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM income WHERE user_id = ?", (user_id,))
        
        print("Generating new test data...")
        
        total_income = 0
        total_expenses = 0

        # 1. Generate random Income (Deposits)
        for i in range(3):
            amount = random.randint(500, 2000)
            days_ago = random.randint(0, 28)
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            db.execute("INSERT INTO income (user_id, amount, date) VALUES (?, ?, ?)", 
                       (user_id, amount, date))
            total_income += amount

        # 2. Generate 40 random Expenses
        for i in range(40):
            category = random.choice(categories)
            amount = round(random.uniform(5.0, 150.0), 2)
            days_ago = random.randint(0, 30)
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            description = f"Test {category} purchase"

            db.execute(
                "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, description, date)
            )
            total_expenses += amount

        # 3. Calculate and update the final cash balance
        # Formula: Initial + Inflow - Outflow
        final_cash = starting_balance + total_income - total_expenses
        db.execute("UPDATE users SET cash = ? WHERE id = ?", (final_cash, user_id))
        
        # Commit changes and close
        conn.commit()
        conn.close()
        
        print("-" * 30)
        print(f"Seeding complete!")
        print(f"Total Income generated:  +${total_income:,.2f}")
        print(f"Total Expenses generated: -${total_expenses:,.2f}")
        print(f"New Database Balance:      ${final_cash:,.2f}")
        print("-" * 30)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    seed_database()
