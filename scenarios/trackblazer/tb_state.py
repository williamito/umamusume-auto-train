"""
Trackblazer state collection — augments the base state with GP, coins, shop, and item data.

Called after collect_main_state() in the turn loop. Does not modify core/state.py.
"""

import utils.device_action_wrapper as device_action
import utils.constants as constants
from utils.log import debug, warning, info
from utils.tools import get_secs
from scenarios.trackblazer import tb_constants


# ---------------------------------------------------------------------------
# Persistent state across turns (not OCR'd every turn — tracked by buy/use)
# ---------------------------------------------------------------------------
_item_inventory = {
    "kale_juice": 0,
    "cupcake": 0,
    "vita_drink": 0,
    "stat_scroll": 0,
    "manual": 0,
}

_scholars_hat_bought = False
_shop_turns_since_refresh = 0


def reset_inventory():
    """Reset tracked inventory at career start."""
    global _item_inventory, _scholars_hat_bought, _shop_turns_since_refresh
    _item_inventory = {k: 0 for k in _item_inventory}
    _scholars_hat_bought = False
    _shop_turns_since_refresh = 0


def get_inventory():
    """Return a copy of the current inventory."""
    return dict(_item_inventory)


def record_item_bought(item_name, count=1):
    """Record that we bought an item (called by tb_actions shop logic)."""
    if item_name in _item_inventory:
        _item_inventory[item_name] += count
    elif item_name == "scholars_hat":
        global _scholars_hat_bought
        _scholars_hat_bought = True


def record_item_used(item_name, count=1):
    """Record that we used an item (called by tb_actions item logic)."""
    if item_name in _item_inventory:
        _item_inventory[item_name] = max(0, _item_inventory[item_name] - count)


def increment_shop_turn():
    """Increment the shop refresh counter."""
    global _shop_turns_since_refresh
    _shop_turns_since_refresh += 1


def reset_shop_turn_counter():
    """Reset after a shop visit."""
    global _shop_turns_since_refresh
    _shop_turns_since_refresh = 0


# ---------------------------------------------------------------------------
# State augmentation — called from trackblazer_career_lobby
# ---------------------------------------------------------------------------

def collect_trackblazer_state(state_obj):
    """
    Augment the main state object with Trackblazer-specific data.
    Called after collect_main_state() returns.
    """
    year = state_obj.get("year", "")

    # Determine current year phase for GP tracking
    phase = _get_year_phase(year)
    state_obj["tb_year_phase"] = phase
    state_obj["tb_gp_objective"] = tb_constants.GP_OBJECTIVES.get(phase, 0)

    # Item inventory (tracked, not OCR'd)
    state_obj["tb_inventory"] = get_inventory()
    state_obj["tb_has_kale_juice"] = _item_inventory.get("kale_juice", 0) > 0
    state_obj["tb_has_cupcake"] = _item_inventory.get("cupcake", 0) > 0
    state_obj["tb_scholars_hat_bought"] = _scholars_hat_bought

    # Shop availability — check via template match (cheap)
    state_obj["tb_shop_available"] = _detect_shop_available()

    # Check if we're in the finale
    state_obj["is_trackblazer_finale"] = _detect_finale(state_obj)

    # Check if current date has a mandatory Triple Tiara race
    state_obj["tb_mandatory_race"] = tb_constants.TRIPLE_TIARA_RACES.get(year, None)

    # Check if current date has a scheduled recommended race
    state_obj["tb_scheduled_race"] = tb_constants.SCHEDULED_RACE_LOOKUP.get(year, None)

    # Increment shop turn counter
    increment_shop_turn()

    debug(f"[TB] Phase: {phase}, GP obj: {state_obj['tb_gp_objective']}, "
          f"Inventory: {state_obj['tb_inventory']}, "
          f"Shop: {state_obj['tb_shop_available']}, "
          f"Mandatory race: {state_obj['tb_mandatory_race']}, "
          f"Scheduled race: {state_obj['tb_scheduled_race']}")

    return state_obj


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_year_phase(year: str) -> str:
    """Extract the year phase (Junior/Classic/Senior/Finale) from the year string."""
    if "Junior" in year:
        return "Junior"
    elif "Classic" in year:
        return "Classic"
    elif "Senior" in year:
        return "Senior"
    elif "Finale" in year:
        return "Finale"
    return ""


def _detect_shop_available():
    """Check if the shop button is visible on the main screen."""
    import os
    shop_btn_path = tb_constants.TEMPLATES.get("shop_btn", "")
    if not shop_btn_path or not os.path.exists(shop_btn_path):
        debug("[TB] Shop button template not found, skipping shop detection.")
        return False
    result = device_action.locate(shop_btn_path, region_ltrb=constants.SCREEN_BOTTOM_BBOX)
    return result is not None


def _detect_finale(state_obj):
    """Check if we're in the Trackblazer finale (Twinkle Star Climax)."""
    year = state_obj.get("year", "")
    if "Finale" in year:
        return True
    # Could also check for the climax race button template
    import os
    climax_path = tb_constants.TEMPLATES.get("climax_race_btn", "")
    if climax_path and os.path.exists(climax_path):
        result = device_action.locate(climax_path, region_ltrb=constants.SCREEN_BOTTOM_BBOX)
        if result is not None:
            return True
    return False
