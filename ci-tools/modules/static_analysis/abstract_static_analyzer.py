from abc import ABC, abstractmethod
from typing import Optional


class AbstractStaticAnalyzer(ABC):
    @abstractmethod
    def execute(self, target_files: list[str], report_file: str) -> dict:  # pragma: no cover
        pass

    def summarize(self, analysis_output: dict) -> Optional[str]:  # pragma: no cover
        """
        MR 全体に対するまとめコメントを返す。
        デフォルトは None なので、コメントなし。
        """
        return None
