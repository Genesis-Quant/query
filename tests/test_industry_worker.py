from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest

from query.manage.workers import build_parser, create_workers
from query.workers.industry import (
    INDUSTRY_FACTORS,
    IndustryLevel0,
    IndustryWorker,
)
from query.workers.registry import normalize_worker_names


def membership(
        code: str,
        *,
        l1_code: str,
        l2_code: str,
        l3_code: str,
        in_date: str,
        out_date: str | None,
        is_new: str,
) -> dict[str, object]:
    return {
        "ts_code": code,
        "l1_code": l1_code,
        "l1_name": "一级",
        "l2_code": l2_code,
        "l2_name": "二级",
        "l3_code": l3_code,
        "l3_name": "三级",
        "in_date": in_date,
        "out_date": out_date,
        "is_new": is_new,
    }


@pytest.fixture
def memberships() -> pd.DataFrame:
    return pd.DataFrame([
        membership(
            "000037.SZ",
            l1_code="801160.SI",
            l2_code="801161.SI",
            l3_code="851614.SI",
            in_date="19940701",
            out_date="20220728",
            is_new="N",
        ),
        membership(
            "000037.SZ",
            l1_code="801160.SI",
            l2_code="801161.SI",
            l3_code="851611.SI",
            in_date="20220729",
            out_date=None,
            is_new="Y",
        ),
        membership(
            "600519.SH",
            l1_code="801120.SI",
            l2_code="801125.SI",
            l3_code="851251.SI",
            in_date="20010731",
            out_date=None,
            is_new="Y",
        ),
    ])


def wide_events(result: pd.DataFrame) -> pd.DataFrame:
    return (
        result.pivot(
            index=["time", "code"],
            columns="factor",
            values="value",
        )
        .reset_index()
        .rename_axis(columns=None)
        .sort_values(["time", "code"])
        .reset_index(drop=True)
    )


def test_transform_memberships_creates_initial_snapshot_and_changes(
        memberships: pd.DataFrame,
) -> None:
    worker = IndustryWorker(
        start_date="2022-07-27",
        end_date="2022-07-30",
        overwrite=True,
    )

    result = wide_events(worker.transform_memberships(memberships))

    initial_utility = result[
        result["time"].eq(pd.Timestamp("2022-07-27"))
        & result["code"].eq("000037.SZ")
    ].iloc[0]
    assert initial_utility["industry_l0"] == IndustryLevel0.UTILITIES
    assert initial_utility["industry_l1"] == 801160
    assert initial_utility["industry_l2"] == 801161
    assert initial_utility["industry_l3"] == 851614

    initial_staples = result[
        result["time"].eq(pd.Timestamp("2022-07-27"))
        & result["code"].eq("600519.SH")
    ].iloc[0]
    assert initial_staples["industry_l0"] == IndustryLevel0.CONSUMER_STAPLES
    assert initial_staples["industry_l1"] == 801120

    transition = result[
        result["time"].eq(pd.Timestamp("2022-07-29"))
        & result["code"].eq("000037.SZ")
    ].iloc[0]
    assert transition["industry_l0"] == IndustryLevel0.UTILITIES
    assert transition["industry_l3"] == 851611
    assert not (
        result["time"].eq(pd.Timestamp("2022-07-29"))
        & result["code"].eq("600519.SH")
    ).any()


def test_transform_memberships_writes_unknown_after_unreplaced_out_date() -> None:
    worker = IndustryWorker(
        start_date="2022-07-27",
        end_date="2022-07-30",
        overwrite=True,
    )
    data = pd.DataFrame([
        membership(
            "000037.SZ",
            l1_code="801160.SI",
            l2_code="801161.SI",
            l3_code="851614.SI",
            in_date="19940701",
            out_date="20220728",
            is_new="N",
        )
    ])

    result = wide_events(worker.transform_memberships(data))
    reset = result[result["time"].eq(pd.Timestamp("2022-07-29"))].iloc[0]

    assert reset[list(INDUSTRY_FACTORS)].eq(IndustryLevel0.UNKNOWN).all()


def test_transform_memberships_rejects_unmapped_level_one() -> None:
    worker = IndustryWorker(
        start_date="2022-01-01",
        end_date="2022-12-31",
        overwrite=True,
    )
    data = pd.DataFrame([
        membership(
            "000001.SZ",
            l1_code="899999.SI",
            l2_code="801783.SI",
            l3_code="857831.SI",
            in_date="20220101",
            out_date=None,
            is_new="Y",
        )
    ])

    with pytest.raises(ValueError, match="未映射的申万一级行业"):
        worker.transform_memberships(data)


def test_stateless_increment_replays_database_watermark(
        memberships: pd.DataFrame,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    def configure(worker: IndustryWorker) -> None:
        monkeypatch.setattr(
            worker,
            "get_last_date",
            lambda: pd.Timestamp("2022-07-29"),
        )
        monkeypatch.setattr(
            worker,
            "fetch_memberships",
            lambda: memberships.copy(),
        )

    first = IndustryWorker(
        start_date="2022-07-27",
        end_date="2022-07-30",
    )
    second = IndustryWorker(
        start_date="2022-07-27",
        end_date="2022-07-30",
    )
    configure(first)
    configure(second)

    first_result = pd.concat(list(first.fetch_all()), ignore_index=True)
    second_result = pd.concat(list(second.fetch_all()), ignore_index=True)

    pd.testing.assert_frame_equal(first_result, second_result)
    assert first_result["time"].min() == pd.Timestamp("2022-07-29")
    assert set(first_result["factor"]) == set(INDUSTRY_FACTORS)


@pytest.mark.parametrize(
    ("factor_dates", "expected"),
    [
        (
            [
                ("industry_l0", "2024-08-01"),
                ("industry_l1", "2024-08-02"),
                ("industry_l2", "2024-08-03"),
                ("industry_l3", "2024-08-04"),
            ],
            pd.Timestamp("2024-08-01"),
        ),
        (
            [
                ("industry_l0", "2024-08-01"),
                ("industry_l1", "2024-08-01"),
                ("industry_l2", "2024-08-01"),
            ],
            None,
        ),
    ],
)
def test_incremental_watermark_comes_only_from_core_data(
        factor_dates: list[tuple[str, str]],
        expected: pd.Timestamp | None,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    session.run.return_value = pd.DataFrame({
        "factor": [factor for factor, _ in factor_dates],
        "time": pd.to_datetime([date for _, date in factor_dates]),
    })
    monkeypatch.setattr(
        "query.workers.industry.create_session",
        lambda **kwargs: session,
    )
    worker = IndustryWorker(
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    assert worker.get_last_date() == expected
    assert session.upload.call_args.args[0][
        "industryWorkerFactors"
    ].tolist() == list(INDUSTRY_FACTORS)
    session.close.assert_called_once_with()


def test_worker_is_registered() -> None:
    assert normalize_worker_names(["IndustryWorker"]) == ("industry",)
    arguments = build_parser().parse_args([
        "industry",
        "--start-date",
        "2022-01-01",
        "--end-date",
        "2022-12-31",
        "--overwrite",
    ])

    workers = create_workers(("industry",), arguments)

    assert len(workers) == 1
    assert isinstance(workers[0], IndustryWorker)
