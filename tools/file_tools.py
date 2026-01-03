# tools/file_tools.py
from tools.base import BaseTool


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file given a path"

    def run(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file at a given path"

    def run(self, path: str, content: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "File written successfully"
