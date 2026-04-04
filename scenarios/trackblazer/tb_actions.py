"""
Trackblazer actions — shop, item usage, Triple Tiara forcing, GP deficit racing, Twinkle Star Climax.

New action functions are injected into core.actions module globals at startup so
Action.run() can dispatch to them. Existing functions are never replaced.
"""

import os
import math

import utils.device_action_wrapper as device_action
import utils.constants as constants
from core.actions import Action, start_race, click_race_buttons
from core.ocr import extract_text
from utils.log import debug, info, warning, error
from utils.tools import sleep, get_secs

from scenarios.trackblazer import tb_constants, tb_config
from scenarios.trackblazer.tb_state import (
    record_item_bought, record_item_used, get_inventory,
    reset_shop_turn_counter
)


# ============================================================================
# ACTION FUNCTIONS — these get injected into core.actions globals
# ============================================================================

def do_trackblazer_finale(options=None):
    """
    Handle the Twinkle Star Climax — 3 final races replacing URA Finale.
    Point-based scoring: max 10 per race, 30 total.
    """
    info("[TB] Starting Twinkle Star Climax")

    for race_num in range(1, tb_constants.CLIMAX_RACE_COUNT + 1):
        info(f"[TB] Twinkle Star Climax race {race_num}/{tb_constants.CLIMAX_RACE_COUNT}")

        # Look for the climax race button
        climax_btn_path = tb_constants.TEMPLATES.get("climax_race_btn", "")
        if climax_btn_path and os.path.exists(climax_btn_path):
            device_action.locate_and_click(
                climax_btn_path,
                min_search_time=get_secs(10),
                region_ltrb=constants.SCREEN_BOTTOM_BBOX
            )
        else:
            # Fallback: try the standard race day button
            if not device_action.locate_and_click(
                "assets/buttons/race_day_btn.png",
                min_search_time=get_secs(10),
                region_ltrb=constants.SCREEN_BOTTOM_BBOX
            ):
                # Also try URA race button as last resort
                device_action.locate_and_click(
                    "assets/ura/ura_race_btn.png",
                    min_search_time=get_secs(10),
                    region_ltrb=constants.SCREEN_BOTTOM_BBOX
                )

        sleep(0.5)
        device_action.locate_and_click("assets/buttons/ok_btn.png", min_search_time=get_secs(2))
        sleep(0.5)

        click_race_buttons()
        start_race()

        # Wait for race results and any interstitial screens
        sleep(2)

        # Click through post-race screens
        for _ in range(10):
            if device_action.locate_and_click("assets/buttons/next_btn.png", region_ltrb=constants.SCREEN_BOTTOM_BBOX):
                sleep(0.5)
            elif device_action.locate_and_click("assets/buttons/next2_btn.png", region_ltrb=constants.SCREEN_BOTTOM_BBOX):
                sleep(0.5)
            elif device_action.locate("assets/ui/tazuna_hint.png"):
                break
            else:
                device_action.click(target=constants.SAFE_SPACE_MOUSE_POS)
                sleep(0.5)

    info("[TB] Twinkle Star Climax complete")
    return True


def do_use_recovery_item(options=None):
    """
    Use Kale Juice for energy recovery, then Cupcake if mood dropped.
    This is an action function — it gets called when the strategy decides
    to use items instead of resting.

    Since item usage doesn't consume a turn in Trackblazer, this function
    uses the item and then falls through to do a wit training as the actual
    turn action (similar to skip_turn in core/actions.py).
    """
    info("[TB] Using recovery items instead of resting")

    kale_used = _try_use_item("kale_juice")
    if kale_used:
        record_item_used("kale_juice")
        # Kale Juice drops mood by 1, so use Cupcake to restore
        inventory = get_inventory()
        if inventory.get("cupcake", 0) > 0:
            sleep(0.5)
            cupcake_used = _try_use_item("cupcake")
            if cupcake_used:
                record_item_used("cupcake")

    # After using items, do a wit training as the turn action
    # (same pattern as skip_turn in core/actions.py)
    if options is None:
        options = {}
    options["training_name"] = "wit"
    from core.actions import do_training
    return do_training(options)


