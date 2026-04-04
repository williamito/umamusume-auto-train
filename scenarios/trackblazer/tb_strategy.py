"""
TrackblazerStrategy — subclass of core Strategy with Trackblazer-specific overrides.

Does not modify core/strategies.py. Uses inheritance to override behavior.
"""

from core.strategies import Strategy
from core.actions import Action
from utils.log import debug, info
from utils.tools import remove_if_exists
import utils.constants as constants
from scenarios.trackblazer import tb_constants, tb_config


class TrackblazerStrategy(Strategy):
    """
    Extends the base Strategy with Trackblazer-specific decision overrides:
    1. Don't rest if recovery items are available (use items instead)
    2. Override consecutive race cancellation (TB needs many consecutive races)
    3. Adjust energy management for race-heavy schedule
    """

    def evaluate_training_alternatives(self, state, action):
        """
        Override: When recovery items (Kale Juice) are available, prevent
        the base strategy from choosing rest. Items will handle energy recovery
        in the pre-action step of the turn loop.
        """
        # If we have Kale Juice, remove rest as an option so the base logic
        # doesn't fall back to it — the item system handles energy
        if state.get("tb_has_kale_juice", False) and state.get("energy_level", 100) >= 20:
            remove_if_exists(action.available_actions, ["do_rest"])
            debug("[TB] Removed do_rest from alternatives — Kale Juice available for energy")

        action = super().evaluate_training_alternatives(state, action)

        return action

    def decide(self, state, action):
        """
        Override: Post-decision correction.
        If the base strategy decided to rest but we have recovery items,
        redirect to item usage instead.
        """
        action = super().decide(state, action)

        # Post-decision override: use recovery item instead of resting
        if action.func == "do_rest" and state.get("tb_has_kale_juice", False):
            action.func = "do_use_recovery_item"
            debug("[TB] Overriding rest → use recovery item (Kale Juice available)")

        return action

    def check_scheduled_races(self, state, action):
        """
        Override: Use Trackblazer race schedule instead of config.RACE_SCHEDULE.
        Checks for mandatory Triple Tiara races and recommended GP races.
        """
        date = state["year"]

        # Check mandatory Triple Tiara races first — these are never skipped
        mandatory_race = tb_constants.TRIPLE_TIARA_RACES.get(date)
        if mandatory_race:
            action.func = "do_race"
            action["race_name"] = mandatory_race
            action["scheduled_race"] = True
            action["tb_mandatory"] = True
            action.available_actions.insert(0, "do_race")
            info(f"[TB] Mandatory Triple Tiara race: {mandatory_race}")
            return action

        # Check recommended races for GP farming
        scheduled_race = tb_constants.SCHEDULED_RACE_LOOKUP.get(date)
        if scheduled_race:
            action["race_name"] = scheduled_race
            action["scheduled_race"] = True
            action.available_actions.insert(0, "do_race")
            debug(f"[TB] Scheduled race: {scheduled_race}")
            return action

        # Fall through to base scheduled races (in case user has custom schedule too)
        return super().check_scheduled_races(state, action)
