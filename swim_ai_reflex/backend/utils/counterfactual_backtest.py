"""
Counterfactual Dual-Meet Backtest

Answers: "Would the optimizer's lineup have beaten the coach's actual lineup?"

Unlike the standard backtest (which reshuffles existing entries and finds zero
improvement), this module:
1. Builds the full team roster from swimmer_bests (all events a swimmer CAN swim)
2. Runs Gurobi MIP to assign swimmers to events from scratch
3. Scores against opponent's actual finals results
4. Compares to what the coach actually entered

Supports both Gurobi MIP (exact) and AquaOpt SA (approximate).

NOTE: Requires persistence.database, persistence.db_models, core.optimizer_factory,
core.optimizer_utils, core.rules, core.scoring -- all should exist on Mac.
"""

import logging
import time

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from swim_ai_reflex.backend.core.optimizer_factory import OptimizerFactory
from swim_ai_reflex.backend.core.optimizer_utils import (
    count_back_to_back_events,
    validate_lineup_constraints,
)
from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.core.scoring import full_meet_scoring
from swim_ai_reflex.backend.persistence.database import engine
from swim_ai_reflex.backend.persistence.db_models import Meet, Team

logger = logging.getLogger(__name__)

VALID_TIME_METRICS = ("best_time", "recent_time", "mean_time")

# Standard VISAA dual meet individual events
DUAL_INDIVIDUAL_EVENTS = [
    "200 Free",
    "200 IM",
    "50 Free",
    "100 Fly",
    "100 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
]


def list_eligible_meets(seton_team_id: int | None = None) -> list[dict]:
    """
    List dual meets eligible for counterfactual backtesting.

    Criteria:
    - meet_type = 'dual'
    - At least 2 teams with individual entries that have finals_time
    - If seton_team_id specified, only meets where that team competed
    """
    with Session(engine) as session:
        params: dict = {}
        team_filter = ""
        if seton_team_id is not None:
            team_filter = """
                AND m.id IN (
                    SELECT DISTINCT ev2.meet_id FROM events ev2
                    JOIN entries en2 ON en2.event_id = ev2.id
                    WHERE en2.team_id = :seton_team_id
                    AND en2.finals_time IS NOT NULL AND en2.finals_time > 0
                )
            """
            params["seton_team_id"] = seton_team_id

        rows = session.exec(
            text(f"""
            SELECT m.id, m.name, m.meet_date, m.season_id,
                   COUNT(DISTINCT en.team_id) AS team_count,
                   COUNT(en.id) AS entry_count
            FROM meets m
            JOIN events ev ON ev.meet_id = m.id
            JOIN entries en ON en.event_id = ev.id
            WHERE m.meet_type = 'dual'
              AND ev.is_relay = 0 AND ev.is_diving = 0
              AND en.finals_time IS NOT NULL AND en.finals_time > 0
              AND en.is_dq = 0
              {team_filter}
            GROUP BY m.id
            HAVING team_count >= 2
            ORDER BY m.meet_date DESC
        """),
            params=params,
        ).all()

        results = []
        for meet_id, name, date, season_id, team_count, entry_count in rows:
            team_rows = session.exec(
                text("""
                SELECT DISTINCT en.team_id, t.name
                FROM entries en
                JOIN events ev ON en.event_id = ev.id
                JOIN teams t ON t.id = en.team_id
                WHERE ev.meet_id = :meet_id
                  AND ev.is_relay = 0
                  AND en.finals_time IS NOT NULL AND en.finals_time > 0
            """),
                params={"meet_id": meet_id},
            ).all()

            results.append(
                {
                    "meet_id": meet_id,
                    "name": name,
                    "date": str(date) if date else "unknown",
                    "season_id": season_id,
                    "team_count": team_count,
                    "entry_count": entry_count,
                    "teams": [{"id": tid, "name": tname} for tid, tname in team_rows],
                }
            )

        return results


