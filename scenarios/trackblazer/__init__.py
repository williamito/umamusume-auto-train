"""
TRACKBLAZER SCENARIO SUPPORT

RULE: Do NOT modify core files (core/skeleton.py, core/strategies.py, core/config.py,
core/state.py, utils/constants.py, config.json, config.template.json).
All Trackblazer logic lives in:
  - scenarios/trackblazer/  (this package)
  - trackblazer_loop.py     (entry point)
  - assets/trackblazer/     (template images)
  - assets/scenario_banner/trackblazer.png

This module provides trackblazer_career_lobby(), a replacement for career_lobby()
that inserts 5 Trackblazer-specific hooks into the turn loop. It imports and reuses
all original helper functions without modifying them.

Hook points:
  1. Strategy:          Use TrackblazerStrategy() instead of Strategy()
  2. State augmentation: Call collect_trackblazer_state() after collect_main_state()
  3. Pre-decision:       Check shop + use consumable items
  4. Finale override:    Twinkle Star Climax instead of URA
  5. Race forcing:       Triple Tiara mandatory + GP deficit races
"""

import pyautogui
import os
import cv2
import sys

from utils.tools import sleep, get_secs, click
from core.state import collect_main_state, collect_training_state, clear_aptitudes_cache
from utils.shared import CleanDefaultDict
import core.config as config
from core.actions import Action
import utils.constants as constants
from core.events import select_event
from core.claw_machine import play_claw_machine
from core.skill import buy_skill, init_skill_py

pyautogui.useImageNotFoundException(False)

import core.bot as bot
from utils.log import info, warning, error, debug, log_encoded, args, record_turn, user_info_block, VERSION
from utils.device_action_wrapper import BotStopException
import utils.device_action_wrapper as device_action
from utils.notifications import on_progress, reset_progress_tracking, StopReason

from utils.adb_actions import init_adb

# Trackblazer-specific imports
from scenarios.trackblazer.tb_strategy import TrackblazerStrategy
from scenarios.trackblazer.tb_state import collect_trackblazer_state, reset_inventory
from scenarios.trackblazer.tb_actions import (
    check_and_use_shop, use_consumable_items,
    check_triple_tiara, check_gp_deficit_race,
    register_actions,
)
from scenarios.trackblazer import tb_config

# ---------------------------------------------------------------------------
# Template caching — mirrors core/skeleton.py lines 29-53
# ---------------------------------------------------------------------------

def _cache_templates(templates):
    cache = {}
    image_read_color = cv2.IMREAD_COLOR
    for name, path in templates.items():
        img = cv2.imread(path, image_read_color)
        if img is None:
            warning(f"[TB] Image doesn't exist: {path}")
            continue
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cache[name] = img
    return cache


# Same templates as core/skeleton.py lines 41-53
_base_templates = {
    "next": "assets/buttons/next_btn.png",
    "next2": "assets/buttons/next2_btn.png",
    "event": "assets/icons/event_choice_1.png",
    "inspiration": "assets/buttons/inspiration_btn.png",
    "cancel": "assets/buttons/cancel_btn.png",
    "retry": "assets/buttons/retry_btn.png",
    "tazuna": "assets/ui/tazuna_hint.png",
    "infirmary": "assets/buttons/infirmary_btn.png",
    "claw_btn": "assets/buttons/claw_btn.png",
    "claw_btn_2": "assets/buttons/claw_btn_2.png",
    "ok_2_btn": "assets/buttons/ok_2_btn.png",
}

_cached_templates = _cache_templates(_base_templates)


# ---------------------------------------------------------------------------
# Scenario detection — reuses core/skeleton.py's detect_scenario()
# ---------------------------------------------------------------------------

def _detect_scenario():
    """
    Detect which scenario we're in by matching banner images.
    Mirrors core/skeleton.py detect_scenario() without importing it
    (to avoid pulling the entire skeleton module at import time).
    """
    if not device_action.locate_and_click(
        "assets/buttons/details_btn.png",
        confidence=0.75,
        min_search_time=get_secs(2),
        region_ltrb=constants.SCREEN_TOP_BBOX,
    ):
        error("Details button not found.")
        raise ValueError("Details button not found.")
    sleep(0.5)
    screenshot = device_action.screenshot()
    scenario_banners = {
        f.split(".")[0]: f"assets/scenario_banner/{f}"
        for f in os.listdir("assets/scenario_banner")
        if f.endswith(".png")
    }
    matches = device_action.multi_match_templates(
        scenario_banners, screenshot=screenshot, stop_after_first_match=True
    )
    device_action.locate_and_click("assets/buttons/close_btn.png", min_search_time=get_secs(1))
    sleep(0.5)
    for name, match in matches.items():
        if match:
            return name
    raise ValueError("No scenario banner matched.")


