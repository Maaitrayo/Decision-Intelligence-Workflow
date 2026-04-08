from pipeline.models import RunResult


class PipelineOrchestrator:
    async def run(self, eval_mode: bool = False) -> RunResult:
        raise NotImplementedError("Pipeline orchestration is not implemented yet.")
