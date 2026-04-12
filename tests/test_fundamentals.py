from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.fundamentals.csv_provider import CsvFundamentalsProvider
from app.fundamentals.engine import CompositeScoreWeights, combine_scores, score_fundamentals
from app.scoring.engine import score_breakout_setup
from app.signals.breakout import combine_latest_signals


def test_csv_fundamentals_provider_reads_requested_symbols(tmp_path: Path) -> None:
    csv_path = tmp_path / "fundamentals.csv"
    csv_path.write_text(
        "\n".join(
            [
                "symbol,sector,market_cap_bucket,revenue_growth_pct,eps_growth_pct,roe_pct,roce_pct,debt_to_equity,net_margin_pct,promoter_holding_pct",
                "RELIANCE,Energy,mega_cap,10,12,9,11,0.4,8,50",
                "TCS,Technology,mega_cap,8,10,40,50,0.0,20,72",
            ],
        ),
        encoding="utf-8",
    )

    provider = CsvFundamentalsProvider(csv_path)
    frame = provider.get_fundamentals(["TCS"])
    assert list(frame["symbol"]) == ["TCS"]
    assert frame.iloc[0]["sector"] == "Technology"


def test_score_fundamentals_returns_bucketed_score() -> None:
    snapshot = {
        "symbol": "TCS",
        "market_cap_bucket": "mega_cap",
        "revenue_growth_pct": 9.0,
        "eps_growth_pct": 12.0,
        "roe_pct": 35.0,
        "roce_pct": 42.0,
        "debt_to_equity": 0.02,
        "net_margin_pct": 20.0,
        "promoter_holding_pct": 72.0,
    }
    result = score_fundamentals(snapshot)
    assert 0 <= result.total_score <= 100
    assert result.rating in {"A", "B", "C", "Reject"}
    assert set(result.component_scores) == {
        "growth_quality",
        "return_ratios",
        "balance_sheet",
        "profitability",
        "ownership_quality",
        "scale_quality",
    }


def test_combine_scores_uses_both_technical_and_fundamental_inputs(breakout_stock_df, benchmark_df) -> None:
    combined = combine_latest_signals("RELIANCE", breakout_stock_df, benchmark_df)
    technical = score_breakout_setup(combined)
    fundamental = score_fundamentals(
        {
            "symbol": "RELIANCE",
            "market_cap_bucket": "mega_cap",
            "revenue_growth_pct": 8.0,
            "eps_growth_pct": 10.0,
            "roe_pct": 12.0,
            "roce_pct": 14.0,
            "debt_to_equity": 0.4,
            "net_margin_pct": 9.0,
            "promoter_holding_pct": 50.0,
        },
    )
    composite = combine_scores(technical, fundamental, weights=CompositeScoreWeights(technical=0.6, fundamental=0.4))

    assert composite.total_score > 0
    assert composite.technical_score == technical.total_score
    assert composite.fundamental_score == fundamental.total_score
