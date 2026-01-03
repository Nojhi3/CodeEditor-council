# tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs) -> Any:
        pass
