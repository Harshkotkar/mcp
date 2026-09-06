

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from dotenv import load_dotenv
from fastmcp import FastMCP
from langsmith import traceable

# Load environment
load_dotenv()

# Server setup
mcp = FastMCP("THE PROMPT TESTING")

# Database Path Configuration
DATABASE_PATH_STR = os.getenv("DATABASE_PATH", "./data/tasks.db")
DB_PATH = Path(DATABASE_PATH_STR)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# --- Database Connection Manager ---

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite connections with row factory,
    automatic commit on success, and rollback on error.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Database Operations with LangSmith Tracing ---

@traceable(name="SQLite - Initialize Database", run_type="tool")
def initialize_database() -> dict[str, Any]:
    """Initializes the SQLite schema with table and performance indexes."""
    start = time.perf_counter()
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_completed
                ON tasks (completed)
                """
            )
        latency = time.perf_counter() - start
        return {
            "operation": "initialize_database",
            "success": True,
            "latency_seconds": latency,
        }
    except sqlite3.Error as exc:
        latency = time.perf_counter() - start
        return {
            "operation": "initialize_database",
            "success": False,
            "error": str(exc),
            "latency_seconds": latency,
        }


# Initialize DB on module load
initialize_database()


@traceable(name="SQLite - Add Task", run_type="tool")
def db_add_task(title: str) -> dict[str, Any]:
    """Inserts a new task into the database."""
    start = time.perf_counter()
    clean_title = title.strip()
    if not clean_title:
        return {
            "operation": "add_task",
            "success": False,
            "error": "Task title cannot be empty.",
            "latency_seconds": time.perf_counter() - start,
        }

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title) VALUES (?)",
                (clean_title,),
            )
            task_id = cursor.lastrowid

        latency = time.perf_counter() - start
        return {
            "operation": "add_task",
            "task_id": task_id,
            "title": clean_title,
            "success": True,
            "latency_seconds": latency,
            "message": f"Task '{clean_title}' added with ID {task_id}",
        }
    except sqlite3.Error as exc:
        latency = time.perf_counter() - start
        return {
            "operation": "add_task",
            "title": clean_title,
            "success": False,
            "error": f"Database error while adding task: {exc}",
            "latency_seconds": latency,
        }


@traceable(name="SQLite - List Tasks", run_type="tool")
def db_list_tasks() -> dict[str, Any]:
    """Retrieves all tasks from the database ordered by ID."""
    start = time.perf_counter()
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, completed, created_at
                FROM tasks
                ORDER BY id ASC
                """
            ).fetchall()

        latency = time.perf_counter() - start
        task_list = [
            {
                "id": row["id"],
                "title": row["title"],
                "completed": bool(row["completed"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
        return {
            "operation": "list_tasks",
            "count": len(task_list),
            "tasks": task_list,
            "success": True,
            "latency_seconds": latency,
        }
    except sqlite3.Error as exc:
        latency = time.perf_counter() - start
        return {
            "operation": "list_tasks",
            "success": False,
            "error": f"Database error while retrieving tasks: {exc}",
            "latency_seconds": latency,
        }


@traceable(name="SQLite - Complete Task", run_type="tool")
def db_complete_task(task_id: int) -> dict[str, Any]:
    """Marks a task as completed in the database."""
    start = time.perf_counter()
    if not isinstance(task_id, int) or task_id <= 0:
        return {
            "operation": "complete_task",
            "task_id": task_id,
            "success": False,
            "error": f"Invalid task ID: {task_id}. Task ID must be a positive integer.",
            "latency_seconds": time.perf_counter() - start,
        }

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET completed = 1 WHERE id = ?",
                (task_id,),
            )
            affected = cursor.rowcount

        latency = time.perf_counter() - start
        if affected == 0:
            return {
                "operation": "complete_task",
                "task_id": task_id,
                "success": False,
                "error": f"Task with ID {task_id} was not found.",
                "latency_seconds": latency,
            }

        return {
            "operation": "complete_task",
            "task_id": task_id,
            "success": True,
            "latency_seconds": latency,
            "message": f"Task {task_id} marked as completed.",
        }
    except sqlite3.Error as exc:
        latency = time.perf_counter() - start
        return {
            "operation": "complete_task",
            "task_id": task_id,
            "success": False,
            "error": f"Database error while completing task: {exc}",
            "latency_seconds": latency,
        }


@traceable(name="SQLite - Remove Task", run_type="tool")
def db_remove_task(task_id: int) -> dict[str, Any]:
    """Deletes a task from the database."""
    start = time.perf_counter()
    if not isinstance(task_id, int) or task_id <= 0:
        return {
            "operation": "remove_task",
            "task_id": task_id,
            "success": False,
            "error": f"Invalid task ID: {task_id}. Task ID must be a positive integer.",
            "latency_seconds": time.perf_counter() - start,
        }

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )
            affected = cursor.rowcount

        latency = time.perf_counter() - start
        if affected == 0:
            return {
                "operation": "remove_task",
                "task_id": task_id,
                "success": False,
                "error": f"Task with ID {task_id} was not found.",
                "latency_seconds": latency,
            }

        return {
            "operation": "remove_task",
            "task_id": task_id,
            "success": True,
            "latency_seconds": latency,
            "message": f"Task {task_id} removed.",
        }
    except sqlite3.Error as exc:
        latency = time.perf_counter() - start
        return {
            "operation": "remove_task",
            "task_id": task_id,
            "success": False,
            "error": f"Database error while removing task: {exc}",
            "latency_seconds": latency,
        }


# --- FastMCP Tool Endpoints ---

@mcp.tool()
def add_task(title: str) -> str:
    """Add a new task."""
    result = db_add_task(title)
    if result["success"]:
        return result["message"]
    return f"Error: {result['error']}"


@mcp.tool()
def list_task() -> str:
    """List all tasks."""
    result = db_list_tasks()
    if not result["success"]:
        return f"Error: {result['error']}"

    tasks = result.get("tasks", [])
    if not tasks:
        return "No tasks found."

    formatted = []
    for task in tasks:
        status = "Completed" if task["completed"] else "Pending"
        formatted.append(
            f"ID: {task['id']}, Title: {task['title']}, Status: {status}, Created: {task['created_at']}"
        )
    return "\n".join(formatted)


@mcp.tool()
def complete_task(task_id: int) -> str:
    """Complete a task."""
    result = db_complete_task(task_id)
    if result["success"]:
        return result["message"]
    return f"Error: {result['error']}"


@mcp.tool()
def remove_task(task_id: int) -> str:
    """Remove a task."""
    result = db_remove_task(task_id)
    if result["success"]:
        return result["message"]
    return f"Error: {result['error']}"


# --- FastMCP System Prompt ---

@mcp.prompt()
def task_assistant() -> str:
    """Prompt for helping the user manage tasks."""
    return """
You are a helpful task assistant.

When the user asks about their tasks:
- Use list_task to inspect the current tasks.
- Use add_task when the user wants to create a task.
- Use complete_task when the user says they finished a task.
- Use remove_task when the user wants to delete a task.

Guidelines:
1. Always inspect tasks before making assumptions about existing tasks.
2. Before completing or removing a task, make sure the exact task ID is known.
3. Never claim that a task was created, completed, or removed unless the corresponding tool succeeds.
4. If a tool returns an error, report the error honestly to the user.
5. Do not invent task IDs or task information.
"""


if __name__ == "__main__":
    mcp.run(transport="streamable-http")