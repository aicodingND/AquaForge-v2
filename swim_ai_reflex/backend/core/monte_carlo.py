# core/monte_carlo.py
import numpy as np
import pandas as pd

from swim_ai_reflex.backend.core.attrition_model import ATTRITION_RATES
from swim_ai_reflex.backend.core.rules import VISAADualRules


def fast_monte_carlo_simulation(
    seton_df, opponent_df, trials=500, rules=None, attrition=None
):
    """
    High-performance vectorized Monte Carlo simulation using Numpy.
    Avoids slow Pandas operations inside the simulation loop.

    Args:
        attrition: AttritionRates instance for stochastic swimmer dropout.
                   Defaults to ATTRITION_RATES singleton.
    """
    if rules is None:
        rules = VISAADualRules()
    if attrition is None:
        attrition = ATTRITION_RATES

    combined_base = pd.concat([seton_df, opponent_df], ignore_index=True)

    # Pre-calculate constants
    seton_points_total = np.zeros(trials)
    opponent_points_total = np.zeros(trials)

    # Identify unique events
    events = combined_base["event"].unique()

    for event in events:
        # Filter for this event
        edf = combined_base[combined_base["event"] == event].copy()
        if edf.empty:
            continue

        # Extract data arrays
        # Use simple numeric ID for teams: 1 = Seton, 0 = Opponent
        # We look for "seton" in team name (case insensitive)
        is_seton = (
            edf["team"].astype(str).str.lower().str.contains("seton").values.astype(int)
        )  # Array of 1s and 0s
        base_times = edf["time"].values.astype(float)

        num_swimmers = len(base_times)

        # --- Vectorized Simulation ---

        # 1. Generate Random Times Matrix (Trials x Swimmers)
        # Different variance models for different event types:
        # - Individual events: σ = max(0.2, 0.005 * time) (~0.5% CV)
        # - Relay events: σ = max(0.5, 0.008 * time) (higher variance from 4 swimmers + exchange)
        # - Diving: σ = max(10.0, 0.05 * score) (5% score variance)

        is_diving = "diving" in event.lower()
        is_relay = "relay" in event.lower()

        if is_diving:
            # Diving: scores typically 200-350 range, 5% variance
            sigmas = np.maximum(10.0, 0.05 * base_times)
        elif is_relay:
            # Relay: 4 swimmers + exchange variance ≈ √4 × individual variance
            # Plus about 20% extra for exchange timing
            sigmas = np.maximum(0.5, 0.008 * base_times)
        else:
            # Individual swimming: ~0.5% coefficient of variation
            sigmas = np.maximum(0.2, 0.005 * base_times)

        # Generate standard normal noise (Trials x Swimmers)
        noise = np.random.normal(loc=0.0, scale=1.0, size=(trials, num_swimmers))

        # Apply noise: T_sim = T + sigma * Z
        # sigmas broadcasts from (N,) to (T, N)
        sim_times = base_times + (noise * sigmas)

        # Ensure non-negative times (or scores for diving)
        sim_times = np.maximum(0.01, sim_times)

        # Attrition: randomly remove swimmers each trial based on DNS/DQ rate
        if attrition.enabled:
            att_rate = attrition.attrition_rate(event)
            if att_rate > 0:
                # Generate uniform random (Trials x Swimmers); scratch if < att_rate
                scratch_rolls = np.random.random(size=(trials, num_swimmers))
                scratched = scratch_rolls < att_rate
                if is_diving:
                    # Diving: lower score = worse → set to 0 to remove
                    sim_times = np.where(scratched, 0.0, sim_times)
                else:
                    # Swimming: higher time = worse → set to large value
                    sim_times = np.where(scratched, 9999.0, sim_times)

        # 2. Determine Ranks (Sorting)
        # argsort along axis 1 (across swimmers for each trial)
        # We want smallest time first -> Ascending sort.
        # But if it's Diving, we want largest score first -> Descending.
        # (is_diving was set above during variance calculation)
        if is_diving:
            # Diving: higher score is better. Negate to use argsort (which sorts ascending).
            sorted_indices = np.argsort(-sim_times, axis=1)
        else:
            sorted_indices = np.argsort(sim_times, axis=1)

        # 3. Map Ranks to Teams
        # We reorder the 'is_seton' array according to the sorted indices
        # results in (Trial x Rank) matrix where value is 1 (Seton in that rank) or 0 (Opp in that rank)
        ranked_teams = is_seton[sorted_indices]

        # 4. Assign Points
        is_relay = (
            edf["is_relay"].iloc[0]
            if "is_relay" in edf.columns
            else "relay" in event.lower()
        )
        points_map = rules.relay_points if is_relay else rules.individual_points

        # Create points vector matching the number of swimmers
        # e.g., [6, 4, 3, 2, 1, 0, 0...]
        points_vector = np.zeros(num_swimmers)
        limit = min(len(points_map), num_swimmers)
        points_vector[:limit] = points_map[:limit]

        # Broadcast points to matrix (Trials x Swimmers)
        # All trials have same potential points for 1st, 2nd, 3rd...
        # So we just multiply the ranked position by points.
        # But wait, we need to handle "Max Scorers per Team".

        scorer_limit = (
            rules.max_scorers_per_team_relay
            if is_relay
            else rules.max_scorers_per_team_individual
        )

        # Calculate cumulative count of swimmers for each team in the ranked order
        # axis=1 is along the ranks (1st, 2nd, 3rd...)
        cum_seton = np.cumsum(ranked_teams == 1, axis=1)
        cum_opp = np.cumsum(ranked_teams == 0, axis=1)

        # Valid scorer mask: Is Seton AND count <= Limit OR Is Opp AND count <= limit
        valid_seton = (ranked_teams == 1) & (cum_seton <= scorer_limit)
        valid_opp = (ranked_teams == 0) & (cum_opp <= scorer_limit)

        # Combine valid mask
        valid_scorers = valid_seton | valid_opp

        # Apply points
        # points_vector must be broadcasted to (Trials, N)
        # It represents points for 1st place, 2nd place...
        trial_points = points_vector * valid_scorers

        # Sum points for Seton and Opponent per trial
        # trial_points where ranked_teams is 1

        trial_seton_points = np.sum(trial_points * (ranked_teams == 1), axis=1)
        trial_opp_points = np.sum(trial_points * (ranked_teams == 0), axis=1)

        seton_points_total += trial_seton_points
        opponent_points_total += trial_opp_points

    # Compile Results
    return {
        "trials": trials,
        "seton_mean": float(np.mean(seton_points_total)),
        "opponent_mean": float(np.mean(opponent_points_total)),
        "seton_std": float(np.std(seton_points_total)),
        "opponent_std": float(np.std(opponent_points_total)),
        "seton_min": float(np.min(seton_points_total)),
        "seton_max": float(np.max(seton_points_total)),
        "seton_win_prob": float(np.mean(seton_points_total > opponent_points_total)),
    }


# Alias for compatibility if imported elsewhere
run_monte_carlo_on_lineups = fast_monte_carlo_simulation
