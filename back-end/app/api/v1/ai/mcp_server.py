import json
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
        "name": "list_student_documents",
        "description": "List private PDF/text documents indexed in PostgreSQL pgvector RAG for a specific student and optional chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer", "description": "Owner student ID"},
                "chat_id": {"type": "string", "description": "Optional MongoDB chat ID filter"},
                "subject": {"type": "string", "description": "Optional subject filter"}
            },
            "required": ["student_id"]
        }
    },
    {
        "name": "query_subject_knowledge",
        "description": "Perform PostgreSQL pgvector similarity search across a student's private uploaded PDF materials.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search question or keywords"},
                "student_id": {"type": "integer", "description": "Owner student ID"},
                "chat_id": {"type": "string", "description": "Optional MongoDB chat ID filter"},
                "subject": {"type": "string", "description": "Optional subject filter"}
            },
            "required": ["query", "student_id"]
        }
    },
    {
        "name": "add_knowledge",
        "description": "Add a new private knowledge note to PostgreSQL pgvector RAG for a specific student.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer", "description": "Owner student ID"},
                "title": {"type": "string", "description": "Document/note title"},
                "content": {"type": "string", "description": "Note content"},
                "chat_id": {"type": "string", "description": "Optional chat ID (defaults to 'default')"},
                "subject": {"type": "string", "description": "Optional subject title"}
            },
            "required": ["student_id", "title", "content"]
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
        elif tool_name == "list_student_documents":
            student_id = arguments.get("student_id")
            if student_id is None:
                result_data = {"error": "student_id is required"}
            else:
                result_data = rag_store.list_documents(
                    subject=arguments.get("subject"),
                    student_id=int(student_id),
                    chat_id=arguments.get("chat_id"),
                )
        elif tool_name == "query_subject_knowledge":
            student_id = arguments.get("student_id")
            if student_id is None:
                result_data = {"error": "student_id is required"}
            else:
                result_data = tool_query_subject_knowledge(
                    query=arguments.get("query", ""),
                    subject=arguments.get("subject"),
                    student_id=int(student_id),
                    chat_id=arguments.get("chat_id"),
                )
        elif tool_name == "add_knowledge":
            student_id = arguments.get("student_id")
            result_data = tool_add_knowledge(
                subject=arguments.get("subject", ""),
                title=arguments.get("title", "Note"),
                content=arguments.get("content", ""),
                student_id=int(student_id) if student_id is not None else None,
                chat_id=arguments.get("chat_id", "default"),
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
                        "text": json.dumps(result_data, ensure_ascii=False)
                    }
                ]
            }
        }

    elif method == "resources/list":
        student_id = params.get("student_id")
        chat_id = params.get("chat_id")
        docs = (
            rag_store.list_documents(student_id=int(student_id), chat_id=chat_id)
            if student_id is not None
            else []
        )
        resources = [
            {
                "uri": f"cms://rag/{student_id}/{d['chat_id']}/{d['filename']}",
                "name": f"{d['filename']}" + (f" ({d['subject']})" if d.get("subject") else ""),
                "description": f"Indexed material ({d['chunks_count']} chunks)"
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
                    "version": "1.1.0"
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