# ============================================================================
# SHOP SYSTEM
# ============================================================================

def check_and_use_shop(state):
    """
    Check if the shop is available and buy items based on priority.
    Called each turn in the pre-decision phase.
    """
    if not tb_config.AUTO_SHOP:
        return

    if not state.get("tb_shop_available", False):
        return

    year = state.get("year", "")
    coins = _estimate_coins(state)

    # Reserve coins for the final shop
    if "Senior" in year and ("Late Nov" in year or "Late Dec" in year):
        reserve = tb_config.COIN_RESERVE
    else:
        reserve = 0

    available_coins = max(0, coins - reserve)
    if available_coins <= 0:
        debug(f"[TB] Not enough coins to shop (coins={coins}, reserve={reserve})")
        return

    info(f"[TB] Opening shop (coins ~{coins}, reserve={reserve})")
    _open_and_buy(state, available_coins)
    reset_shop_turn_counter()


def _open_and_buy(state, available_coins):
    """Open the shop and buy items based on priority list."""
    shop_btn_path = tb_constants.TEMPLATES.get("shop_btn", "")
    if not shop_btn_path or not os.path.exists(shop_btn_path):
        debug("[TB] Shop button template missing, cannot open shop")
        return

    # Click shop button
    if not device_action.locate_and_click(shop_btn_path, min_search_time=get_secs(2)):
        warning("[TB] Could not click shop button")
        return

    sleep(1)

    # Verify we're in the shop
    shop_header_path = tb_constants.TEMPLATES.get("shop_header", "")
    if shop_header_path and os.path.exists(shop_header_path):
        if not device_action.locate(shop_header_path, min_search_time=get_secs(2)):
            warning("[TB] Shop header not found, may not be in shop")
            device_action.locate_and_click("assets/buttons/back_btn.png", min_search_time=get_secs(1))
            return

    # Scan for items and buy based on priority
    year = state.get("year", "")
    inventory = get_inventory()

    for item_name in tb_constants.ITEM_PRIORITY:
        cost = tb_constants.ITEM_COSTS.get(item_name, 999)

        # Skip if we can't afford it
        if cost > available_coins:
            debug(f"[TB] Can't afford {item_name} (cost={cost}, available={available_coins})")
            continue

        # Skip Scholar's Hat if already bought or disabled
        if item_name == "scholars_hat":
            if state.get("tb_scholars_hat_bought", False) or not tb_config.BUY_SCHOLARS_HAT:
                continue

        # Skip Kale Juice if at stockpile limit
        if item_name == "kale_juice":
            if inventory.get("kale_juice", 0) >= tb_config.MAX_KALE_JUICE_STOCKPILE:
                continue

        # Skip Grilled Carrots outside Junior Year
        if item_name == "grilled_carrots" and "Junior" not in year:
            continue

        # Try to find the item — either via OCR text or template matching
        found = False

        # Method 1: OCR text matching (for scrolls and manuals with color variants)
        ocr_keyword = tb_constants.ITEM_OCR_KEYWORDS.get(item_name)
        if ocr_keyword:
            found = _find_and_click_item_by_text(ocr_keyword)

        # Method 2: Template matching (for items with unique icons)
        if not found:
            item_template = tb_constants.ITEM_TEMPLATES.get(item_name, "")
            if item_template and os.path.exists(item_template):
                if device_action.locate_and_click(item_template, min_search_time=get_secs(1)):
                    found = True

        if not found:
            debug(f"[TB] Could not find {item_name} in shop")
            continue

        sleep(0.5)
        # Click buy button
        buy_btn_path = tb_constants.TEMPLATES.get("buy_btn", "")
        if buy_btn_path and os.path.exists(buy_btn_path):
            if device_action.locate_and_click(buy_btn_path, min_search_time=get_secs(1)):
                sleep(0.5)
                # Confirm purchase
                device_action.locate_and_click("assets/buttons/ok_btn.png", min_search_time=get_secs(1))
                sleep(0.5)

                record_item_bought(item_name)
                available_coins -= cost
                info(f"[TB] Bought {item_name} (cost={cost}, remaining={available_coins})")

    # Close shop
    device_action.locate_and_click("assets/buttons/back_btn.png", min_search_time=get_secs(1))
    sleep(0.5)


