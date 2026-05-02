from dataclasses import dataclass


@dataclass
class GenerationResult:
    mermaid_code: str
    diagram_type: str
    model_used: str
