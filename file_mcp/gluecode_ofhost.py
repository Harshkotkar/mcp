print("MAIN FUNCTION STARTED")

    async with Client("server.py") as client:
        print("CLIENT CREATED")

        await client.ping()


        print("MCP SERVER CONNECTED!")

        tools = await client.list_tools()

        # print("\nAVAILABLE TOOLS:")

        # for tool in tools:
        #     print("\nTOOL OBJECT:")
        #     print(tool)

        #     print("\nTOOL NAME:")
        #     print(tool.name)

        #     print("\nTOOL DESCRIPTION:")
        #     print(tool.description)

        #     print("\nTOOL INPUT SCHEMA:")
        #     print(tool.inputSchema)

        # for tool in tools:
        #     print(f"- {tool.name}: {tool.description}")

        # print("\n resource available:")
        # resource=await client.list_resources()
        # for r in resource:
        #     print(f"-{resource.name}")

        # print("RESOURCE:")
        # content=await client.read_resource("greeting://bunny")
        # print("CONTENT:", content)

        functions = []

        for tool in tools:
            print("Tool: ", tool.name)
            print("Tool", tool.inputSchema["properties"])
            functions.append(convert_to_llm_tool(tool))
        
        

        # ask LLM what tools to all, if any
        #functions_to_call = call_llm(prompt, functions)

        # call suggested functions
        # for f in functions_to_call:
        #     result = await client.call_tool(f["name"], arguments=f["args"])
        #     print("TOOLS result: ", result.content)
        response_text, functions_to_call = call_llm(
            prompt,
            functions
        )

        if functions_to_call:

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

            for f in functions_to_call:

                result = await client.call_tool(
                    f["name"],
                    arguments=f["args"]
                )

                print(
                    "TOOLS result:",
                    result.content
                )

                tool_result = result.content[0].text

                messages.append({
                    "role": "tool",
                    "tool_call_id": f["id"],
                    "content": tool_result
                })

            final_answer = get_final_answer(messages)

            print("\nFINAL ANSWER:")
            print(final_answer)

        else:

            print("\nFINAL ANSWER:")
            print(response_text.content)


if __name__ == "__main__":
    print("RUNNING MAIN")
    prompt=input("enter prompt")
    asyncio.run(main())