# ============================================================================
# ITEM USAGE (STRATEGIC TIMING)
# ============================================================================

def use_consumable_items(state):
    """
    Use consumable items based on strategic timing.
    Called each turn in the pre-decision phase, before strategy.decide().

    - Kale Juice: when energy < threshold AND high-value training upcoming
    - Cupcake: when mood dropped below GOOD (typically after Kale Juice)
    - Stat scrolls: in Senior Year when close to stat targets

    NOTE: Item usage does NOT consume a turn — it's a pre-action step.
    """
    if not tb_config.USE_ITEMS:
        return

    energy = state.get("energy_level", 100)
    mood = state.get("current_mood", "GREAT")
    year = state.get("year", "")
    inventory = get_inventory()

    # --- Kale Juice for energy ---
    if (inventory.get("kale_juice", 0) > 0
            and energy < tb_config.KALE_JUICE_ENERGY_THRESHOLD
            and _is_high_value_training_turn(state)):
        info(f"[TB] Using Kale Juice (energy={energy:.0f}, threshold={tb_config.KALE_JUICE_ENERGY_THRESHOLD})")
        if _try_use_item("kale_juice"):
            record_item_used("kale_juice")
            sleep(0.5)
            # Kale Juice drops mood — use Cupcake to restore
            if inventory.get("cupcake", 0) > 0:
                if _try_use_item("cupcake"):
                    record_item_used("cupcake")
            return

    # --- Cupcake for mood (independent of Kale Juice) ---
    if (inventory.get("cupcake", 0) > 0
            and mood in ("BAD", "AWFUL", "NORMAL")):
        info(f"[TB] Using Cupcake (mood={mood})")
        if _try_use_item("cupcake"):
            record_item_used("cupcake")
            return


def _is_high_value_training_turn(state):
    """
    Check if this is a high-value training turn worth using Kale Juice for.
    High-value: summer camp, or many support cards present.
    """
    year = state.get("year", "")
    # Summer camp (Early Jul - Late Aug) is always high value
    if "Jul" in year or "Aug" in year:
        return True
    # Late game is high value
    if "Senior" in year:
        return True
    # Default: use it if energy is really low
    return state.get("energy_level", 100) < 20


def _try_use_item(item_name):
    """
    Try to use an item from the inventory.
    Opens the inventory UI, finds the item, and uses it.
    Returns True if successful.
    """
    # Open inventory
    inventory_btn_path = tb_constants.TEMPLATES.get("inventory_btn", "")
    if not inventory_btn_path or not os.path.exists(inventory_btn_path):
        debug(f"[TB] Inventory button template missing, cannot use {item_name}")
        return False

    if not device_action.locate_and_click(inventory_btn_path, min_search_time=get_secs(2)):
        debug(f"[TB] Could not click inventory button for {item_name}")
        return False

    sleep(1)

    # Find the item
    item_template = tb_constants.ITEM_TEMPLATES.get(item_name, "")
    if not item_template or not os.path.exists(item_template):
        debug(f"[TB] Item template for {item_name} not found")
        device_action.locate_and_click("assets/buttons/back_btn.png", min_search_time=get_secs(1))
        return False

    if device_action.locate_and_click(item_template, min_search_time=get_secs(1)):
        sleep(0.5)
        # Confirm use
        device_action.locate_and_click("assets/buttons/ok_btn.png", min_search_time=get_secs(1))
        sleep(0.5)
        info(f"[TB] Used {item_name}")
        # Close inventory
        device_action.locate_and_click("assets/buttons/back_btn.png", min_search_time=get_secs(1))
        return True

    debug(f"[TB] Could not find {item_name} in inventory")
    device_action.locate_and_click("assets/buttons/back_btn.png", min_search_time=get_secs(1))
    return False


# ============================================================================
# RACE LOGIC — Triple Tiara and GP deficit
# ============================================================================

