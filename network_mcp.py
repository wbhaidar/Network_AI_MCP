from mcp.server import FastMCP
import asyncio
from genie.testbed import load
from genie.libs.parser.utils import get_parser
from genie.metaparser.util.exceptions import SchemaEmptyParserError
import os


# Create an instance of the MCP server
mcp = FastMCP("hello-world-server")

# Configure the settings for remote access -- only relevant when using SSE mode
mcp.settings.host = "0.0.0.0"  # Bind to all network interfaces
mcp.settings.port = 8000       # Specify the port


# Dynamically build path relative to current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTBED_PATH = os.path.join(BASE_DIR, "etc", "testbed.yaml")



# Load the pyATS testbed
testbed = load(TESTBED_PATH)

class DeviceConnectionManager:
    def __init__(self):
        self._connections = {}
        self._connection_locks = {}
    
    async def get_connection(self, device_name: str):
        if device_name not in self._connections:
            device = testbed.devices[device_name]
            await run_in_thread(device.connect)
            self._connections[device_name] = device
            print(f"[DEBUG] New connection established for {device_name}")
        return self._connections[device_name]
    
    async def cleanup_connection(self, device_name: str):
        if device_name in self._connections:
            await run_in_thread(self._connections[device_name].disconnect)
            del self._connections[device_name]

# Global connection manager
connection_manager = DeviceConnectionManager()


