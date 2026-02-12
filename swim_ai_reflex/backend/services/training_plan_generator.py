"""
Training Plan Generator

AI-powered training plan creation based on swimmer goals and current performance.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class WorkoutSet:
    """Individual workout set"""

    distance: int
    repetitions: int
    interval: str  # e.g., "1:30", "on the top"
    intensity: str  # 'easy', 'moderate', 'hard', 'race-pace'
    stroke: str
    description: str


@dataclass
class TrainingSession:
    """Single training session"""

    date: datetime
    session_type: str  # 'technique', 'endurance', 'speed', 'recovery'
    total_yards: int
    duration_minutes: int
    sets: list[WorkoutSet]
    focus_area: str


@dataclass
class TrainingPlan:
    """Complete training plan"""

    start_date: datetime
    end_date: datetime
    goal: str
    sessions: list[TrainingSession]
    weekly_volume: int
    phases: list[dict]


class TrainingPlanGenerator:
    """
    Generates personalized training plans based on:
    - Current fitness level
    - Target times
    - Time available
    - Meet schedule
    """

    def generate_plan(
        self,
        swimmer_profile: dict,
        target_times: dict[str, float],
        weeks: int = 12,
        sessions_per_week: int = 5,
    ) -> TrainingPlan:
        """Generate comprehensive training plan."""
        level = swimmer_profile.get("level", "intermediate")

        base_volume = self._calculate_base_volume(level)
        phases = self._create_phases(weeks)

        start_date = datetime.now()
        sessions = []

        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            phase = self._get_phase_for_week(week, phases)

            for session_num in range(sessions_per_week):
                session_date = week_start + timedelta(days=session_num)
                session_type = self._determine_session_type(
                    session_num, sessions_per_week
                )

                session = self._generate_session(
                    session_date, session_type, phase, base_volume, target_times
                )
                sessions.append(session)

        return TrainingPlan(
            start_date=start_date,
            end_date=start_date + timedelta(weeks=weeks),
            goal=self._format_goal(target_times),
            sessions=sessions,
            weekly_volume=base_volume * sessions_per_week,
            phases=phases,
        )

    def _calculate_base_volume(self, level: str) -> int:
        """Calculate base yardage per session"""
        volumes = {
            "beginner": 2000,
            "intermediate": 3500,
            "advanced": 5000,
            "elite": 7000,
        }
        return volumes.get(level, 3500)

    def _create_phases(self, weeks: int) -> list[dict]:
        """Create training phases (periodization)"""
        phase_length = weeks // 3

        return [
            {
                "name": "Base Building",
                "weeks": phase_length,
                "focus": "Aerobic endurance and technique",
                "intensity_distribution": {"easy": 70, "moderate": 20, "hard": 10},
            },
            {
                "name": "Intensity Development",
                "weeks": phase_length,
                "focus": "Threshold and VO2 max work",
                "intensity_distribution": {"easy": 50, "moderate": 30, "hard": 20},
            },
            {
                "name": "Speed & Taper",
                "weeks": weeks - (phase_length * 2),
                "focus": "Race-specific speed and taper",
                "intensity_distribution": {"easy": 40, "moderate": 30, "hard": 30},
            },
        ]

    def _get_phase_for_week(self, week: int, phases: list[dict]) -> dict:
        """Determine which phase a week belongs to"""
        cumulative = 0
        for phase in phases:
            cumulative += phase["weeks"]
            if week < cumulative:
                return phase
        return phases[-1]

    def _determine_session_type(self, session_num: int, total_sessions: int) -> str:
        """Determine type of session based on weekly schedule"""
        schedule = {
            5: ["technique", "endurance", "speed", "endurance", "race-pace"],
            4: ["technique", "endurance", "speed", "race-pace"],
            3: ["endurance", "speed", "race-pace"],
        }

        session_types = schedule.get(total_sessions, ["endurance"] * total_sessions)
        return session_types[session_num % len(session_types)]

    def _generate_session(
        self,
        date: datetime,
        session_type: str,
        phase: dict,
        base_volume: int,
        target_times: dict,
    ) -> TrainingSession:
        """Generate a single training session"""

        sets: list[WorkoutSet] = []

        if session_type == "technique":
            sets = [
                WorkoutSet(
                    300, 1, "easy", "easy", "choice", "Warmup - swim/drill/swim"
                ),
                WorkoutSet(
                    50, 8, "1:15", "moderate", "freestyle", "Drill work with fins"
                ),
                WorkoutSet(
                    200, 4, "3:30", "moderate", "freestyle", "Pull with focus on catch"
                ),
                WorkoutSet(100, 6, "2:00", "moderate", "IM", "Stroke technique focus"),
                WorkoutSet(100, 1, "easy", "easy", "choice", "Cooldown"),
            ]
        elif session_type == "endurance":
            sets = [
                WorkoutSet(400, 1, "easy", "easy", "freestyle", "Warmup"),
                WorkoutSet(100, 4, "1:45", "moderate", "IM", "Kick set"),
                WorkoutSet(
                    500, 4, "7:30", "moderate", "freestyle", "Main set - steady pace"
                ),
                WorkoutSet(200, 4, "3:15", "moderate", "choice", "Pull set"),
                WorkoutSet(200, 1, "easy", "easy", "choice", "Cooldown"),
            ]
        elif session_type == "speed":
            sets = [
                WorkoutSet(600, 1, "easy", "easy", "choice", "Warmup"),
                WorkoutSet(50, 8, "1:00", "hard", "freestyle", "Sprint 50s - fast!"),
                WorkoutSet(25, 12, ":45", "hard", "freestyle", "All-out sprints"),
                WorkoutSet(100, 4, "2:30", "moderate", "choice", "Active recovery"),
                WorkoutSet(200, 1, "easy", "easy", "freestyle", "Cooldown"),
            ]
        elif session_type == "race-pace":
            sets = [
                WorkoutSet(500, 1, "easy", "easy", "choice", "Warmup"),
                WorkoutSet(100, 6, "1:45", "race-pace", "freestyle", "Race pace 100s"),
                WorkoutSet(
                    50, 8, ":55", "race-pace", "freestyle", "Build to race pace"
                ),
                WorkoutSet(200, 1, "easy", "easy", "choice", "Cooldown"),
            ]
        else:  # recovery
            sets = [
                WorkoutSet(
                    2000, 1, "easy", "easy", "choice", "Continuous easy swimming"
                )
            ]

        total_yards = sum(s.distance * s.repetitions for s in sets)

        return TrainingSession(
            date=date,
            session_type=session_type,
            total_yards=total_yards,
            duration_minutes=int(total_yards / 30),
            sets=sets,
            focus_area=phase["focus"],
        )

    def _format_goal(self, target_times: dict) -> str:
        """Format goal string"""
        goals = [f"{event}: {time:.2f}" for event, time in target_times.items()]
        return "Target times - " + ", ".join(goals)

    def export_to_text(self, plan: TrainingPlan) -> str:
        """Export plan to readable text format"""
        lines = []
        lines.append("=" * 80)
        lines.append("AQUAFORGE TRAINING PLAN")
        lines.append("=" * 80)
        lines.append(f"\nGoal: {plan.goal}")
        lines.append(
            f"Duration: {plan.start_date.strftime('%m/%d/%Y')} - {plan.end_date.strftime('%m/%d/%Y')}"
        )
        lines.append(f"Weekly Volume: {plan.weekly_volume:,} yards")
        lines.append("\n")

        current_week = None
        for session in plan.sessions:
            week_num = (session.date - plan.start_date).days // 7 + 1

            if week_num != current_week:
                current_week = week_num
                lines.append(f"\n{'=' * 80}")
                lines.append(f"WEEK {week_num}")
                lines.append(f"{'=' * 80}\n")

            lines.append(
                f"\n{session.date.strftime('%A, %B %d')} - {session.session_type.upper()}"
            )
            lines.append(
                f"Total: {session.total_yards} yards | {session.duration_minutes} minutes"
            )
            lines.append(f"Focus: {session.focus_area}\n")

            for i, workout_set in enumerate(session.sets, 1):
                lines.append(
                    f"  {i}. {workout_set.repetitions} x {workout_set.distance} {workout_set.stroke} "
                    f"@ {workout_set.interval} | {workout_set.intensity}"
                )
                lines.append(f"     {workout_set.description}")

        return "\n".join(lines)
