from mcp.client.sse import sse_client
from mcp import ClientSession
import asyncio


async def test_list_devices():
    try:
        async with sse_client(url="http://127.0.0.1:8000/sse") as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                print('Session initialized successfully')

                print('Testing list devices function...')

                result = await session.call_tool("list_devices")
                
                print('Output:')
                print(result)
                
    except ConnectionError as e:
        print(f"Connection error: {e}")
    except TimeoutError as e:
        print(f"Timeout error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


async def test_run_show_command():
    async with sse_client(url="http://127.0.0.1:8000/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            
            # Call the 'run_show_command' tool
            device_name = "cbtdcnfl-ncml-rt01"
            command = "show version"

            print(f"Testing {command} on device {device_name}...")
            try:
                result = await session.call_tool(
                    "run_show_command",
                    {"device_name": device_name, "command": command}
                )
                print("Command output:")
                print(result)
            except Exception as e:
                print(f"Error while calling the tool: {e}")

if __name__ == "__main__":
    # Run the client asynchronously

    asyncio.run(test_list_devices())
#    asyncio.run(test_run_show_command())
