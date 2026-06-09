from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def readcv(file_path: str) -> str:
    """
    Read, parse, and extract structural information from a candidate's CV/Resume file.
    Use this tool to screen applicants, summarize their work history, analyze education, and understand their technical skills.
    
    Args:
        file_path: The absolute path to the candidate's CV/Resume file (e.g. PDF, Word, or text format).
    """
    return await call_mcp_tool("readcv", {"file_path": file_path})
