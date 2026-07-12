# Email Guardian

Email Guardian is a full-stack security and policy enforcement system for email management. It uses an AI agent to process emails, route them through a Model Context Protocol (MCP) server that exposes email tools, evaluate policies using a pure Python rule engine, log all actions to an SQLite audit log, and interact with a mock email store. All of this is exposed via a FastAPI backend and displayed on a Vite-powered React frontend.

## Architecture

The project consists of the following components flow:

```
[ React Frontend ]
        │
        ▼
[ FastAPI Backend (api) ]
        │
        ▼
[ LangChain Agent (agent) ]
        │
        ▼
[ MCP Server (mcp_server) ] ── (Uses email tools)
        │
        ├──► [ Policy Engine (policy_engine) ] ──► (Evaluates YAML Rules in rules/)
        │
        ├──► [ Audit Log (audit) ] ──► (Writes to SQLite database)
        │
        └──► [ Mock Email Store (mock_email) ] ──► (Simulates email inbox/actions)
```

1. **Frontend**: A Vite + React application providing a dashboard to view the email inbox, configure policy rules, and inspect audit logs.
2. **FastAPI Backend (`backend/api`)**: The API layer that ties everything together, serving as the bridge between the React frontend and the backend services.
3. **LangChain Agent (`backend/agent`)**: An intelligent agent that decides how to handle emails using the tools exposed by the MCP server.
4. **MCP Server (`backend/mcp_server`)**: A Model Context Protocol server that wraps low-level email tools (e.g., read, send, flag, delete) and applies policy checks before executing them.
5. **Policy Engine (`backend/policy_engine`)**: A pure Python rule evaluation engine that checks actions against YAML-defined policies (stored in `backend/rules/`) without external service dependencies.
6. **Audit Log (`backend/audit`)**: An SQLite-based logging system that records every tool call, policy evaluation result, and agent action for auditability.
7. **Mock Email Store (`backend/mock_email`)**: A simulated email database/inbox containing test emails to safely test agent interactions and policy checks.

## Project Structure

```text
/
├── backend/
│   ├── pyproject.toml         # uv Python dependencies configuration
│   ├── agent/                 # LangChain agent code
│   ├── mcp_server/            # MCP server exposing email tools
│   ├── policy_engine/         # Pure Python rule evaluation engine
│   ├── rules/                 # YAML rule files
│   ├── audit/                 # SQLite-based audit logger
│   ├── mock_email/            # Fake email store simulating an inbox
│   └── api/                   # FastAPI app tying it all together
└── frontend/                  # React + Vite frontend application
```

## Setup and Installation

### Backend
1. Make sure you have `uv` installed.
2. Navigate to the `backend` directory and sync dependencies:
   ```bash
   cd backend
   uv sync
   ```

### Frontend
1. Navigate to the `frontend` directory.
2. Install dependencies and start the development server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