# Asynchronous Wrapper for Blocking Calls
def run_in_thread(func, *args, **kwargs):
    """Run synchronous function in a thread."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args, **kwargs)


@mcp.tool()
async def list_devices() -> dict:
    """
    Retrieve a list of devices from the network testbed.

    This tool directly reads from the testbed YAML file loaded on the server.
    The user does NOT need to provide the testbed file content. Simply call this
    to retrieve all devices with metadata including OS, type, function, and management IP.


    Returns:
        dict: {
            "devices": {
                "<device_name>": {
                    "os": "<Operating System>",
                    "type": "<Device Type or Model>",
                    "function": "<Device Role or Purpose>",
                    "management_ip": "<IP Address for Management>"
                },
                ...
            }
        }
    """

    try:
        device_list = {}
        for device in testbed.devices.values():

            device_list[device.name]= {
                "os": device.os or "unknown", 
                "type": device.type  or "unknown",
                "function": getattr(device.custom, "function", "unknown"),
                "management_ip": str(getattr(device.connections.cli, "ip", "unknown"))
                }

        return {"devices": device_list}
    except Exception as e:
        return {"error": f"Failed to list devices: {str(e)}"}

@mcp.tool()
async def show_version(device_name: str) -> dict:
    """
    Run 'show version' on the specified device.

    Args:
        device_name (str): The name of the device in the testbed.

    Returns:
        dict: Parsed or raw output of 'show version' command.
    """
    try:
        if device_name not in testbed.devices:
            return {"error": f"Device not found: {device_name}"}
        
        device = await connection_manager.get_connection(device_name)
        print(f"[DEBUG] Connected to {device_name}")

        try:
            parsed_output = await run_in_thread(device.parse, "show version")
            return {"success": True, "data": parsed_output}
        except SchemaEmptyParserError:
            raw_output = await run_in_thread(device.execute, "show version")
            return {
                "success": True,
                "data": {"raw_output": raw_output},
                "note": "Could not parse, returning raw output"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    except Exception as e:
        return {"success": False, "error": f"Connection or execution error: {str(e)}"}
    
@mcp.tool()
async def discover_neighbors_lldp(device_name: str = "") -> dict:
    """
    🎯 Purpose:
        Discover LLDP neighbors of a given device.

    📥 Parameters:
        device_name (str): Name of the device defined in the pyATS testbed.

    📤 Returns:
        dict: {
            "success": true,
            "device": "<device_name>",
            "neighbors": [
                {
                    "protocol": "lldp",
                    "local_interface": "GigabitEthernet0/0",
                    "remote_device": "switch1",
                    "remote_interface": "GigabitEthernet1/0/1"
                },
                ...
            ]
        }

    🧪 Example Input:
        {
            "device_name": "rtr1"
        }
    """
    if device_name not in testbed.devices:
        return {"success": False, "error": f"Device not found: {device_name}"}

    try:
        device = await connection_manager.get_connection(device_name)
        lldp_output = await run_in_thread(device.parse, "show lldp neighbors detail")

        neighbors = []
        if "interfaces" in lldp_output:
            for local_intf, intf_data in lldp_output["interfaces"].items():
                port_id_dict = intf_data.get("port_id", {})
                for _, port_data in port_id_dict.items():
                    for _, neighbor_info in port_data.get("neighbors", {}).items():
                        neighbors.append({
                            "protocol": "lldp",
                            "local_interface": local_intf,
                            "remote_device": neighbor_info.get("system_name") or neighbor_info.get("neighbor_id"),
                            "remote_interface": neighbor_info.get("port_id") or neighbor_info.get("port_description")
                        })

        return {
            "success": True,
            "device": device_name,
            "neighbors": neighbors
        }

    except SchemaEmptyParserError:
        return {"success": True, "device": device_name, "neighbors": []}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def discover_neighbors_cdp(device_name: str = "") -> dict:
    """
    🎯 Purpose:
        Discover CDP neighbors of a given device.

    📥 Parameters:
        device_name (str): Name of the device defined in the pyATS testbed.

    📤 Returns:
        dict: {
            "success": true,
            "device": "<device_name>",
            "neighbors": [
                {
                    "protocol": "cdp",
                    "local_interface": "GigabitEthernet0/0",
                    "remote_device": "rtr2",
                    "remote_interface": "GigabitEthernet0/2"
                },
                ...
            ]
        }

    🧪 Example Input:
        {
            "device_name": "rtr1"
        }
    """
    if device_name not in testbed.devices:
        return {"success": False, "error": f"Device not found: {device_name}"}

    try:
        device = await connection_manager.get_connection(device_name)
        cdp_output = await run_in_thread(device.parse, "show cdp neighbors detail")

        neighbors = []
        if "index" in cdp_output:
            for _, entry in cdp_output["index"].items():
                neighbors.append({
                    "protocol": "cdp",
                    "local_interface": entry.get("local_interface"),
                    "remote_device": entry.get("device_id"),
                    "remote_interface": entry.get("port_id")
                })

        return {
            "success": True,
            "device": device_name,
            "neighbors": neighbors
        }

    except SchemaEmptyParserError:
        return {"success": True, "device": device_name, "neighbors": []}
    except Exception as e:
        return {"success": False, "error": str(e)}



@mcp.tool()
async def discover_neighbors_combined(device_name: str = "") -> dict:
    """
    🎯 Purpose:
        Discover all neighboring network devices using both LLDP and CDP, with deduplication.

    📥 Parameters:
        device_name (str): Name of the device in the pyATS testbed.

    📤 Returns:
        dict: {
            "success": true,
            "device": "rtr1",
            "neighbors": [
                {
                    "protocol": "cdp" | "lldp",
                    "local_interface": "GigabitEthernet0/0",
                    "remote_device": "rtr2",
                    "remote_interface": "GigabitEthernet0/1",
                    "management_address": "192.168.1.2",
                    "platform": "Cisco 7206VXR"
                },
                ...
            ],
            "total_neighbors": 5
        }

    🧪 Example Input:
        {
            "device_name": "rtr1"
        }
    """
    if device_name not in testbed.devices:
        return {"success": False, "error": f"Device not found: {device_name}"}

    try:
        device = await connection_manager.get_connection(device_name)

        # Run both discovery commands
        lldp_neighbors = []
        cdp_neighbors = []

        # LLDP parsing
        try:
            lldp_output = await run_in_thread(device.parse, "show lldp neighbors detail")
            if "interfaces" in lldp_output:
                for local_intf, intf_data in lldp_output["interfaces"].items():
                    port_id_dict = intf_data.get("port_id", {})
                    for _, port_data in port_id_dict.items():
                        for _, neighbor_info in port_data.get("neighbors", {}).items():
                            lldp_neighbors.append({
                                "protocol": "lldp",
                                "local_interface": local_intf,
                                "remote_device": neighbor_info.get("system_name") or neighbor_info.get("neighbor_id"),
                                "remote_interface": neighbor_info.get("port_id") or neighbor_info.get("port_description"),
                                "management_address": neighbor_info.get("management_address", "unknown"),
                                "platform": neighbor_info.get("system_description", "").split("\n")[0]
                            })
        except SchemaEmptyParserError:
            pass
        except Exception as e:
            print(f"[WARN] LLDP parsing failed: {e}")

        # CDP parsing
        try:
            cdp_output = await run_in_thread(device.parse, "show cdp neighbors detail")
            if "index" in cdp_output:
                for _, entry in cdp_output["index"].items():
                    mgmt_ips = list(entry.get("management_addresses", {}).keys())
                    cdp_neighbors.append({
                        "protocol": "cdp",
                        "local_interface": entry.get("local_interface"),
                        "remote_device": entry.get("device_id"),
                        "remote_interface": entry.get("port_id"),
                        "management_address": mgmt_ips[0] if mgmt_ips else "unknown",
                        "platform": entry.get("platform", "").strip()
                    })
        except SchemaEmptyParserError:
            pass
        except Exception as e:
            print(f"[WARN] CDP parsing failed: {e}")

        # Combine + deduplicate neighbors
        combined = lldp_neighbors + cdp_neighbors
        unique_set = set()
        deduped = []

        for neighbor in combined:
            key = (
                neighbor["local_interface"],
                neighbor["remote_device"],
                neighbor["remote_interface"]
            )
            if key not in unique_set:
                unique_set.add(key)
                deduped.append(neighbor)

        return {
            "success": True,
            "device": device_name,
            "neighbors": deduped,
            "total_neighbors": len(deduped)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}



if __name__ == "__main__":

    # Run MCP server in Stdio mode
    asyncio.run(mcp.run_stdio_async())

    ## Run MCP Server in SSE mode
    #asyncio.run(mcp.run_sse_async())
