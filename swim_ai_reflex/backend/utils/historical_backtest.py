"""
Historical Backtest Module

Loads historical meet data from SQLite DB, scores seed times (prediction)
vs finals times (actual), optionally runs optimizer, and compares results.

Key design:
  - PROJECTED scores use seed_time (what you'd know before the meet)
  - ACTUAL scores use finals_time (what really happened)
  - Scoring rules auto-selected: VISAADualRules vs VISAAChampRules

NOTE: Requires persistence.database, persistence.db_models, core.optimizer_factory,
core.scoring, core.rules -- all should exist on Mac. Also references
core.championship_strategy which may be at strategies/championship_strategy.py on Mac.
"""

import asyncio

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from swim_ai_reflex.backend.core.optimizer_factory import OptimizerFactory
from swim_ai_reflex.backend.core.rules import VISAAChampRules, VISAADualRules
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.persistence.database import engine
from swim_ai_reflex.backend.persistence.db_models import Meet, Team


def compute_team_seed_bias(team_id: int, before_date: str | None = None) -> dict:
    """Compute a team's historical seed-to-finals bias."""
    with Session(engine) as session:
        date_filter = "AND m.meet_date < :before_date" if before_date else ""
        params: dict = {"team_id": team_id}
        if before_date:
            params["before_date"] = before_date

        row = session.exec(
            text(f"""
            SELECT t.name,
                   count(en.id) as n,
                   avg(en.seed_time - en.finals_time) as avg_bias,
                   avg(abs(en.seed_time - en.finals_time)) as avg_abs_gap,
                   avg((en.seed_time - en.finals_time) / en.seed_time * 100) as avg_pct_bias
            FROM entries en
            JOIN events ev ON en.event_id = ev.id
            JOIN meets m ON ev.meet_id = m.id
            JOIN teams t ON en.team_id = t.id
            WHERE en.team_id = :team_id
              AND en.seed_time > 0 AND en.finals_time > 0
              AND en.is_dq = 0 AND ev.is_relay = 0
              AND abs(en.seed_time - en.finals_time) / en.seed_time < 0.5
              {date_filter}
            GROUP BY t.id
        """),
            params=params,
        ).first()

        if not row:
            return {
                "team_id": team_id,
                "n": 0,
                "avg_bias": 0.0,
                "avg_abs_gap": 0.0,
                "avg_pct_bias": 0.0,
                "by_event": {},
            }

        team_name, n, avg_bias, avg_abs_gap, avg_pct = row

        event_rows = session.exec(
            text(f"""
            SELECT ev.event_name,
                   count(en.id) as n,
                   avg(en.seed_time - en.finals_time) as avg_bias
            FROM entries en
            JOIN events ev ON en.event_id = ev.id
            JOIN meets m ON ev.meet_id = m.id
            WHERE en.team_id = :team_id
              AND en.seed_time > 0 AND en.finals_time > 0
              AND en.is_dq = 0 AND ev.is_relay = 0
              AND abs(en.seed_time - en.finals_time) / en.seed_time < 0.5
              {date_filter}
            GROUP BY ev.event_name
            HAVING n >= 5
        """),
            params=params,
        ).all()

        by_event = {}
        for evt_name, evt_n, evt_bias in event_rows:
            by_event[evt_name] = {"n": evt_n, "avg_bias": round(evt_bias, 3)}

    return {
        "team_id": team_id,
        "team_name": team_name,
        "n": n,
        "avg_bias": round(avg_bias, 3),
        "avg_abs_gap": round(avg_abs_gap, 3),
        "avg_pct_bias": round(avg_pct, 2),
        "by_event": by_event,
    }


def apply_bias_correction(
    df: pd.DataFrame,
    bias: dict,
    time_col: str = "time",
    min_n: int = 30,
) -> pd.DataFrame:
    """Adjust seed times by subtracting the team's historical bias."""
    if not bias or bias.get("n", 0) < min_n:
        return df

    df = df.copy()
    by_event = bias.get("by_event", {})
    team_avg = bias.get("avg_bias", 0.0)

    for idx, row in df.iterrows():
        event = row.get("event", "")
        event_bias = by_event.get(event, {}).get("avg_bias", team_avg)
        df.at[idx, time_col] = max(1.0, row[time_col] - event_bias)

    return df


def _get_rules(meet_type: str, scoring_type: str = "auto"):
    """Return appropriate scoring rules for the meet type."""
    if scoring_type == "auto":
        if meet_type == "championship":
            return VISAAChampRules()
        else:
            return VISAADualRules()
    elif scoring_type in ("visaa_champ", "champ"):
        return VISAAChampRules()
    else:
        return VISAADualRules()


