"""
Comprehensive test suite verifying database operations, validation, and LangGraph components.
"""

import sys
import tempfile
from pathlib import Path

# Override database for testing
import server
from config import load_config
from server import (
    db_add_task,
    db_complete_task,
    db_list_tasks,
    db_remove_task,
    initialize_database,
)


def run_tests():
    print("========================================")
    print("  RUNNING MCP PRODUCTION TEST SUITE")
    print("========================================")

    # 1. Config Loading
    print("\n[1] Testing Configuration Loading...")
    cfg = load_config()
    assert cfg.groq_api_key, "Groq API key missing in config"
    assert cfg.primary_model, "Primary model missing"
    assert cfg.fallback_model, "Fallback model missing"
    print("    PASSED: Config loaded successfully.")

    # 2. Database Initialization
    print("\n[2] Testing Database Initialization...")
    init_res = initialize_database()
    assert init_res["success"] is True, f"DB init failed: {init_res}"
    print("    PASSED: Database initialized.")

    # 3. Add Task & Edge Cases
    print("\n[3] Testing Add Task (Valid & Invalid)...")
    # Empty title test
    empty_res = db_add_task("   ")
    assert empty_res["success"] is False, "Empty task title should fail"
    print("    PASSED: Empty title validation caught properly.")

    # Valid task test
    add_res = db_add_task("Buy groceries for dinner")
    assert add_res["success"] is True, f"Add task failed: {add_res}"
    task_id = add_res["task_id"]
    assert task_id > 0, "Task ID should be positive integer"
    print(f"    PASSED: Task added with ID {task_id}.")

    # 4. List Tasks
    print("\n[4] Testing List Tasks...")
    list_res = db_list_tasks()
    assert list_res["success"] is True, f"List tasks failed: {list_res}"
    assert list_res["count"] >= 1, "Should have at least 1 task"
    print(f"    PASSED: Retrieved {list_res['count']} tasks.")

    # 5. Complete Task & Edge Cases
    print("\n[5] Testing Complete Task...")
    # Invalid ID (negative)
    inv_res = db_complete_task(-5)
    assert inv_res["success"] is False, "Negative ID should fail"

    # Non-existent ID
    non_res = db_complete_task(999999)
    assert non_res["success"] is False, "Non-existent task should fail"

    # Valid completion
    comp_res = db_complete_task(task_id)
    assert comp_res["success"] is True, f"Complete task failed: {comp_res}"
    print(f"    PASSED: Task {task_id} completed successfully.")

    # 6. Remove Task & Edge Cases
    print("\n[6] Testing Remove Task...")
    # Invalid ID
    inv_rem = db_remove_task(0)
    assert inv_rem["success"] is False, "Zero ID should fail"

    # Valid removal
    rem_res = db_remove_task(task_id)
    assert rem_res["success"] is True, f"Remove task failed: {rem_res}"
    print(f"    PASSED: Task {task_id} removed successfully.")

    # 7. LangGraph Graph Build Test
    print("\n[7] Testing LangGraph Agent Graph Build...")
    import client
    assert client.agent_graph is not None, "Agent graph should compile"
    print("    PASSED: LangGraph agent graph compiled successfully.")

    print("\n========================================")
    print("  ALL TESTS PASSED SUCCESSFULLY! (7/7)")
    print("========================================")


if __name__ == "__main__":
    run_tests()
