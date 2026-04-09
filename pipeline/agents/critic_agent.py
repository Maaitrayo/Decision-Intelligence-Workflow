from pipeline.agents.base_agent import BaseAgent
from pipeline.models import AgentOutput, ContradictionRecord, ScoredItem


class CriticAgent(BaseAgent):
    async def run(self, analyst_output: AgentOutput, items: list[ScoredItem]) -> AgentOutput:
        payload = await self.generate_json(
            system_prompt=(
                "You are the Critic agent in a decision intelligence workflow. "
                "Challenge the analyst's proposed signals, identify contested signals, "
                "endorse strong ones, and surface contradictions from the broader scored set. "
                "Return strict JSON with keys: contested_signals, contradictions, endorsements, reasoning. "
                "Each contradiction must contain signal_a, signal_b, description."
            ),
            user_prompt=(
                "Analyst output:\n"
                f"{analyst_output.model_dump_json(indent=2)}\n\n"
                "Scored items:\n"
                f"{self.build_context(items)}"
            ),
        )

        contradictions = [
            ContradictionRecord(
                signal_a=entry.get("signal_a", ""),
                signal_b=entry.get("signal_b", ""),
                description=entry.get("description", ""),
            )
            for entry in payload.get("contradictions", [])
            if entry.get("signal_a") and entry.get("signal_b")
        ]

        return AgentOutput(
            contested_signals=[item for item in payload.get("contested_signals", []) if isinstance(item, str)],
            contradictions=contradictions,
            endorsements=[item for item in payload.get("endorsements", []) if isinstance(item, str)],
            reasoning=str(payload.get("reasoning", "")),
        )
