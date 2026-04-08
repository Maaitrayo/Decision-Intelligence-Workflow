from pipeline.agents.analyst_agent import AnalystAgent
from pipeline.agents.critic_agent import CriticAgent
from pipeline.ingestion.service import IngestionService
from pipeline.models import RunResult
from pipeline.scoring.service import ScoringService
from pipeline.synthesis.synthesiser import Synthesiser


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.ingestion_service = IngestionService()
        self.scoring_service = ScoringService()
        self.analyst_agent = AnalystAgent()
        self.critic_agent = CriticAgent()
        self.synthesiser = Synthesiser()

    async def run(self, eval_mode: bool = False) -> RunResult:
        raw_items = await self.ingestion_service.fetch_all()
        scored_items = self.scoring_service.score(raw_items)
        analyst_output = await self.analyst_agent.run(scored_items)
        critic_output = await self.critic_agent.run(analyst_output, scored_items)
        return self.synthesiser.merge(analyst_output, critic_output, scored_items)
