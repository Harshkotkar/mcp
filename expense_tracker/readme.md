# Expense Tracker MCP

An intelligent expense tracking assistant built using the **Model Context Protocol (MCP)**, **FastMCP**, and **Groq LLM**.

## Features

- **Natural Language Assistant**: Chat with an AI assistant ("Kevin") to log, query, and summarize expenses.
- **SQLite Storage**: Persistent and lightweight database (`expense.db`) for tracking transactions.
- **MCP Tools**:
  - `add_expense`: Add new expenses with date, amount, category, subcategory, and description.
  - `list_expense`: Query expenses filtered by date range.
  - `expense_summary`: Get aggregate stats (total spend, transaction counts, average, min/max).

## Project Structure

```
expense_tracker/
├── server.py       # FastMCP server providing SQLite-backed expense tools
├── host.py         # AI client connected to Groq and the FastMCP server
├── expense.db      # SQLite database (auto-generated)
├── .env            # Environment configuration (API keys)
└── readme.md       # Project documentation
```

## Setup & Usage

### 1. Environment Variables
Create a `.env` file in the `expense_tracker` directory:
```env
groq_api=your_groq_api_key_here
```

### 2. Run the Server
Start the FastMCP server:
```bash
python server.py
```

### 3. Run the AI Host
Run the interactive terminal assistant:
```bash
python host.py
```

## Example Prompts

- *"I spent $15 on lunch today (food / fast-food)."*
- *"Show all my expenses for this week."*
- *"Give me a summary of all my spending so far."*
