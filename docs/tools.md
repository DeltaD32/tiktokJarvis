---
title: Tools
nav_order: 4
---

# Tool Registry

48 tools across 19 modules. Each tool is a self-contained function decorated with `@register(...)`.

## Adding a New Tool

1. Create a new file in `dela/tools/` (or add to an existing one).
2. Import `register` from `dela.tools`.
3. Decorate your function:

```python
from dela.tools import register

@register(
    name="my_tool",
    description="Clear, one-line description of WHEN to use this (for the model, not a compiler).",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "What this input means."},
        },
        "required": ["input"],
    },
    requires_confirmation=False,  # True if it sends/spends/deletes/changes
)
def my_tool(args: dict) -> str:
    return f"Done: {args['input']}"
```

4. Add the import to `dela/tools/__init__.py`.
5. That's it. The brain picks it up automatically.

## Tool Design Rules

- **Describe tools for a reader, not a compiler.**
- **Typed, named inputs.** JSON-schema with `type` and `description` on every parameter.
- **Return errors as strings.** Never raise — return the error so the model can reason over it.
- **Flag consequential tools.** `requires_confirmation=True` for anything that sends, spends, deletes, or changes.

---

## Complete Tool Reference

### Core Tools

| Tool | Module | Confirmation |
|---|---|---|
| `list_tasks` | project | No |
| `add_task` | project | Yes |
| `complete_task` | project | Yes |
| `fetch_url` | research | No |
| `check_host` | systems | No |
| `remember_fact` | memory | Yes |
| `update_fact` | memory | Yes |
| `forget_fact` | memory | Yes |
| `list_notices` | heartbeat_tools | No |
| `dismiss_notice` | heartbeat_tools | Yes |
| `show_panel` | ui_tools | No |
| `dispatch_subagent` | subagent | No |
| `dispatch_system_expert` | subagent | No |
| `load_skill` | skills | No |
| `list_skills` | skills | No |
| `run_code` | code_exec | Yes |
| `analyze_external_repo` | repo_analysis | No |

### Presentation Tools

| Tool | Module | Confirmation |
|---|---|---|
| `clone_pptx_style` | presentation | Yes |
| `list_ppt_styles` | presentation | No |
| `generate_presentation` | presentation | Yes |

### Project Management (Blackboard) Tools

| Tool | Module | Confirmation |
|---|---|---|
| `create_project` | project_mgmt | Yes |
| `create_blackboard` | project_mgmt | Yes |
| `dispatch_to_blackboard` | project_mgmt | No |
| `set_execution_plan` | project_mgmt | Yes |
| `advance_queue` | project_mgmt | No |
| `resolve_conflict` | project_mgmt | Yes |
| `get_blackboard_status` | project_mgmt | No |
| `get_project_status` | project_mgmt | No |
| `approve_blackboard` | project_mgmt | Yes |

### Workflow Tools

| Tool | Module | Confirmation |
|---|---|---|
| `design_workflow` | workflow_tools | No |
| `save_workflow` | workflow_tools | Yes |
| `list_workflows` | workflow_tools | No |
| `get_workflow` | workflow_tools | No |
| `run_workflow` | workflow_tools | Yes |
| `delete_workflow` | workflow_tools | Yes |

### Agent Memory Tools

| Tool | Module | Confirmation |
|---|---|---|
| `recall_agent_memory` | agent_memory_tools | No |
| `record_agent_learning` | agent_memory_tools | Yes |
| `get_agent_memory_status` | agent_memory_tools | No |

### State Browser Tools

| Tool | Module | Confirmation |
|---|---|---|
| `search_state` | state_browser_tools | No |
| `list_state_types` | state_browser_tools | No |
| `read_state` | state_browser_tools | No |

### Security Tools

| Tool | Module | Confirmation |
|---|---|---|
| `run_security_scan` | security_tools | No |
| `get_security_status` | security_tools | No |
| `refresh_vuln_kb` | security_tools | No |

### Routing Cache Tools

| Tool | Module | Confirmation |
|---|---|---|
| `check_routing_cache` | routing_cache_tools | No |
| `routing_cache_status` | routing_cache_tools | No |

### DAG Scheduler Tools

| Tool | Module | Confirmation |
|---|---|---|
| `run_dag` | dag_tools | Yes |

### Status Events Tools

| Tool | Module | Confirmation |
|---|---|---|
| `get_timeline` | status_events_tools | No |

### MCP Tools

MCP server tools are dynamically loaded from configured MCP servers. They appear in the registry as `<server>__<tool_name>` and respect the same confirmation gate. See `mcp_config.json` for configuration.