# ---------------------------------------------------------------------------
# Main turn loop — mirrors core/skeleton.py career_lobby() with TB hooks
# ---------------------------------------------------------------------------

LIMIT_TURNS = args.limit_turns
if LIMIT_TURNS is None:
    LIMIT_TURNS = 0

_non_match_count = 0
_action_count = 0
_last_state = CleanDefaultDict()


def _record_and_finalize_turn(state_obj, action):
    """Mirrors core/skeleton.py record_and_finalize_turn()."""
    global _last_state, _action_count
    user_info_block(state_obj, _last_state, action)
    record_turn(state_obj, _last_state, action)
    _last_state = state_obj

    _action_count += 1
    if LIMIT_TURNS > 0:
        if _action_count >= LIMIT_TURNS:
            info(f"Completed {_action_count} actions, stopping bot as requested.")
            device_action.stop_bot(
                StopReason.FINISHED,
                f"assets/notifications/{config.SUCCESS_NOTIFICATION}",
                volume=config.NOTIFICATION_VOLUME,
            )


def _validate_turn(state):
    """Mirrors core/skeleton.py validate_turn()."""
    if state["turn"] == -1:
        return False
    return True


def _check_configured_bot_stop(state):
    """Mirrors core/skeleton.py check_configured_bot_stop()."""
    def bot_stop_func():
        device_action.stop_bot(
            StopReason.FINISHED,
            f"assets/notifications/{config.SUCCESS_NOTIFICATION}",
            volume=config.NOTIFICATION_VOLUME,
        )

    for turn in config.STOP_AT_TURNS:
        if state["year"] in turn:
            if "Finale Underway" in turn:
                finale_type = turn.split(" ")[2]
                debug(f"check_configured_bot_stop {turn} {finale_type} {state['criteria']} {state['turn']}")
                if finale_type in state["criteria"] and state["turn"] == "Race Day":
                    bot_stop_func()
            else:
                debug(f"check_configured_bot_stop {turn} {state['year']}")
                bot_stop_func()


