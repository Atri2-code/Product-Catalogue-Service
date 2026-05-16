"""
experiments/ab_router.py

Deterministic A/B experiment assignment.
Uses a hash of (user_id + experiment_name) to assign users to buckets.
Same user always gets the same bucket for the same experiment — no re-randomisation.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ExperimentConfig:
    name: str
    variants: List[str]           # e.g. ["control", "treatment"]
    traffic_split: List[float]    # must sum to 1.0, e.g. [0.5, 0.5]
    description: str = ""


# Active experiments registry
EXPERIMENTS: Dict[str, ExperimentConfig] = {
    "ranking_v2": ExperimentConfig(
        name="ranking_v2",
        variants=["control", "bm25_rerank"],
        traffic_split=[0.5, 0.5],
        description="Test BM25 re-ranking vs default sort on search results",
    ),
    "price_sort_default": ExperimentConfig(
        name="price_sort_default",
        variants=["control", "price_asc"],
        traffic_split=[0.7, 0.3],
        description="Test price-ascending default sort for new users",
    ),
}


def assign(user_id: str, experiment: str) -> Optional[dict]:
    """
    Assign a user to an experiment variant.

    Args:
        user_id:    Unique user identifier
        experiment: Experiment name

    Returns:
        {"experiment": str, "bucket": str, "variant": str} or None if experiment unknown
    """
    config = EXPERIMENTS.get(experiment)
    if not config:
        return None

    # Deterministic hash — same user always gets same bucket
    key = f"{user_id}:{experiment}"
    hash_int = int(hashlib.md5(key.encode()).hexdigest(), 16)
    bucket_float = (hash_int % 10000) / 10000.0  # 0.0 to 1.0

    # Map to variant
    cumulative = 0.0
    for variant, split in zip(config.variants, config.traffic_split):
        cumulative += split
        if bucket_float < cumulative:
            return {
                "experiment": experiment,
                "bucket": "treatment" if variant != "control" else "control",
                "variant": variant,
            }

    # Fallback to last variant
    return {
        "experiment": experiment,
        "bucket": "treatment",
        "variant": config.variants[-1],
    }


def list_experiments() -> List[dict]:
    return [
        {
            "name": cfg.name,
            "variants": cfg.variants,
            "traffic_split": cfg.traffic_split,
            "description": cfg.description,
        }
        for cfg in EXPERIMENTS.values()
    ]
