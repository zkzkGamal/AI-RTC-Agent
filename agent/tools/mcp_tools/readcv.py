"""agent.tools.mcp_tools.readcv module."""

from langchain_core.tools import tool
from core.content_store import read_document, resolve_path


@tool
async def readcv(file_path: str = "") -> str:
    """
    Read, parse, and extract the full text of a candidate's CV/Resume so it can be
    screened, summarized, and analyzed (work history, education, technical skills).

    Only PDF, Word (.docx), and Markdown/text files are supported. Files live in the
    global `content/` folder at the project root — uploaded CVs are saved there, and
    you can refer to a CV by its file name (e.g. "cv.pdf") or leave `file_path` empty
    to read the most recently uploaded CV.

    Args:
        file_path: Name of the CV inside the content/ folder (or an absolute path).
                   Leave empty to read the most recent CV.
    """
    try:
        text = read_document(file_path)
    except FileNotFoundError:
        return (
            "No CV found. Ask the candidate to upload a PDF, Word, or Markdown CV "
            "(it is saved into the content/ folder), then try again."
        )
    except ValueError as e:
        return f"Could not read CV: {e}"
    except Exception as e:
        return f"Error reading CV: {e}"

    resolved = resolve_path(file_path)
    name = resolved.name if resolved is not None else (file_path or "CV")
    return f"CV file: {name}\n\n{text}"