def load_all_meet_entries(meet_id: int) -> tuple[pd.DataFrame, dict]:
    """Load ALL entries from ALL teams at a meet."""
    with Session(engine) as session:
        meet = session.get(Meet, meet_id)
        if not meet:
            raise ValueError(f"Meet {meet_id} not found")

        rows = session.exec(
            text("""
            SELECT s.first_name || ' ' || s.last_name as swimmer,
                   ev.event_name as event,
                   en.seed_time,
                   en.finals_time,
                   t.name as team_name,
                   en.team_id,
                   sts.grade
            FROM entries en
            JOIN events ev ON en.event_id = ev.id
            JOIN swimmers s ON en.swimmer_id = s.id
            JOIN teams t ON en.team_id = t.id
            LEFT JOIN swimmer_team_seasons sts ON sts.swimmer_id = s.id
                AND sts.team_id = en.team_id
                AND sts.season_id = :season_id
            WHERE ev.meet_id = :meet_id
              AND en.is_dq = 0
              AND en.is_exhibition = 0
              AND ev.is_relay = 0
              AND (en.seed_time IS NOT NULL OR en.finals_time IS NOT NULL)
            ORDER BY ev.event_number, en.seed_time
        """),
            params={
                "meet_id": meet_id,
                "season_id": meet.season_id or 0,
            },
        ).all()

        if not rows:
            return pd.DataFrame(), {"meet_id": meet_id, "meet_name": meet.name}

        records = []
        for swimmer, event, seed_time, finals_time, team_name, team_id, grade in rows:
            records.append(
                {
                    "swimmer": swimmer,
                    "event": event,
                    "seed_time": round(seed_time, 2)
                    if seed_time and seed_time > 0
                    else None,
                    "finals_time": round(finals_time, 2)
                    if finals_time and finals_time > 0
                    else None,
                    "team": team_name,
                    "team_id": team_id,
                    "grade": grade if grade else 10,
                }
            )

        df = pd.DataFrame(records)
        team_counts = df.groupby("team").size().sort_values(ascending=False)

        meet_info = {
            "meet_id": meet_id,
            "meet_name": meet.name,
            "meet_date": str(meet.meet_date),
            "meet_type": meet.meet_type,
            "total_entries": len(df),
            "total_teams": df["team_id"].nunique(),
            "total_swimmers": df["swimmer"].nunique(),
            "events": sorted(df["event"].unique()),
            "top_teams": [
                {"name": name, "entries": int(cnt)}
                for name, cnt in team_counts.head(10).items()
            ],
        }

    return df, meet_info


