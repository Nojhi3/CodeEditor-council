# tools/registry.py
from tools.file_tools import ReadFileTool, WriteFileTool

TOOLS = {
    "read_file": ReadFileTool(),
    "write_file": WriteFileTool(),
}
