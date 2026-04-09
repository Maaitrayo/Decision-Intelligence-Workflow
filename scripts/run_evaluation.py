import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.orchestrator import PipelineOrchestrator


async def main() -> None:
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run(eval_mode=True)

    assets_dir = PROJECT_ROOT / "assets"
    assets_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = assets_dir / f"evaluation_{timestamp}.json"
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    print(f"Saved evaluation result to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
