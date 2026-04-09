from pipeline.models import RawItem


SOURCE_CREDIBILITY_WEIGHTS = {
    "hacker_news": 0.9,
    "arxiv": 1.0,
    "github_trending": 0.85,
}


def get_source_weight(item: RawItem) -> float:
    return SOURCE_CREDIBILITY_WEIGHTS.get(item.source, 1.0)
