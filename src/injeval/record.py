from dataclasses import asdict, dataclass
import json


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    timestamp: str
    model: str
    position: str
    framing: str
    dilution: int
    task_id: str
    injection_id: str
    seed: int
    temperature: float
    arm: str
    prompt: str
    final_answer: str
    tool_calls: list[dict]
    benign_hits: list[dict]
    attacker_hits: list[dict]
    steps_used: int
    wall_clock_s: float
    parse_failed: bool
    parse_retries: int = 0
    run_error: str | None = None

    def __post_init__(self) -> None:
        if self.arm not in {"main", "baseline", "pilot", "defense", "defense_control"}:
            raise ValueError(f"Unknown arm: {self.arm!r}")

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "RunRecord":
        return cls(**json.loads(s))