def build_dual_roster(
    session: Session,
    team_id: int,
    season_id: int,
    time_metric: str = "best_time",
    event_names: list[str] | None = None,
    gender: str | None = None,
) -> pd.DataFrame:
    """Build full roster DataFrame from swimmer_bests for dual meet optimization."""
    if time_metric not in VALID_TIME_METRICS:
        raise ValueError(
            f"Invalid time_metric '{time_metric}'. Use: {VALID_TIME_METRICS}"
        )

    time_col = f"sb.{time_metric}"

    gender_filter = ""
    if gender:
        gender_filter = "AND s.gender = :gender"

    rows = session.exec(
        text(f"""
        SELECT s.first_name || ' ' || s.last_name AS swimmer_name,
               s.gender,
               sb.event_name,
               {time_col} AS time_val,
               sts.grade
        FROM swimmer_bests sb
        JOIN swimmers s ON sb.swimmer_id = s.id
        JOIN swimmer_team_seasons sts
            ON sts.swimmer_id = s.id
            AND sts.season_id = :season_id
            AND sts.team_id = :team_id
        WHERE sb.season_id = :season_id
          AND {time_col} IS NOT NULL
          AND {time_col} > 0
          {gender_filter}
        ORDER BY s.last_name, s.first_name, sb.event_name
    """),
        params={
            "season_id": season_id,
            "team_id": team_id,
            **({"gender": gender} if gender else {}),
        },
    ).all()

    if not rows:
        return pd.DataFrame()

    target_events = set(event_names) if event_names else set(DUAL_INDIVIDUAL_EVENTS)

    records = []
    for swimmer_name, swimmer_gender, event_name, time_val, grade in rows:
        if event_name not in target_events:
            continue
        records.append(
            {
                "swimmer": swimmer_name,
                "event": event_name,
                "time": round(time_val, 2),
                "team": "seton",
                "grade": grade if grade else 10,
                "gender": swimmer_gender,
            }
        )

    return pd.DataFrame(records)


def load_meet_actuals(
    session: Session,
    meet_id: int,
    team_id: int,
    team_label: str = "opponent",
    gender: str | None = None,
) -> pd.DataFrame:
    """Load a team's actual entries from a meet."""
    gender_filter = ""
    if gender:
        gender_filter = "AND ev.gender = :gender"

    rows = session.exec(
        text(f"""
        SELECT s.first_name || ' ' || s.last_name AS swimmer,
               ev.event_name AS event,
               en.finals_time AS time_val,
               s.gender,
               sts.grade
        FROM entries en
        JOIN events ev ON en.event_id = ev.id
        JOIN swimmers s ON en.swimmer_id = s.id
        LEFT JOIN swimmer_team_seasons sts
            ON sts.swimmer_id = s.id
            AND sts.team_id = :team_id
            AND sts.season_id = (SELECT season_id FROM meets WHERE id = :meet_id)
        WHERE ev.meet_id = :meet_id
          AND en.team_id = :team_id
          AND en.is_dq = 0
          AND ev.is_relay = 0
          AND ev.is_diving = 0
          AND en.finals_time IS NOT NULL
          AND en.finals_time > 0
          {gender_filter}
        ORDER BY ev.event_number, en.finals_time
    """),
        params={
            "meet_id": meet_id,
            "team_id": team_id,
            **({"gender": gender} if gender else {}),
        },
    ).all()

    if not rows:
        return pd.DataFrame()

    records = []
    for swimmer, event, time_val, swimmer_gender, grade in rows:
        records.append(
            {
                "swimmer": swimmer,
                "event": event,
                "time": round(time_val, 2),
                "team": team_label,
                "grade": grade if grade else 10,
                "gender": swimmer_gender,
            }
        )

    return pd.DataFrame(records)


def _get_meet_genders(session: Session, meet_id: int) -> list[str]:
    """Get distinct genders for individual events at a meet."""
    rows = session.exec(
        text("""
        SELECT DISTINCT ev.gender
        FROM events ev
        WHERE ev.meet_id = :meet_id
          AND ev.is_relay = 0 AND ev.is_diving = 0
          AND ev.gender IS NOT NULL
        ORDER BY ev.gender
    """),
        params={"meet_id": meet_id},
    ).all()
    return [r[0] for r in rows if r[0]]