def check_triple_tiara(state, action):
    """
    Check if the current date has a mandatory Triple Tiara race.
    Returns a modified Action if a mandatory race is found, else None.
    """
    mandatory_race = state.get("tb_mandatory_race")
    if mandatory_race:
        action.func = "do_race"
        action["race_name"] = mandatory_race
        action["scheduled_race"] = True
        action["tb_mandatory"] = True
        action["scroll_to_top_wanted"] = False
        action.available_actions.insert(0, "do_race")
        info(f"[TB] Mandatory Triple Tiara race: {mandatory_race}")
        return action
    return None


def check_gp_deficit_race(state, action):
    """
    Check if we're behind on Grade Points and need to race to catch up.
    Uses the recommended race schedule and available races on the current date.

    Returns a modified Action if we should race, else None.
    """
    year = state.get("year", "")
    phase = state.get("tb_year_phase", "")

    if not phase or phase == "Finale":
        return None

    # Check if there's a scheduled recommended race on this date
    scheduled_race = state.get("tb_scheduled_race")
    if scheduled_race and not state.get("tb_mandatory_race"):
        # We have a recommended race — check available races
        races_on_date = constants.RACES.get(year, [])
        for race in races_on_date:
            if race.get("name") == scheduled_race:
                action.func = "do_race"
                action["race_name"] = scheduled_race
                action["scheduled_race"] = True
                action["scroll_to_top_wanted"] = False
                action.available_actions.insert(0, "do_race")
                debug(f"[TB] GP race from schedule: {scheduled_race}")
                return action

    # If no scheduled race, check if there are any G1/G2 races available
    # that match our priority grades
    races_on_date = constants.RACES.get(year, [])
    for grade in tb_config.RACE_PRIORITY_GRADES:
        for race in races_on_date:
            if race.get("grade") == grade:
                action.func = "do_race"
                action["race_name"] = race["name"]
                action["scroll_to_top_wanted"] = False
                action.available_actions.insert(0, "do_race")
                debug(f"[TB] GP deficit race ({grade}): {race['name']}")
                return action

    return None


# ============================================================================
# HELPERS
# ============================================================================

def _find_and_click_item_by_text(keyword):
    """
    Find a shop item by OCR text matching and click it.
    Scans the shop screen for text containing the keyword (case-insensitive).
    Used for items like scrolls and manuals that have multiple color variants
    but share the same label text.

    Returns True if found and clicked, False otherwise.
    """
    from core.ocr import get_reader

    screenshot = device_action.screenshot(region_ltrb=constants.GAME_WINDOW_BBOX)
    import numpy as np
    img_np = np.array(screenshot)

    reader = get_reader()
    results = reader.readtext(img_np, allowlist="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")

    for bbox, text, confidence in results:
        if keyword.lower() in text.lower():
            # bbox is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
            # Click the center of the detected text region
            x_center = int((bbox[0][0] + bbox[2][0]) / 2) + constants.GAME_WINDOW_BBOX[0]
            y_center = int((bbox[0][1] + bbox[2][1]) / 2) + constants.GAME_WINDOW_BBOX[1]
            debug(f"[TB] Found '{keyword}' in text '{text}' at ({x_center}, {y_center})")
            device_action.click(target=(x_center, y_center))
            return True

    debug(f"[TB] OCR text '{keyword}' not found in shop")
    return False


def _estimate_coins(state):
    """
    Estimate current coin count.
    TODO: Replace with OCR reading when screen regions are calibrated.
    For now, estimate based on races completed (100 coins per win).
    """
    # Placeholder: we don't have OCR for coins yet
    # Return a high number so we always attempt to shop
    return 999


def register_actions():
    """
    Inject Trackblazer action functions into core.actions module globals.
    This allows Action.run() to dispatch to them via globals()[self.func].

    Only ADDS new names — never replaces existing functions.
    """
    import core.actions as actions_module

    new_actions = {
        "do_trackblazer_finale": do_trackblazer_finale,
        "do_use_recovery_item": do_use_recovery_item,
    }

    for name, func in new_actions.items():
        if hasattr(actions_module, name):
            debug(f"[TB] Action {name} already registered, skipping")
        else:
            setattr(actions_module, name, func)
            debug(f"[TB] Registered action: {name}")
