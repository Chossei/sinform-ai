"""
Módulo de Estimativa e Auditoria de Custos de API do Google Gemini
Preços oficiais por milhão de tokens (USD):
- Gemini 3.5 Flash Lite: Input $0.075 / 1M, Output $0.30 / 1M
- Gemini 3.1 Flash Lite: Input $0.075 / 1M, Output $0.30 / 1M
- Gemini Embedding 2 (models/gemini-embedding-2): Input $0.02 / 1M
"""

from typing import Dict, Any, Optional

PRICING_PER_MILLION = {
    # Gemini 3.5 Flash Lite
    "gemini-3.5-flash-lite": {"input": 0.075, "output": 0.30},
    "models/gemini-3.5-flash-lite": {"input": 0.075, "output": 0.30},
    # Gemini 3.1 Flash Lite
    "gemini-3.1-flash-lite": {"input": 0.075, "output": 0.30},
    "models/gemini-3.1-flash-lite": {"input": 0.075, "output": 0.30},
    # Gemini 2.5 Flash / Fallback adicional
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "models/gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    # Embeddings
    "gemini-embedding-2": {"input": 0.02, "output": 0.0},
    "models/gemini-embedding-2": {"input": 0.02, "output": 0.0},
}

class CostEstimator:
    @staticmethod
    def calculate_cost(model_name: str, input_tokens: int, output_tokens: int = 0) -> float:
        clean_model = model_name.replace("models/", "")
        pricing = PRICING_PER_MILLION.get(model_name) or PRICING_PER_MILLION.get(clean_model, {"input": 0.075, "output": 0.30})
        
        input_cost = (input_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (output_tokens / 1_000_000.0) * pricing["output"]
        return input_cost + output_cost

    @staticmethod
    def format_cost(cost_usd: float) -> str:
        if cost_usd < 0.0001:
            return f"${cost_usd:.6f} USD"
        return f"${cost_usd:.4f} USD"

class SessionCostTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.operations_log = []

    def record_operation(
        self,
        operation_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int = 0,
        extra_info: Optional[Dict[str, Any]] = None
    ) -> float:
        cost = CostEstimator.calculate_cost(model_name, input_tokens, output_tokens)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        
        entry = {
            "operation": operation_name,
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "extra_info": extra_info or {}
        }
        self.operations_log.append(entry)
        return cost

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "formatted_cost": CostEstimator.format_cost(self.total_cost_usd),
            "operations_count": len(self.operations_log)
        }