def _get_meet_events(session: Session, meet_id: int) -> list[str]:
    """Get distinct individual event names at a meet."""
    rows = session.exec(
        text("""
        SELECT DISTINCT ev.event_name
        FROM events ev
        WHERE ev.meet_id = :meet_id
          AND ev.is_relay = 0 AND ev.is_diving = 0
        ORDER BY ev.event_name
    """),
        params={"meet_id": meet_id},
    ).all()
    return [r[0] for r in rows]


def identify_key_differences(
    coach_lineup: pd.DataFrame,
    optimizer_lineup: pd.DataFrame,
) -> list[dict]:
    """Compare coach vs optimizer lineups to find meaningful differences."""

    def _swimmer_events(df: pd.DataFrame) -> dict[str, list[str]]:
        if df.empty:
            return {}
        return df.groupby("swimmer")["event"].apply(list).to_dict()

    coach_map = _swimmer_events(coach_lineup)
    opt_map = _swimmer_events(optimizer_lineup)

    all_swimmers = set(coach_map.keys()) | set(opt_map.keys())
    diffs = []

    for swimmer in sorted(all_swimmers):
        coach_events = sorted(coach_map.get(swimmer, []))
        opt_events = sorted(opt_map.get(swimmer, []))

        if coach_events == opt_events:
            continue

        if not coach_events:
            diffs.append(
                {
                    "swimmer": swimmer,
                    "type": "added",
                    "coach_events": [],
                    "optimizer_events": opt_events,
                }
            )
        elif not opt_events:
            diffs.append(
                {
                    "swimmer": swimmer,
                    "type": "benched",
                    "coach_events": coach_events,
                    "optimizer_events": [],
                }
            )
        else:
            diffs.append(
                {
                    "swimmer": swimmer,
                    "type": "reassigned",
                    "coach_events": coach_events,
                    "optimizer_events": opt_events,
                }
            )

    return diffs


