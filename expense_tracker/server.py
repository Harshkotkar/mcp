from asyncio import transports
from fastmcp import FastMCP
import os
import sqlite3
import warnings
warnings.filterwarnings("ignore", category=UserWarning)


db_path = os.path.join(os.path.dirname(__file__), "expense.db")

mcp = FastMCP("Expense Tracker MCP")

def init_db():
    with sqlite3.connect(db_path) as c:
        cur = c.execute("PRAGMA table_info(expenses)")
        columns = [row[1] for row in cur.fetchall()]
        if "expence_date" in columns:
            c.execute("ALTER TABLE expenses RENAME COLUMN expence_date TO expense_date")
        elif not columns:
            c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                subcategory TEXT,
                expense_date DATE NOT NULL
            )
            """)

init_db()

@mcp.tool()
def add_expense(
    expense_date: str,
    amount: float,
    description: str,
    category: str = "General",
    subcategory: str = "",
) -> dict:
    """Add a new expense entry and return its ID.

    Args:
        expense_date: Date of the expense in YYYY-MM-DD format (e.g. '2026-09-05').
        amount: The monetary amount spent (positive number).
        description: Description of what was purchased or paid for.
        category: Main expense category (e.g., 'Groceries', 'Food', 'Transport', 'General').
        subcategory: Optional subcategory (e.g., 'Bakery', 'Snacks', 'Taxi').
    """
    with sqlite3.connect(db_path) as c:
        cur = c.execute(
            "INSERT INTO expenses(expense_date, amount, category, subcategory, description) VALUES (?,?,?,?,?)",
            (expense_date, float(amount), category, subcategory, description)
        )
        return {
            "status": "ok",
            "id": cur.lastrowid,
            "message": f"Expense of {amount} for '{description}' recorded successfully with ID {cur.lastrowid} on {expense_date}."
        }

@mcp.tool()
def list_expense(
    start_date: str = "",
    end_date: str = "",
    startdate: str = "",
    enddate: str = "",
) -> list:
    """Fetch expenses between two dates (inclusive).

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g. '2026-09-01').
        end_date: End date in YYYY-MM-DD format (e.g. '2026-09-30').
    """
    start = start_date or startdate or "1970-01-01"
    end = end_date or enddate or "2099-12-31"
    with sqlite3.connect(db_path) as c:
        cur = c.execute(
            "SELECT * FROM expenses WHERE expense_date BETWEEN ? AND ? ORDER BY expense_date DESC",
            (start, end)
        )
        colls = [d[0] for d in cur.description]
        return [dict(zip(colls, r)) for r in cur.fetchall()]

@mcp.tool()
def expense_summary() -> dict:
    """Summary of all transactions."""
    with sqlite3.connect(db_path) as c:
        cur = c.execute("""
            SELECT 
                COUNT(*) AS total_transactions,
                SUM(amount) AS total_amount,
                AVG(amount) AS average_amount,
                MIN(amount) AS smallest_expense,
                MAX(amount) AS largest_expense
            FROM expenses
        """)
        row = cur.fetchone()
        return {
            "total_transactions": row[0],
            "total_amount": row[1],
            "average_amount": row[2],
            "smallest_expense": row[3],
            "largest_expense": row[4]
        }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )