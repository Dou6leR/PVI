from typing import Any
from sqlmodel import Session
from api.v1.ai.tools import (
    tool_search_students,
    tool_get_group_students,
    tool_get_system_stats,
    tool_query_subject_knowledge,
    tool_add_knowledge
)
from api.v1.ai.rag import rag_store
from core.logger import logger


MCP_TOOLS = [
    {
        "name": "search_students",
        "description": "Search students in the CMS PostgreSQL database by first name, last name, or group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_or_query": {"type": "string", "description": "Student name or group to search"}
            },
            "required": ["name_or_query"]
        }
    },
    {
        "name": "get_group_students",
        "description": "Get the list of all students belonging to a specified university group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group": {"type": "string", "description": "Group name, e.g. PZ-22"}
            },
            "required": ["group"]
        }
    },
    {
        "name": "get_system_stats",
        "description": "Get system statistics: total students, active students, and group distribution.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "query_subject_knowledge",
        "description": "Perform RAG vector similarity search across uploaded PDF materials and course guidelines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search question or keywords"},
                "subject": {"type": "string", "description": "Course/subject filter, e.g. ПВІ"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_knowledge",
        "description": "Add a new knowledge note or rule to the RAG vector store.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject title"},
                "title": {"type": "string", "description": "Document/rule title"},
                "content": {"type": "string", "description": "Rule content"}
            },
            "required": ["subject", "title", "content"]
        }
    }
]


def handle_mcp_request(payload: dict, session: Session) -> dict:
    """
    Handles JSON-RPC 2.0 requests following the Model Context Protocol specification.
    """
    req_id = payload.get("id", 1)
    method = payload.get("method", "")
    params = payload.get("params", {})

    logger.info(f"Handling MCP request: method={method}")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result_data: Any = None
        if tool_name == "search_students":
            result_data = tool_search_students(arguments.get("name_or_query", ""), session)
        elif tool_name == "get_group_students":
            result_data = tool_get_group_students(arguments.get("group", ""), session)
        elif tool_name == "get_system_stats":
            result_data = tool_get_system_stats(session)
        elif tool_name == "query_subject_knowledge":
            result_data = tool_query_subject_knowledge(arguments.get("query", ""), arguments.get("subject"))
        elif tool_name == "add_knowledge":
            result_data = tool_add_knowledge(
                arguments.get("subject", "Загальний"),
                arguments.get("title", "Note"),
                arguments.get("content", "")
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method/Tool '{tool_name}' not found"
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": str(result_data)
                    }
                ]
            }
        }

    elif method == "resources/list":
        docs = rag_store.list_documents()
        resources = [
            {
                "uri": f"cms://rag/{d['subject']}/{d['filename']}",
                "name": f"{d['filename']} ({d['subject']})",
                "description": f"Indexed course materials ({d['chunks_count']} chunks)"
            }
            for d in docs
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": resources
            }
        }

    # Ping / initialize
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "cms-mcp-server",
                    "version": "1.0.0"
                }
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not supported"
        }
    }