def trackblazer_career_lobby(dry_run_turn=False):
    """
    Replacement for career_lobby() with Trackblazer hooks.
    Structurally mirrors core/skeleton.py career_lobby() with 5 insertion points.

    See module docstring for hook descriptions.
    """
    global _last_state, _action_count, _non_match_count

    _non_match_count = 0
    _action_count = 0
    sleep(1)
    bot.PREFERRED_POSITION_SET = False
    constants.SCENARIO_NAME = ""
    clear_aptitudes_cache()
    reset_inventory()

    # HOOK 1: Use TrackblazerStrategy instead of Strategy
    strategy = TrackblazerStrategy()

    init_adb()
    init_skill_py()
    reset_progress_tracking()
    _last_state = CleanDefaultDict()

    # Register Trackblazer action functions into core.actions globals
    register_actions()

    try:
        while bot.is_bot_running:
            sleep(1)
            device_action.flush_screenshot_cache()
            screenshot = device_action.screenshot()

            if _non_match_count > 20:
                info("Career lobby stuck, quitting.")
                complete_career_btn = device_action.locate(
                    "assets/buttons/complete_career_btn.png",
                    min_search_time=get_secs(2),
                )
                if complete_career_btn is not None:
                    device_action.stop_bot(
                        StopReason.FINISHED,
                        f"assets/notifications/{config.SUCCESS_NOTIFICATION}",
                        volume=config.NOTIFICATION_VOLUME,
                    )
                else:
                    device_action.stop_bot(
                        StopReason.STUCK,
                        f"assets/notifications/{config.ERROR_NOTIFICATION}",
                        volume=config.NOTIFICATION_VOLUME,
                    )

            # --- Template matching (mirrors skeleton.py lines 124-210) ---
            matches = device_action.match_cached_templates(
                _cached_templates,
                region_ltrb=constants.GAME_WINDOW_BBOX,
                threshold=0.9,
                stop_after_first_match=True,
            )

            def click_match(matches):
                if matches and len(matches) > 0:
                    x, y, w, h = matches[0]
                    cx = x + w // 2
                    cy = y + h // 2
                    return device_action.click(target=(cx, cy), text=f"Clicked match: {matches[0]}")
                return False

            if len(matches.get("event", [])) > 0:
                select_event()
                continue
            if click_match(matches.get("inspiration")):
                debug("Pressed inspiration.")
                _non_match_count = 0
                continue
            if click_match(matches.get("next")):
                debug("Pressed next.")
                _non_match_count = 0
                continue
            if click_match(matches.get("next2")):
                debug("Pressed next2.")
                _non_match_count = 0
                continue
            if matches.get("cancel", False):
                clock_icon = device_action.match_template(
                    "assets/icons/clock_icon.png", screenshot=screenshot, threshold=0.9
                )
                if clock_icon:
                    debug("Lost race, wait for input.")
                    _non_match_count += 1
                elif click_match(matches.get("cancel")):
                    debug("Pressed cancel.")
                    _non_match_count = 0
                continue
            if click_match(matches.get("retry")):
                debug("Pressed retry.")
                _non_match_count = 0
                continue

            # Claw machine handling
            if matches.get("claw_btn", False) or matches.get("claw_btn_2", False):
                if not config.USE_SKIP_CLAW_MACHINE:
                    info("Claw machine detected, but skip is disabled. Stopping the bot for manual play.")
                    device_action.stop_bot(
                        StopReason.CLAW_MACHINE,
                        f"assets/notifications/{config.INFO_NOTIFICATION}",
                        volume=config.NOTIFICATION_VOLUME,
                    )
                    continue

                claw_match = ""
                if matches.get("claw_btn", False):
                    claw_match = matches["claw_btn"][0]
                elif matches.get("claw_btn_2", False):
                    claw_match = matches["claw_btn_2"][0]
                else:
                    warning("Got into claw machine match but there's no match in both versions.")
                    continue

                sleep(0.5)
                play_claw_machine(claw_match)
                debug("Played claw machine.")
                _non_match_count = 0
                continue

            if click_match(matches.get("ok_2_btn")):
                debug("Pressed Okay button.")
                _non_match_count = 0
                continue

            # --- Tazuna check (main screen ready) ---
            if not matches.get("tazuna"):
                print(".", end="")
                _non_match_count += 1
                continue
            else:
                sys.stdout.write("\r\x1b[2K")
                sys.stdout.flush()
                debug("Tazuna matched, moving to state collection.")
                if constants.SCENARIO_NAME == "":
                    scenario_name = _detect_scenario()
                    info(f"Scenario detected: {scenario_name}")
                    constants.SCENARIO_NAME = scenario_name
                    if scenario_name != "trackblazer":
                        warning(
                            f"[TB] Expected trackblazer scenario but detected '{scenario_name}'. "
                            "Continuing anyway — the Trackblazer hooks will still run."
                        )
                _non_match_count = 0

            device_action.flush_screenshot_cache()
            debug(f"Bot version: {VERSION}")

            # --- State collection ---
            action = Action()
            state_obj = collect_main_state()

            # HOOK 2: Augment state with Trackblazer-specific data
            state_obj = collect_trackblazer_state(state_obj)

            if not _validate_turn(state_obj):
                info("Couldn't read turn text correctly, retrying.")
                continue

            on_progress(state_obj)
            _check_configured_bot_stop(state_obj)

            # HOOK 3: Pre-decision — shop and item usage
            check_and_use_shop(state_obj)
            use_consumable_items(state_obj)
            # Re-flush after shop/item UI interactions
            device_action.flush_screenshot_cache()

            # --- Race Day handling ---
            action["scroll_to_top_wanted"] = False

            if state_obj["turn"] == "Race Day":
                # HOOK 4: Trackblazer finale override
                if state_obj.get("is_trackblazer_finale", False):
                    from scenarios.trackblazer.tb_actions import do_trackblazer_finale
                    info("[TB] Race Day during finale — Twinkle Star Climax")
                    action.func = "do_trackblazer_finale"
                    action["year"] = state_obj["year"]
                    if action.run():
                        _record_and_finalize_turn(state_obj, action)
                        continue
                else:
                    action.func = "do_race"
                    action["is_race_day"] = True
                    action["year"] = state_obj["year"]
                    info("Race Day")
                    if action.run():
                        _record_and_finalize_turn(state_obj, action)
                        continue
                    else:
                        action.func = None
                        del action.options["is_race_day"]
                        del action.options["year"]

            # HOOK 5: Force Triple Tiara / GP deficit races
            forced_action = check_triple_tiara(state_obj, action)
            if forced_action:
                debug(f"[TB] Forcing race: {forced_action['race_name']}")
                buy_skill(state_obj, _action_count, race_check=True)
                if forced_action.run():
                    _record_and_finalize_turn(state_obj, forced_action)
                    continue
                else:
                    action.func = None
                    action.options.pop("race_name", None)

            # Check for scheduled Trackblazer races (GP farming)
            action = strategy.check_scheduled_races(state_obj, action)
            if "race_name" in action.options and action.func == "do_race":
                debug(f"[TB] Taking scheduled race: {action['race_name']}")
                buy_skill(state_obj, _action_count, race_check=True)
                if action.run():
                    _record_and_finalize_turn(state_obj, action)
                    continue
                else:
                    action.func = None
                    action.options.pop("race_name", None)
                    action.options.pop("race_image_path", None)

            # Check for GP deficit races (non-scheduled G1/G2)
            gp_action = check_gp_deficit_race(state_obj, action)
            if gp_action:
                debug(f"[TB] GP deficit race: {gp_action['race_name']}")
                buy_skill(state_obj, _action_count, race_check=True)
                if gp_action.run():
                    _record_and_finalize_turn(state_obj, gp_action)
                    continue
                else:
                    action.func = None
                    action.options.pop("race_name", None)

            # Mission races (reuse existing logic)
            if config.DO_MISSION_RACES_IF_POSSIBLE and state_obj.get("race_mission_available", False):
                debug("Mission race logic entered.")
                action.func = "do_race"
                action["race_name"] = "any"
                action["race_image_path"] = "assets/ui/match_track.png"
                action["race_mission_available"] = True
                buy_skill(state_obj, _action_count, race_check=True)
                if action.run():
                    _record_and_finalize_turn(state_obj, action)
                    continue
                else:
                    action.func = None
                    action.options.pop("race_name", None)
                    action.options.pop("race_image_path", None)
                    action.options.pop("race_mission_available", None)

            # Goal races (existing logic)
            if "Achieved" not in state_obj.get("criteria", ""):
                action = strategy.decide_race_for_goal(state_obj, action)
                if action.func == "do_race":
                    debug(f"Taking goal race: {action.func}")
                    buy_skill(state_obj, _action_count, race_check=True)
                    if action.run():
                        _record_and_finalize_turn(state_obj, action)
                        continue
                    else:
                        action.func = None

            # --- Training decision ---
            training_function_name = strategy.get_training_template(state_obj)["training_function"]

            state_obj = collect_training_state(state_obj, training_function_name)
            if state_obj.get("training_locked", False):
                state_obj = collect_training_state(state_obj, training_function_name, check_stat_gains=True)

            if not state_obj.get("training_results", False):
                info("Couldn't collect training state, retrying turn from top.")
                continue

            buy_skill(state_obj, _action_count)

            log_encoded(f"{state_obj}", "Encoded state: ")
            debug(f"State: {state_obj}")

            # Strategy decision (uses TrackblazerStrategy with overrides)
            action = strategy.decide(state_obj, action)

            if isinstance(action, dict):
                error(f"Strategy returned an invalid action. Returned: {action}")
            elif action.func == "no_action":
                info("State is invalid, retrying...")
                debug(f"State: {state_obj}")
            elif action.func == "skip_turn":
                info("Skipping turn, retrying...")
            else:
                debug(f"Taking action: {action.func}")

                if action.func == "do_race":
                    buy_skill(state_obj, _action_count, race_check=True)
                if dry_run_turn:
                    info("Dry run turn, quitting.")
                    device_action.stop_bot(
                        StopReason.FINISHED,
                        f"assets/notifications/{config.SUCCESS_NOTIFICATION}",
                        volume=config.NOTIFICATION_VOLUME,
                    )
                elif not action.run():
                    if action.available_actions:
                        action.available_actions.pop(0)
                    else:
                        warning("No more actions remaining. Retrying turn.")
                        _non_match_count += 1
                        continue

                    if action.options.get("race_mission_available") and action.func == "do_race":
                        info("Couldn't match race mission to aptitudes, trying next action.")
                    else:
                        info(f"Action {action.func} failed, trying other actions.")
                    debug(f"Available actions: {action.available_actions}")

                    for function_name in action.available_actions:
                        sleep(1)
                        debug(f"Trying action: {function_name}")
                        action.func = function_name
                        if action.func == "do_race":
                            buy_skill(state_obj, _action_count, race_check=True)
                        if action.run():
                            break
                        debug(f"Action {function_name} failed, trying other actions.")

                _record_and_finalize_turn(state_obj, action)
                continue

    except BotStopException as e:
        info(f"{e}")
        return
