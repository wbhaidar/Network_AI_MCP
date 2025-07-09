# Network MCP

## 🧠 Overview

**Network MCP** is an experimental project to build a Model Context Protocol (MCP) server that enables **AI agents** to interact with network environments — particularly virtual topologies built in **GNS3** — using natural language queries.

This project integrates:
- 🧠 AI agents via the [FastMCP](https://github.com/ContextualAI/fast-mcp) framework
- 🔧 Network devices defined via a **pyATS testbed**
- 🧪 Network command execution, parsing, and discovery using **pyATS/Genie**

---

## 🌐 Purpose

The goal is to expose a set of tools to AI agents through the MCP interface so they can:
- Discover network devices and their metadata
- Execute commands such as `show version`
- Parse and combine CDP/LLDP neighbor info
- Work against **live or simulated environments** (like GNS3)

---

## ⚙️ Requirements

- Python 3.8+
- `pyATS` and `Genie`
- GNS3 network topology (or any SSH-accessible network environment)
- A valid `testbed.yaml` file that defines your devices

---

## 📦 Install Dependencies

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🛠️ Configure Your Testbed

Update `etc/testbed.yaml` with your network device definitions.

Example:

```yaml
testbed:
  name: GNS3 Lab

devices:
  rtr1:
    os: iosxe
    type: router
    custom:
      function: edge
    connections:
      cli:
        protocol: ssh
        ip: 192.168.1.10
        port: 22
        username: cisco
        password: cisco
```

---

## ▶️ Integrate the MCP Server with your LLM interface


To connect your MCP tools to a local LLM (like [LM Studio](https://lmstudio.ai)), update the relevant mcp config file. 

For instance, here is relevant config file for LM Studio
```text
{
  "mcpServers": {
    "network_mcp": {
      "command": "/Users/user/venv_mcp/bin/python3",
      "args": [
        "/Users/user/network_mcp/network_mcp.py"
      ]
    }
  }
}
```

---

## 🧰 Available Tools

These functions are available via MCP-compatible agents or HTTP POSTs to the `/mcp` endpoint.

| Tool Name                     | Description                                                        |
|------------------------------|--------------------------------------------------------------------|
| `list_devices()`             | Lists all devices from the testbed with metadata                   |
| `show_version(device_name)`  | Runs and parses `show version` on a device                         |
| `discover_neighbors_lldp()`  | Parses LLDP neighbors on the device                                |
| `discover_neighbors_cdp()`   | Parses CDP neighbors on the device                                 |
| `discover_neighbors_combined()` | Combines CDP + LLDP with deduplication, includes platform and management IPs |

---
