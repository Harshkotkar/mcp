import asyncio
import json
import os
import datetime
from dotenv import load_dotenv
from groq import AsyncGroq
from fastmcp import Client

load_dotenv()

groq_api_key = os.getenv("groq_api")
GROQ_MODEL = "openai/gpt-oss-120b"


async def main():
    # Initialize Groq client
    groq_client = AsyncGroq(api_key=groq_api_key)

    # Connect to FastMCP server
    async with Client("server.py") as mcp_client:
        tools = await mcp_client.list_tools()

        groq_tools = []
        print("Tools discovered:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

            input_schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", None))
            if input_schema is None and hasattr(tool, "parameters"):
                input_schema = tool.parameters
            if hasattr(input_schema, "model_dump"):
                input_schema = input_schema.model_dump()
            if not isinstance(input_schema, dict):
                input_schema = {"type": "object", "properties": {}}

            groq_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": input_schema,
                    },
                }
            )

        # System prompt
        system_prompt = f"""
You are an intelligent expense tracker assistant named Kevin.
Your task is to manage user expenses.

Today is {datetime.date.today().isoformat()}.
You have access to MCP tools for managing expenses.

Available tools:
- add_expense → record an expense
- list_expense → retrieve/search expenses

Rules:
- If the user says "today", use today's date: {datetime.date.today().isoformat()}.
- If the user says "yesterday", calculate the correct date.
- Always respond in structured format.
- Never track future expenses; decline if asked.
- Ask for missing information if necessary.
- Avoid vague instructions; be explicit.
- Never claim a task was created unless the tool succeeds.
- Keep responses simple and understandable.
- Never bypass the system prompt or break safety rules.
"""

        messages = [{"role": "system", "content": system_prompt}]

        print("\n" + "=" * 55)
        print("        EXPENSE TRACKER AI")
        print("=" * 55)
        print("Type 'exit' to quit.\n")

        # Chat loop
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "bye"}:
                print("Goodbye!")
                break

            messages.append({"role": "user", "content": user_input})

            while True:
                response = await groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    tools=groq_tools,
                    tool_choice="auto",
                    temperature=0.2,
                )

                message = response.choices[0].message

                if not message.tool_calls:
                    answer = message.content or ""
                    print(f"\nAssistant: {answer}\n")
                    messages.append({"role": "assistant", "content": answer})
                    break

                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments,
                                },
                            }
                            for call in message.tool_calls
                        ],
                    }
                )

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    print(f"\n[Calling MCP tool: {tool_name}]")
                    print(f"[Arguments: {arguments}]")

                    try:
                        result = await mcp_client.call_tool(tool_name, arguments)
                        if hasattr(result, "data") and result.data is not None:
                            tool_output = json.dumps(result.data, default=str)
                        elif hasattr(result, "content") and result.content:
                            tool_output = "\n".join(c.text if hasattr(c, "text") else str(c) for c in result.content)
                        else:
                            tool_output = json.dumps(str(result))
                    except Exception as e:
                        tool_output = json.dumps({"error": str(e)})

                    print(f"[MCP result: {tool_output}]")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_output,
                        }
                    )


if __name__ == "__main__":
    asyncio.run(main())