def run_counterfactual(
    meet_id: int,
    seton_team_id: int,
    opponent_team_id: int,
    time_metric: str = "best_time",
    gurobi_time_limit: int = 30,
    method: str = "gurobi",
) -> dict:
    """Run a single counterfactual backtest for one dual meet."""
    rules = VISAADualRules()

    with Session(engine) as session:
        meet = session.get(Meet, meet_id)
        if not meet:
            return {"success": False, "error": f"Meet {meet_id} not found"}

        seton_team = session.get(Team, seton_team_id)
        opp_team = session.get(Team, opponent_team_id)
        if not seton_team or not opp_team:
            return {"success": False, "error": "Team not found"}

        season_id = meet.season_id
        if not season_id:
            return {"success": False, "error": "Meet has no season_id"}

        meet_events = _get_meet_events(session, meet_id)
        genders = _get_meet_genders(session, meet_id)
        if not genders:
            genders = ["M", "F"]

        coach_seton_total = 0.0
        coach_opp_total = 0.0
        opt_seton_total = 0.0
        opt_opp_total = 0.0
        fair_seton_total = 0.0
        fair_opp_total = 0.0
        all_coach_lineup: list[pd.DataFrame] = []
        all_opt_lineup: list[pd.DataFrame] = []
        all_fair_lineup: list[pd.DataFrame] = []
        _all_diffs: list[dict] = []  # noqa: F841
        roster_swimmers: set[str] = set()
        roster_pairs = 0
        coach_violations: list[str] = []

        strategy = OptimizerFactory.get_strategy(method)

        t0 = time.time()

        for gender in genders:
            opp_actuals = load_meet_actuals(
                session, meet_id, opponent_team_id, team_label="opponent", gender=gender
            )
            if opp_actuals.empty:
                continue

            seton_roster = build_dual_roster(
                session,
                seton_team_id,
                season_id,
                time_metric=time_metric,
                event_names=meet_events,
                gender=gender,
            )
            if seton_roster.empty:
                continue

            roster_swimmers.update(seton_roster["swimmer"].unique())
            roster_pairs += len(seton_roster)

            coach_lineup = load_meet_actuals(
                session, meet_id, seton_team_id, team_label="seton", gender=gender
            )

            def scoring_fn(df: pd.DataFrame):
                return full_meet_scoring(df, rules=rules, validate=False)

            try:
                opt_kwargs: dict = dict(
                    seton_roster=seton_roster,
                    opponent_roster=opp_actuals,
                    scoring_fn=scoring_fn,
                    rules=rules,
                    time_limit=gurobi_time_limit,
                )
                if method == "aquaopt":
                    opt_kwargs["full_roster"] = seton_roster
                    opt_kwargs["max_iters"] = 5000

                opt_lineup, opt_scored, opt_totals, _ = strategy.optimize(**opt_kwargs)
                opt_seton_total += opt_totals.get("seton", 0)
                opt_opp_total += opt_totals.get("opponent", 0)
                all_opt_lineup.append(opt_lineup)
            except Exception as e:
                logger.warning(f"{method} failed for {gender}: {e}")
                opt_seton_total += 0
                opt_opp_total += 0

            if not coach_lineup.empty and not opp_actuals.empty:
                combined = pd.concat([coach_lineup, opp_actuals], ignore_index=True)
                _, coach_totals = full_meet_scoring(
                    combined, rules=rules, validate=False
                )
                coach_seton_total += coach_totals.get("seton", 0)
                coach_opp_total += coach_totals.get("opponent", 0)
                all_coach_lineup.append(coach_lineup)

                _, v = validate_lineup_constraints(coach_lineup, rules)
                for violation in v:
                    coach_violations.append(f"{gender}: {violation}")
                b2b = count_back_to_back_events(coach_lineup)
                if b2b > 0 and not any("back-to-back" in cv for cv in coach_violations):
                    coach_violations.append(f"{gender}: {b2b} back-to-back event(s)")

            if not coach_lineup.empty and not seton_roster.empty:
                coach_swimmers = set(coach_lineup["swimmer"].unique())
                fair_roster = seton_roster[
                    seton_roster["swimmer"].isin(coach_swimmers)
                ].copy()
                if not fair_roster.empty:
                    try:
                        fair_kwargs: dict = dict(
                            seton_roster=fair_roster,
                            opponent_roster=opp_actuals,
                            scoring_fn=scoring_fn,
                            rules=rules,
                            time_limit=gurobi_time_limit,
                        )
                        if method == "aquaopt":
                            fair_kwargs["full_roster"] = fair_roster
                            fair_kwargs["max_iters"] = 5000
                        fair_lineup, _, fair_totals, _ = strategy.optimize(
                            **fair_kwargs
                        )
                        fair_seton_total += fair_totals.get("seton", 0)
                        fair_opp_total += fair_totals.get("opponent", 0)
                        all_fair_lineup.append(fair_lineup)
                    except Exception as e:
                        logger.warning(f"Fair-mode {method} failed for {gender}: {e}")

        elapsed = time.time() - t0

        coach_combined = (
            pd.concat(all_coach_lineup, ignore_index=True)
            if all_coach_lineup
            else pd.DataFrame()
        )
        opt_combined = (
            pd.concat(all_opt_lineup, ignore_index=True)
            if all_opt_lineup
            else pd.DataFrame()
        )

        if not coach_combined.empty:
            coach_reduced = _reduce_to_scoring(coach_combined, rules)
        else:
            coach_reduced = coach_combined

        diffs = identify_key_differences(coach_reduced, opt_combined)

        delta = opt_seton_total - coach_seton_total

        coach_winner = "seton" if coach_seton_total > coach_opp_total else "opponent"
        opt_winner = "seton" if opt_seton_total > opt_opp_total else "opponent"

        fair_delta = fair_seton_total - coach_seton_total
        fair_winner = "seton" if fair_seton_total > fair_opp_total else "opponent"

        return {
            "success": True,
            "meet_info": {
                "meet_id": meet_id,
                "meet_name": meet.name,
                "meet_date": str(meet.meet_date) if meet.meet_date else "unknown",
                "season_id": season_id,
                "seton_team": seton_team.name,
                "opponent_team": opp_team.name,
            },
            "coach_result": {
                "seton_score": coach_seton_total,
                "opponent_score": coach_opp_total,
                "winner": coach_winner,
                "violations": coach_violations,
                "seton_swimmers": coach_combined["swimmer"].nunique()
                if not coach_combined.empty
                else 0,
            },
            "optimizer_result": {
                "seton_score": opt_seton_total,
                "opponent_score": opt_opp_total,
                "winner": opt_winner,
            },
            "fair_result": {
                "seton_score": fair_seton_total,
                "opponent_score": fair_opp_total,
                "winner": fair_winner,
                "delta": fair_delta,
            },
            "delta": delta,
            "fair_delta": fair_delta,
            "win_flipped": coach_winner != opt_winner,
            "key_differences": diffs,
            "roster_stats": {
                "total_swimmers": len(roster_swimmers),
                "swimmer_event_pairs": roster_pairs,
                "events": len(meet_events),
                "genders": genders,
            },
            "time_metric": time_metric,
            "elapsed_seconds": round(elapsed, 2),
        }