def _score_meet_multi_team(
    df: pd.DataFrame,
    rules,
    time_col: str = "time",
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Score a meet with multiple teams, preserving original team names."""
    if df.empty:
        return pd.DataFrame(), {}

    df = df.copy()
    if "is_relay" not in df.columns:
        df["is_relay"] = df["event"].str.lower().str.contains("relay", na=False)

    points_table = rules.individual_points
    relay_points = rules.relay_points
    max_scorers = rules.max_scorers_per_team_individual

    scored_parts = []
    for event_name, grp in df.groupby("event"):
        is_relay = grp["is_relay"].any()
        pts = relay_points if is_relay else points_table
        cur_max_scorers = 999 if is_relay else max_scorers

        grp = grp.sort_values(time_col, ascending=True).reset_index(drop=True)

        team_scorer_count: dict[str, int] = {}
        place = 0
        for idx, row in grp.iterrows():
            team = row["team"]
            scorer_count = team_scorer_count.get(team, 0)

            if scorer_count < cur_max_scorers:
                place += 1
                pt = pts[place - 1] if place <= len(pts) else 0
                team_scorer_count[team] = scorer_count + 1
            else:
                pt = 0

            grp.at[idx, "place"] = place if pt > 0 else 0
            grp.at[idx, "points"] = pt

        scored_parts.append(grp)

    if scored_parts:
        scored = pd.concat(scored_parts, ignore_index=True)
    else:
        scored = pd.DataFrame()

    team_totals: dict[str, float] = {}
    if not scored.empty:
        for team, team_df in scored.groupby("team"):
            team_totals[team] = float(team_df["points"].sum())

    return scored, team_totals


def load_meet_entries(
    meet_id: int, team_a_id: int, team_b_id: int
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Query DB for individual entries at a meet, split by team."""
    with Session(engine) as session:
        meet = session.get(Meet, meet_id)
        if not meet:
            raise ValueError(f"Meet {meet_id} not found")

        team_a = session.get(Team, team_a_id)
        team_b = session.get(Team, team_b_id)
        if not team_a or not team_b:
            raise ValueError(f"Team not found: {team_a_id} or {team_b_id}")

        meet_info = {
            "meet_id": meet_id,
            "meet_name": meet.name,
            "meet_date": str(meet.meet_date),
            "meet_type": meet.meet_type,
            "team_a": {"id": team_a.id, "name": team_a.name},
            "team_b": {"id": team_b.id, "name": team_b.name},
        }

        def _load_team(tid: int, team_label: str) -> pd.DataFrame:
            rows = session.exec(
                text("""
                SELECT s.first_name || ' ' || s.last_name as swimmer,
                       ev.event_name as event,
                       en.seed_time,
                       en.finals_time,
                       sts.grade
                FROM entries en
                JOIN events ev ON en.event_id = ev.id
                JOIN swimmers s ON en.swimmer_id = s.id
                LEFT JOIN swimmer_team_seasons sts ON sts.swimmer_id = s.id
                    AND sts.team_id = :team_id
                    AND sts.season_id = :season_id
                WHERE ev.meet_id = :meet_id
                  AND en.team_id = :team_id
                  AND en.is_dq = 0
                  AND en.is_exhibition = 0
                  AND ev.is_relay = 0
                  AND (en.seed_time IS NOT NULL OR en.finals_time IS NOT NULL)
                ORDER BY ev.event_number, en.finals_time
            """),
                params={
                    "meet_id": meet_id,
                    "team_id": tid,
                    "season_id": meet.season_id or 0,
                },
            ).all()

            if not rows:
                return pd.DataFrame(
                    columns=[
                        "swimmer",
                        "event",
                        "seed_time",
                        "finals_time",
                        "team",
                        "grade",
                    ]
                )

            records = []
            for swimmer, event, seed_time, finals_time, grade in rows:
                records.append(
                    {
                        "swimmer": swimmer,
                        "event": event,
                        "seed_time": round(seed_time, 2)
                        if seed_time and seed_time > 0
                        else None,
                        "finals_time": round(finals_time, 2)
                        if finals_time and finals_time > 0
                        else None,
                        "team": team_label,
                        "grade": grade if grade else 10,
                    }
                )
            return pd.DataFrame(records)

        team_a_df = _load_team(team_a_id, "seton")
        team_b_df = _load_team(team_b_id, "opponent")

        meet_info["team_a_entries"] = len(team_a_df)
        meet_info["team_b_entries"] = len(team_b_df)
        meet_info["team_a_seed_count"] = int(team_a_df["seed_time"].notna().sum())
        meet_info["team_b_seed_count"] = int(team_b_df["seed_time"].notna().sum())
        meet_info["team_a_finals_count"] = int(team_a_df["finals_time"].notna().sum())
        meet_info["team_b_finals_count"] = int(team_b_df["finals_time"].notna().sum())
        meet_info["events"] = sorted(
            set(list(team_a_df["event"].unique()) + list(team_b_df["event"].unique()))
        )

    return team_a_df, team_b_df, meet_info


def _prepare_for_scoring(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    """Prepare a DataFrame for full_meet_scoring."""
    out = df[df[time_col].notna()].copy()
    out["time"] = out[time_col]
    return out[["swimmer", "event", "time", "team", "grade"]].reset_index(drop=True)


def reduce_roster_for_optimizer(
    roster: pd.DataFrame,
    max_events_per_swimmer: int = 2,
    max_swimmers_per_event: int = 4,
) -> pd.DataFrame:
    """Reduce a full meet roster to optimizer-sized lineup."""
    if roster.empty:
        return roster

    roster = roster.copy()
    roster["rank_in_swimmer"] = roster.groupby("swimmer")["time"].rank(method="first")
    roster = roster[roster["rank_in_swimmer"] <= max_events_per_swimmer].copy()

    roster["rank_in_event"] = roster.groupby("event")["time"].rank(method="first")
    roster = roster[roster["rank_in_event"] <= max_swimmers_per_event].copy()

    roster.drop(columns=["rank_in_swimmer", "rank_in_event"], inplace=True)
    return roster.reset_index(drop=True)


def _df_to_details(scored_df: pd.DataFrame | None) -> list[dict]:
    """Convert a scored DataFrame to a list of dicts."""
    if scored_df is None or scored_df.empty:
        return []
    details = []
    for _, row in scored_df.iterrows():
        details.append(
            {
                "event": row.get("event", ""),
                "swimmer": row.get("swimmer", ""),
                "time": row.get("time", 0),
                "team": row.get("team", ""),
                "points": row.get("points", 0),
                "place": row.get("place", 0),
            }
        )
    return details


async def run_backtest(
    meet_id: int,
    team_a_id: int,
    team_b_id: int,
    optimizer: str = "heuristic",
    max_iters: int = 0,
    scoring_type: str = "auto",
    timeout_seconds: int = 120,
    bias_correct: bool = False,
) -> dict:
    """Full backtest workflow."""
    team_a_df, team_b_df, meet_info = load_meet_entries(meet_id, team_a_id, team_b_id)

    if team_a_df.empty:
        return {
            "success": False,
            "error": f"No entries found for team {meet_info['team_a']['name']} at this meet",
            "meet_info": meet_info,
        }
    if team_b_df.empty:
        return {
            "success": False,
            "error": f"No entries found for team {meet_info['team_b']['name']} at this meet",
            "meet_info": meet_info,
        }

    rules = _get_rules(meet_info["meet_type"], scoring_type)

    seed_a = _prepare_for_scoring(team_a_df, "seed_time")
    seed_b = _prepare_for_scoring(team_b_df, "seed_time")

    projected_score_a = 0.0
    projected_score_b = 0.0
    projected_scored = None

    if not seed_a.empty and not seed_b.empty:
        seed_combined = pd.concat([seed_a, seed_b], ignore_index=True)
        projected_scored, projected_totals = full_meet_scoring(
            seed_combined, rules=rules, validate=False
        )
        projected_score_a = projected_totals.get("seton", 0)
        projected_score_b = projected_totals.get("opponent", 0)
    else:
        finals_a = _prepare_for_scoring(team_a_df, "finals_time")
        finals_b = _prepare_for_scoring(team_b_df, "finals_time")
        if not finals_a.empty and not finals_b.empty:
            combined = pd.concat([finals_a, finals_b], ignore_index=True)
            projected_scored, projected_totals = full_meet_scoring(
                combined, rules=rules, validate=False
            )
            projected_score_a = projected_totals.get("seton", 0)
            projected_score_b = projected_totals.get("opponent", 0)

    bias_score_a = None
    bias_score_b = None
    bias_info: dict = {}

    if bias_correct and not seed_a.empty and not seed_b.empty:
        meet_date = meet_info.get("meet_date")
        bias_a = compute_team_seed_bias(team_a_id, before_date=meet_date)
        bias_b = compute_team_seed_bias(team_b_id, before_date=meet_date)
        bias_info = {
            "team_a_bias": bias_a.get("avg_bias", 0),
            "team_a_n": bias_a.get("n", 0),
            "team_b_bias": bias_b.get("avg_bias", 0),
            "team_b_n": bias_b.get("n", 0),
        }

        adjusted_a = apply_bias_correction(seed_a.copy(), bias_a)
        adjusted_b = apply_bias_correction(seed_b.copy(), bias_b)
        adj_combined = pd.concat([adjusted_a, adjusted_b], ignore_index=True)
        _, adj_totals = full_meet_scoring(adj_combined, rules=rules, validate=False)
        bias_score_a = adj_totals.get("seton", 0)
        bias_score_b = adj_totals.get("opponent", 0)

    finals_a = _prepare_for_scoring(team_a_df, "finals_time")
    finals_b = _prepare_for_scoring(team_b_df, "finals_time")

    actual_score_a = 0.0
    actual_score_b = 0.0
    actual_scored = None

    if not finals_a.empty and not finals_b.empty:
        finals_combined = pd.concat([finals_a, finals_b], ignore_index=True)
        actual_scored, actual_totals = full_meet_scoring(
            finals_combined, rules=rules, validate=False
        )
        actual_score_a = actual_totals.get("seton", 0)
        actual_score_b = actual_totals.get("opponent", 0)

    optimized_score_a = None
    optimized_score_b = None
    optimized_iterations = 0
    lineup_list: list[dict] = []
    optimizer_details: list[dict] = []

    if max_iters > 0 and not seed_a.empty and not seed_b.empty:
        seed_a_reduced = reduce_roster_for_optimizer(seed_a)
        seed_b_reduced = reduce_roster_for_optimizer(seed_b)

        def scoring_fn(df: pd.DataFrame):
            return full_meet_scoring(df, rules=rules, validate=False)

        try:
            strategy = OptimizerFactory.get_strategy(optimizer)
        except (ImportError, ModuleNotFoundError):
            strategy = OptimizerFactory.get_strategy("heuristic")

        try:
            best_lineup, best_scored, best_totals, history = await asyncio.wait_for(
                asyncio.to_thread(
                    strategy.optimize,
                    seton_roster=seed_a_reduced,
                    opponent_roster=seed_b_reduced,
                    scoring_fn=scoring_fn,
                    rules=rules,
                    max_iters=max_iters,
                    alpha=1.0,
                ),
                timeout=timeout_seconds,
            )
            optimized_score_a = best_totals.get("seton", 0) if best_totals else None
            optimized_score_b = best_totals.get("opponent", 0) if best_totals else None
            optimized_iterations = len(history) if history else max_iters

            if best_lineup is not None and not best_lineup.empty:
                for _, row in best_lineup.iterrows():
                    lineup_list.append(
                        {
                            "swimmer": row.get("swimmer", ""),
                            "event": row.get("event", ""),
                            "time": row.get("time", 0),
                        }
                    )
            optimizer_details = _df_to_details(best_scored)
        except (TimeoutError, Exception) as e:
            err_type = (
                "timed out" if isinstance(e, asyncio.TimeoutError) else f"failed: {e}"
            )
            print(f"  WARNING: Optimizer {err_type}. Using projected scores only.")

    event_comparison = _build_event_comparison(
        projected_scored, actual_scored, meet_info["events"]
    )

    result: dict = {
        "success": True,
        "meet_info": meet_info,
        "projected": {
            "team_a_score": projected_score_a,
            "team_b_score": projected_score_b,
            "source": "seed_time" if not seed_a.empty else "finals_time",
        },
        "predicted": {
            "team_a_score": optimized_score_a
            if optimized_score_a is not None
            else projected_score_a,
            "team_b_score": optimized_score_b
            if optimized_score_b is not None
            else projected_score_b,
            "optimizer": optimizer,
            "iterations": optimized_iterations,
        },
        "actual": {
            "team_a_score": float(actual_score_a),
            "team_b_score": float(actual_score_b),
        },
        "lineup": lineup_list,
        "details": optimizer_details
        if optimizer_details
        else _df_to_details(projected_scored),
        "actual_details": _df_to_details(actual_scored),
        "event_comparison": event_comparison,
    }

    if bias_correct and bias_score_a is not None:
        result["bias_corrected"] = {
            "team_a_score": bias_score_a,
            "team_b_score": bias_score_b,
            **bias_info,
        }

    return result


def _build_event_comparison(
    projected_scored: pd.DataFrame | None,
    actual_scored: pd.DataFrame | None,
    events: list[str],
) -> list[dict]:
    """Build event-by-event comparison between projected and actual scores."""
    comparison = []
    for event_name in events:
        entry: dict = {"event": event_name}

        if projected_scored is not None and not projected_scored.empty:
            evt_proj = projected_scored[projected_scored["event"] == event_name]
            entry["proj_a_points"] = (
                float(evt_proj.loc[evt_proj["team"] == "seton", "points"].sum())
                if not evt_proj.empty
                else 0
            )
            entry["proj_b_points"] = (
                float(evt_proj.loc[evt_proj["team"] == "opponent", "points"].sum())
                if not evt_proj.empty
                else 0
            )
        else:
            entry["proj_a_points"] = 0
            entry["proj_b_points"] = 0

        if actual_scored is not None and not actual_scored.empty:
            evt_act = actual_scored[actual_scored["event"] == event_name]
            entry["actual_a_points"] = (
                float(evt_act.loc[evt_act["team"] == "seton", "points"].sum())
                if not evt_act.empty
                else 0
            )
            entry["actual_b_points"] = (
                float(evt_act.loc[evt_act["team"] == "opponent", "points"].sum())
                if not evt_act.empty
                else 0
            )
            entry["actual_entries"] = len(evt_act)
        else:
            entry["actual_a_points"] = 0
            entry["actual_b_points"] = 0
            entry["actual_entries"] = 0

        comparison.append(entry)

    return comparison


async def run_championship_backtest(
    meet_id: int,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
    scoring_type: str = "auto",
) -> dict:
    """
    Backtest a championship meet using ALL teams for accurate scoring.

    Loads every entry at the meet, scores the full field with championship rules,
    then extracts scores for the teams of interest.

    If team_a_id/team_b_id are None, returns top 2 teams by total score.
    """
    all_df, meet_info = load_all_meet_entries(meet_id)
    if all_df.empty:
        return {"success": False, "error": "No entries found", "meet_info": meet_info}

    rules = _get_rules(meet_info.get("meet_type", "championship"), scoring_type)

    # PROJECTED: score by seed_time
    seed_df = all_df[all_df["seed_time"].notna()].copy()
    seed_df["time"] = seed_df["seed_time"]

    proj_scored, proj_totals = _score_meet_multi_team(seed_df, rules, time_col="time")

    # ACTUAL: score by finals_time
    finals_df = all_df[all_df["finals_time"].notna()].copy()
    finals_df["time"] = finals_df["finals_time"]

    actual_scored, actual_totals = _score_meet_multi_team(
        finals_df, rules, time_col="time"
    )

    # Find teams of interest
    if team_a_id and team_b_id:
        team_a_name = (
            all_df[all_df["team_id"] == team_a_id]["team"].iloc[0]
            if not all_df[all_df["team_id"] == team_a_id].empty
            else f"Team {team_a_id}"
        )
        team_b_name = (
            all_df[all_df["team_id"] == team_b_id]["team"].iloc[0]
            if not all_df[all_df["team_id"] == team_b_id].empty
            else f"Team {team_b_id}"
        )
    else:
        # Use top 2 teams by actual score
        sorted_actual = sorted(actual_totals.items(), key=lambda x: -x[1])
        if len(sorted_actual) < 2:
            return {
                "success": False,
                "error": "Fewer than 2 teams scored",
                "meet_info": meet_info,
            }
        team_a_name = sorted_actual[0][0]
        team_b_name = sorted_actual[1][0]

    proj_a = proj_totals.get(team_a_name, 0.0)
    proj_b = proj_totals.get(team_b_name, 0.0)
    actual_a = actual_totals.get(team_a_name, 0.0)
    actual_b = actual_totals.get(team_b_name, 0.0)

    # Build standings
    proj_standings = sorted(proj_totals.items(), key=lambda x: -x[1])
    actual_standings = sorted(actual_totals.items(), key=lambda x: -x[1])

    # Team A and B rank in standings
    proj_rank_a = next(
        (i + 1 for i, (t, _) in enumerate(proj_standings) if t == team_a_name), 0
    )
    proj_rank_b = next(
        (i + 1 for i, (t, _) in enumerate(proj_standings) if t == team_b_name), 0
    )
    actual_rank_a = next(
        (i + 1 for i, (t, _) in enumerate(actual_standings) if t == team_a_name), 0
    )
    actual_rank_b = next(
        (i + 1 for i, (t, _) in enumerate(actual_standings) if t == team_b_name), 0
    )

    return {
        "success": True,
        "meet_info": {
            **meet_info,
            "team_a": {"name": team_a_name},
            "team_b": {"name": team_b_name},
        },
        "projected": {
            "team_a_score": proj_a,
            "team_b_score": proj_b,
            "source": "seed_time",
            "team_a_rank": proj_rank_a,
            "team_b_rank": proj_rank_b,
            "total_teams": len(proj_totals),
        },
        "actual": {
            "team_a_score": actual_a,
            "team_b_score": actual_b,
            "team_a_rank": actual_rank_a,
            "team_b_rank": actual_rank_b,
            "total_teams": len(actual_totals),
        },
        "projected_standings": proj_standings[:10],
        "actual_standings": actual_standings[:10],
        "event_comparison": [],  # Could build per-event later
    }


async def run_batch_backtest(
    min_entries: int = 30,
    meet_types: list[str] | None = None,
    max_meets: int = 100,
    scoring_type: str = "auto",
    bias_correct: bool = False,
    bias_margin_threshold: float = 0.0,
) -> list[dict]:
    """
    Run backtests across many meets to measure overall prediction accuracy.

    For championship meets with many teams, uses full-field scoring.
    For dual/invitational meets, uses 2-team scoring.

    Args:
        bias_correct: If True, compute bias-corrected projections for comparison.
        bias_margin_threshold: If > 0 and bias_correct=True, only USE bias-corrected
            scores for winner prediction when projected margin < this threshold.
            When 0 (default), always use bias-corrected scores if available.

    Returns a list of result summaries (one per meet-team-pair).
    """
    meets = list_backtestable_meets(min_entries=min_entries)
    results: list[dict] = []

    for meet in meets[:max_meets]:
        if meet_types and meet["type"] not in meet_types:
            continue

        top_teams = meet.get("top_teams", [])
        if len(top_teams) < 2:
            continue

        team_a = top_teams[0]
        team_b = top_teams[1]

        try:
            # Use full-field scoring for championship meets with many teams
            if meet["type"] == "championship" and meet.get("teams", 0) > 4:
                result = await run_championship_backtest(
                    meet_id=meet["meet_id"],
                    team_a_id=team_a["id"],
                    team_b_id=team_b["id"],
                    scoring_type=scoring_type,
                )
            else:
                result = await run_backtest(
                    meet_id=meet["meet_id"],
                    team_a_id=team_a["id"],
                    team_b_id=team_b["id"],
                    max_iters=0,
                    scoring_type=scoring_type,
                    bias_correct=bias_correct,
                )

            if not result.get("success"):
                continue

            proj = result["projected"]
            actual = result["actual"]

            # Determine which scores to use for winner prediction
            raw_a = proj["team_a_score"]
            raw_b = proj["team_b_score"]
            raw_margin = abs(raw_a - raw_b)

            has_bc = bias_correct and "bias_corrected" in result
            use_bc = False

            if has_bc:
                bc = result["bias_corrected"]
                if bias_margin_threshold <= 0:
                    # Always use bias-corrected
                    use_bc = True
                elif raw_margin < bias_margin_threshold:
                    # Only use when margin is close
                    use_bc = True

            if use_bc:
                best_a = bc["team_a_score"]
                best_b = bc["team_b_score"]
            else:
                best_a = raw_a
                best_b = raw_b

            proj_winner = "A" if best_a > best_b else "B"
            actual_winner = (
                "A" if actual["team_a_score"] > actual["team_b_score"] else "B"
            )

            entry: dict = {
                "meet_id": meet["meet_id"],
                "meet_name": meet["name"],
                "meet_date": meet["date"],
                "meet_type": meet["type"],
                "team_a": team_a["name"],
                "team_b": team_b["name"],
                "proj_a": best_a,
                "proj_b": best_b,
                "actual_a": actual["team_a_score"],
                "actual_b": actual["team_b_score"],
                "score_error": abs(best_a - actual["team_a_score"])
                + abs(best_b - actual["team_b_score"]),
                "winner_correct": proj_winner == actual_winner,
                "source": proj.get("source", "unknown"),
                "used_bias": use_bc,
                "raw_margin": raw_margin,
            }

            # Include raw projected for comparison when bias-correcting
            if has_bc:
                entry["raw_proj_a"] = raw_a
                entry["raw_proj_b"] = raw_b
                entry["raw_error"] = abs(raw_a - actual["team_a_score"]) + abs(
                    raw_b - actual["team_b_score"]
                )
                raw_winner = "A" if raw_a > raw_b else "B"
                entry["raw_winner_correct"] = raw_winner == actual_winner

            results.append(entry)
        except Exception:
            continue

    return results


async def run_championship_strategy_backtest(
    meet_id: int,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
    scoring_type: str = "auto",
    methods: list[str] | None = None,
    aquaopt_iters: int = 100,
    gurobi_time_limit: int = 10,
    **kwargs,
) -> dict:
    """
    Compare championship meet predictions across multiple strategies:
      - projection: raw seed-time scoring (baseline)
      - greedy: greedy per-swimmer event assignment
      - nash: iterated greedy with Nash multi-team equilibrium
      - aquaopt: per-team SA optimizer against rest of field

    Returns a dict with results per method plus actual results.
    """
    from swim_ai_reflex.backend.core.championship_strategy import (
        run_championship_strategy,
    )

    if methods is None:
        methods = ["projection", "hungarian", "nash"]

    all_df, meet_info = load_all_meet_entries(meet_id)
    if all_df.empty:
        return {"success": False, "error": "No entries found", "meet_info": meet_info}

    rules = _get_rules(meet_info.get("meet_type", "championship"), scoring_type)

    # --- ACTUAL results (ground truth from finals_time) ---
    finals_df = all_df[all_df["finals_time"].notna()].copy()
    finals_df["time"] = finals_df["finals_time"]
    actual_scored, actual_totals = _score_meet_multi_team(
        finals_df, rules, time_col="time"
    )
    actual_standings = sorted(actual_totals.items(), key=lambda x: -x[1])

    # --- Find teams of interest ---
    if team_a_id and team_b_id:
        team_a_name = (
            all_df[all_df["team_id"] == team_a_id]["team"].iloc[0]
            if not all_df[all_df["team_id"] == team_a_id].empty
            else f"Team {team_a_id}"
        )
        team_b_name = (
            all_df[all_df["team_id"] == team_b_id]["team"].iloc[0]
            if not all_df[all_df["team_id"] == team_b_id].empty
            else f"Team {team_b_id}"
        )
    else:
        if len(actual_standings) < 2:
            return {
                "success": False,
                "error": "Fewer than 2 teams scored",
                "meet_info": meet_info,
            }
        team_a_name = actual_standings[0][0]
        team_b_name = actual_standings[1][0]

    # --- Run each strategy on SEED times ---
    seed_df = all_df[all_df["seed_time"].notna()].copy()
    seed_df["time"] = seed_df["seed_time"]

    strategy_results: dict = {}
    for method in methods:
        try:
            result = run_championship_strategy(
                all_entries=seed_df,
                rules=rules,
                time_col="time",
                method=method,
                aquaopt_iters=aquaopt_iters,
                gurobi_time_limit=gurobi_time_limit,
                **kwargs,
            )
            totals = result.get("team_totals", {})
            standings = result.get("standings", [])

            strategy_results[method] = {
                "team_a_score": totals.get(team_a_name, 0.0),
                "team_b_score": totals.get(team_b_name, 0.0),
                "standings_top5": standings[:5],
                "status": result.get("status", ""),
                "iterations": result.get("iterations", 0),
                "total_teams": len(totals),
            }
        except Exception as e:
            strategy_results[method] = {"error": str(e)}

    # --- Compute accuracy metrics ---
    actual_a = actual_totals.get(team_a_name, 0.0)
    actual_b = actual_totals.get(team_b_name, 0.0)
    actual_winner = "A" if actual_a > actual_b else "B"

    for method, res in strategy_results.items():
        if "error" in res:
            continue
        pa = res["team_a_score"]
        pb = res["team_b_score"]
        proj_winner = "A" if pa > pb else "B"
        res["winner_correct"] = proj_winner == actual_winner
        res["score_error"] = abs(pa - actual_a) + abs(pb - actual_b)
        res["margin_error"] = abs((pa - pb) - (actual_a - actual_b))

        # Standings overlap (top 5)
        actual_top5 = set(t for t, _ in actual_standings[:5])
        proj_top5 = set(t for t, _ in res.get("standings_top5", []))
        res["top5_overlap"] = len(actual_top5 & proj_top5)

        # Overall winner
        proj_standings_names = [t for t, _ in res.get("standings_top5", [])]
        res["overall_winner_correct"] = (
            proj_standings_names[0] == actual_standings[0][0]
            if proj_standings_names and actual_standings
            else False
        )

    return {
        "success": True,
        "meet_info": {
            **meet_info,
            "team_a": {"name": team_a_name},
            "team_b": {"name": team_b_name},
        },
        "actual": {
            "team_a_score": actual_a,
            "team_b_score": actual_b,
            "standings_top10": actual_standings[:10],
        },
        "strategies": strategy_results,
    }


def list_backtestable_meets(
    min_entries: int = 20, recent_seasons: int = 5
) -> list[dict]:
    """List meets suitable for backtesting (have entries from 2+ teams).

    Excludes meets marked as duplicates or corrupted (notes LIKE 'DUPLICATE%' or 'CORRUPTED%').
    """
    with Session(engine) as session:
        rows = session.exec(
            text("""
            SELECT m.id, m.name, m.meet_date, m.meet_type, s.name as season,
                   count(DISTINCT en.id) as entry_count,
                   count(DISTINCT en.team_id) as team_count,
                   count(DISTINCT en.swimmer_id) as swimmer_count,
                   sum(CASE WHEN en.seed_time > 0 THEN 1 ELSE 0 END) as seed_count,
                   sum(CASE WHEN en.finals_time > 0 THEN 1 ELSE 0 END) as finals_count,
                   sum(CASE WHEN en.seed_time > 0 AND en.finals_time > 0 THEN 1 ELSE 0 END) as both_count
            FROM meets m
            JOIN seasons s ON m.season_id = s.id
            JOIN events ev ON ev.meet_id = m.id
            JOIN entries en ON en.event_id = ev.id
            WHERE (en.finals_time IS NOT NULL OR en.seed_time IS NOT NULL)
              AND en.is_dq = 0
              AND ev.is_relay = 0
              AND (m.notes IS NULL OR (m.notes NOT LIKE 'DUPLICATE%' AND m.notes NOT LIKE 'CORRUPTED%'))
            GROUP BY m.id
            HAVING finals_count >= :min_entries AND team_count >= 2
            ORDER BY m.meet_date DESC
        """),
            params={"min_entries": min_entries},
        ).all()

        meets = []
        for mid, name, mdate, mt, season, ecnt, tcnt, scnt, seedc, finc, bothc in rows:
            teams = session.exec(
                text("""
                SELECT t.id, t.name, count(en.id) as cnt
                FROM entries en
                JOIN events ev ON en.event_id = ev.id
                JOIN teams t ON en.team_id = t.id
                WHERE ev.meet_id = :meet_id
                  AND (en.finals_time IS NOT NULL OR en.seed_time IS NOT NULL)
                GROUP BY t.id
                ORDER BY cnt DESC
                LIMIT 5
            """),
                params={"meet_id": mid},
            ).all()

            meets.append(
                {
                    "meet_id": mid,
                    "name": name,
                    "date": str(mdate),
                    "type": mt,
                    "season": season,
                    "entries": ecnt,
                    "teams": tcnt,
                    "swimmers": scnt,
                    "seed_count": seedc,
                    "finals_count": finc,
                    "both_count": bothc,
                    "top_teams": [
                        {"id": t[0], "name": t[1], "entries": t[2]} for t in teams
                    ],
                }
            )

        return meets
