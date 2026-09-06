# import asyncio #basicaly asyncio is about concurrency, particularly allowing a program to make progress on other tasks while one task is waiting.
# """
# example of asyncrounous programing is when you are downloading a file and you want to do something else in the meantime
# if we are performing mulitplication and division at the same time we can do it using asyncrounous programing
# """

# from fastmcp import Client

# async def main():
#     async with Client("calulator_mcp.py") as client:
#         await client.ping() # basically this will check wether the server is rechable or not
         
#         print("mcp server connected!")

#         tools=await client.list_tools() # check the avalable tools
#         print("\navailable tools:")
#         for tool in tools:
#             print(f'-{tool.name}, {tool.description}')
        
# if __name__=="__main__":
#     asyncio.run(main())

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import os
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from fastmcp import Client
load_dotenv()

llm=OpenAI(base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTE"],
)

server_params = StdioServerParameters(
    command="mcp",  # Executable
)
print("HOST.PY STARTED")

def call_llm(prompt, functions):

    response = llm.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=300,
        tools=functions,
        top_p=1.0
    )

    response_text = response.choices[0].message

    print("\nLLM RESPONSE:")
    print(response_text)

    function_calls = [] 

    if response_text.tool_calls: # if the llm wants to call a tool

        for tool_call in response_text.tool_calls: # loop through each tool call

            print("\nTOOL CALL:")
            print(tool_call)

            name = tool_call.function.name # get the name of the tool

            args = json.loads(
                tool_call.function.arguments # get the arguments of the tool
            )

            function_calls.append({
                "name": name,
                "args": args,
                "id": tool_call.id
            })

    return response_text, function_calls

def get_final_answer(messages):

    response = llm.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
        max_tokens=300,
    )

    return response.choices[0].message.content #  this will give us the response from the llm basically [0] means the inddex 0 which is the first message from the llm [1] will be the msg of user
    #-------------------------------------top_p-------------------------------------------------
    """
    
    When the model is about to generate the next word (token), it has a probability distribution over all possible words.

top_p says: “Only consider the smallest set of words whose combined probability is at least p.”
Suppose the model predicts the next word with probabilities:
"cat" → 0.5
"dog" → 0.3
"fish" → 0.1
"car" → 0.05
"tree" → 0.05
If top_p = 1.0 → include all tokens (cat, dog, fish, car, tree).
If top_p = 0.8 → only include "cat" (0.5) + "dog" (0.3) = 0.8. The rest are ignored.
If top_p = 0.6 → only "cat" (0.5) + "dog" (0.3) because together they exceed 0.6.
So the smaller the value, the narrower the set of possible words.
--->top_p = 1.0 → maximum diversity, the model can pick from all tokens.
Lower top_p (like 0.8 or 0.9) → more focused, avoids unlikely or “weird” words.
Very low top_p (like 0.2) → extremely restrictive, the model only picks from the most probable few tokens, making output deterministic and repetitive.
    """


def convert_to_llm_tool(tool):
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    }


async def main():

    print("MAIN FUNCTION STARTED")

    async with Client("server.py") as client:

        print("CLIENT CREATED")

        await client.ping()

        print("MCP SERVER CONNECTED!")

        tools = await client.list_tools()

        functions = []

        for tool in tools:

            print("Tool:", tool.name)
            print("Tool:", tool.inputSchema["properties"])

            functions.append(
                convert_to_llm_tool(tool)
            )

        # -------------------------------
        # 1. Ask LLM which MCP tool to use
        # -------------------------------

        response_text, functions_to_call = call_llm(
            prompt,
            functions
        )

        # -------------------------------
        # 2. No tool required
        # -------------------------------

        if not functions_to_call:

            print("\nFINAL ANSWER:")
            print(response_text.content)

            return

        # -------------------------------
        # 3. Prepare conversation
        # -------------------------------

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            },
            response_text.model_dump()
        ]

        # -------------------------------
        # 4. Execute MCP tools
        # -------------------------------

        for f in functions_to_call:

            print("\nCALLING MCP TOOL:")
            print("Name:", f["name"])
            print("Arguments:", f["args"])

            result = await client.call_tool(
                f["name"],
                arguments=f["args"]
            )

            print("TOOLS result:", result.content)

            tool_result = result.content[0].text

            messages.append({
                "role": "tool",
                "tool_call_id": f["id"],
                "content": tool_result
            })

        # -------------------------------
        # 5. Give MCP result back to LLM
        # -------------------------------

        final_answer = get_final_answer(messages)

        print("\nFINAL ANSWER:")
        print(final_answer)

if __name__ == "__main__":
    print("RUNNING MAIN")
    prompt=input("enter prompt")
    asyncio.run(main())


    """
User prompt
    ↓
OpenRouter LLM
    ↓
LLM understands the problem
    ↓
LLM chooses MCP tool: subtract
    ↓
LLM generates arguments: {"x":20,"y":9}
    ↓
MCP Client
    ↓
MCP Server
    ↓
subtract(20, 9)
    ↓
11.0
    ↓
Result sent back to LLM
    ↓
Final natural-language answer
    """