def _reduce_to_scoring(df: pd.DataFrame, rules: VISAADualRules) -> pd.DataFrame:
    """Reduce a full lineup to the top N entries per event."""
    if df.empty:
        return df

    df = df.copy()
    df["rank_in_swimmer"] = df.groupby("swimmer")["time"].rank(method="first")
    df = df[df["rank_in_swimmer"] <= rules.max_individual_events_per_swimmer].copy()

    df["rank_in_event"] = df.groupby("event")["time"].rank(method="first")
    df = df[df["rank_in_event"] <= rules.max_entries_per_team_per_event].copy()

    df.drop(columns=["rank_in_swimmer", "rank_in_event"], inplace=True)
    return df.reset_index(drop=True)


def run_batch(
    seton_team_id: int,
    time_metric: str = "best_time",
    gurobi_time_limit: int = 30,
    max_meets: int = 50,
    method: str = "gurobi",
) -> dict:
    """Run counterfactual backtests across all eligible dual meets."""
    eligible = list_eligible_meets(seton_team_id)
    if not eligible:
        return {
            "success": False,
            "error": "No eligible dual meets found",
            "results": [],
        }

    results = []
    total_delta = 0.0
    total_fair_delta = 0.0
    wins_flipped = 0
    meets_better = 0
    meets_worse = 0
    meets_same = 0
    coach_b2b_total = 0
    coach_violation_meets = 0

    for meet_info in eligible[:max_meets]:
        meet_id = meet_info["meet_id"]

        opponents = [t for t in meet_info["teams"] if t["id"] != seton_team_id]

        for opp in opponents:
            result = run_counterfactual(
                meet_id=meet_id,
                seton_team_id=seton_team_id,
                opponent_team_id=opp["id"],
                time_metric=time_metric,
                gurobi_time_limit=gurobi_time_limit,
                method=method,
            )

            if result.get("success"):
                delta = result["delta"]
                total_delta += delta
                total_fair_delta += result.get("fair_delta", 0)
                if delta > 0.5:
                    meets_better += 1
                elif delta < -0.5:
                    meets_worse += 1
                else:
                    meets_same += 1
                if result.get("win_flipped"):
                    wins_flipped += 1
                cv = result.get("coach_result", {}).get("violations", [])
                if cv:
                    coach_violation_meets += 1
                    coach_b2b_total += sum(1 for v in cv if "back-to-back" in v)

            results.append(result)

    n = len([r for r in results if r.get("success")])
    avg_delta = total_delta / n if n > 0 else 0
    avg_fair_delta = total_fair_delta / n if n > 0 else 0

    return {
        "success": True,
        "total_matchups": len(results),
        "successful": n,
        "avg_delta": round(avg_delta, 1),
        "avg_fair_delta": round(avg_fair_delta, 1),
        "meets_optimizer_better": meets_better,
        "meets_coach_better": meets_worse,
        "meets_same": meets_same,
        "wins_flipped": wins_flipped,
        "total_delta": round(total_delta, 1),
        "total_fair_delta": round(total_fair_delta, 1),
        "coach_violation_meets": coach_violation_meets,
        "coach_b2b_total": coach_b2b_total,
        "time_metric": time_metric,
        "results": results,
    }
