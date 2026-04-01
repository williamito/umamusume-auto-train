import utils.device_action_wrapper as device_action
import utils.constants as constants
from utils.tools import sleep, get_secs
from utils.log import info, warning

# Pixel distance from the CENTRE of an item row template match to the
# centre of its "Use" button on the Recover TP screen (energy_2).
# Measured from sample screenshots at 803×1151 emulator resolution.
_USE_BTN_OFFSET_X = 519


def _click(template, timeout, label):
  """locate_and_click with a warning logged on failure."""
  ok = device_action.locate_and_click(template, min_search_time=timeout, text=label)
  if not ok:
    warning(f"[{label}] Template not found: {template}")
  return ok


def close_career():
  """Navigate all post-career screens after career_lobby() returns.

  Expected entry state: the "Complete Career" button is visible on screen
  (career_lobby sets this as the last visible element before stopping).

  Screens navigated (see assets/post_career/ for templates):
    end_1  → click Complete Career button
    end_2  → click Finish (confirmation dialog)
    end_3  → Career Rank screen, click Next
    end_4  → SPARKS list: detect 3★ primary spark, click Next
    end_5  → Umamusume Details: if 3★, open favourite picker and select carrot icon; click Close
    end_6  → career results screen, click Next
    end_7  → rewards (fans/bond), click Next
    end_8  → rewards (support cards/items), click Next
    end_9  → Career Complete dialog, click To Home
  """
  info("Closing career...")

  # end_1: Complete Career button (already visible when this is called)
  info("[end_1] Clicking Complete Career...")
  _click("assets/buttons/complete_career_btn.png", get_secs(3), "end_1")
  sleep(1)

  info("[end_2] Clicking Finish...")
  _click("assets/post_career/finish_btn.png", get_secs(5), "end_2")
  sleep(1)

  # Career Rank has a long entrance animation; wait up to 25s for Next to appear.
  info("[end_3] Career Rank — clicking Next...")
  _click("assets/buttons/next_btn.png", get_secs(25), "end_3")
  sleep(1)

  info("[end_4] Sparks — clicking Next...")
  is_three_star = _check_three_star_spark()
  _click("assets/buttons/next_btn.png", get_secs(5), "end_4")
  sleep(1)

  info("[end_5] Umamusume Details — closing...")
  if is_three_star:
    info("3★ primary spark detected — favouriting.")
    _favourite_spark()
  _click("assets/buttons/close_btn.png", get_secs(5), "end_5")
  sleep(1)

  for label, desc in (("end_6", "Career Results"), ("end_7", "Rewards (fans)"), ("end_8", "Rewards (items)")):
    info(f"[{label}] {desc} — clicking Next...")
    _click("assets/buttons/next_btn.png", get_secs(8), label)
    sleep(1)

  info("[end_9] Career Complete — clicking To Home...")
  _click("assets/post_career/to_home_btn.png", get_secs(8), "end_9")
  sleep(2)
  info("Career closed. Returned to home.")


def _check_three_star_spark() -> bool:
  """Return True if the first row of the SPARKS list shows 3 gold stars.

  TODO: capture assets/post_career/spark_3star.png from a run that achieves
  a 3★ primary spark, then replace the body of this function with the
  locate() call below:

    first_row_region = constants.add_tuple_elements(
        constants.GAME_WINDOW_BBOX, (60, 200, 0, -680)
    )
    result = device_action.locate(
        "assets/post_career/spark_3star.png",
        min_search_time=get_secs(2),
        region_ltrb=first_row_region,
    )
    if result:
        info("3★ primary spark found.")
    return result is not None
  """
  return False


def _favourite_spark():
  """Open the favourite icon picker and select the carrot icon."""
  # end_4: click the grey carrot icon to open the picker
  device_action.locate_and_click(
    "assets/post_career/grey_carrot_icon.png",
    min_search_time=get_secs(5),
    text="fav_1: open favourite picker"
  )
  sleep(0.5)

  # fav_1: click the coloured carrot icon in the picker grid
  device_action.locate_and_click(
    "assets/post_career/carrot_icon.png",
    min_search_time=get_secs(5),
    text="fav_1: select carrot icon"
  )
  sleep(0.5)

  # fav_2: confirm with OK
  device_action.locate_and_click(
    "assets/buttons/ok_btn.png",
    min_search_time=get_secs(5),
    text="fav_2: OK"
  )
  sleep(1)


def start_new_career():
  """Navigate from the home screen through all setup screens to start a new career.

  Expected entry state: home screen visible after close_career() → To Home.

  Screens navigated (see assets/new_career/ for templates):
    start_1  → click CAREER button on home screen
    start_2  → Scenario Select, click Next (extra wait for render delay)
    start_3  → Trainee Select, click Next
    start_4  → Legacy Select, click Next
    start_5  → Support Formation: click Friends slot (green +)
    start_6  → Borrow Card list: click Kitasan Black 4-diamond row
    start_7  → Support Formation (friend filled): click Start Career!
               If low-TP popup appears, handle energy restoration first.
    start_8  → Final Confirmation dialog, click Start Career!
    start_9  → Intro movie, click fast-forward (>>|)
    start_10 → Quick Mode Settings: cycle skip button to Skip >> then Confirm
  """
  info("Starting new career...")

  info("[start_1] Clicking Career button...")
  _click("assets/new_career/career_btn.png", get_secs(10), "start_1")
  sleep(1)

  info("[start_2] Scenario Select — clicking Next...")
  _click("assets/buttons/next_btn.png", get_secs(8), "start_2")
  sleep(1)

  info("[start_3] Trainee Select — clicking Next...")
  _click("assets/buttons/next_btn.png", get_secs(5), "start_3")
  sleep(1)

  info("[start_4] Legacy Select — clicking Next...")
  _click("assets/buttons/next_btn.png", get_secs(5), "start_4")
  sleep(1)

  info("[start_5] Support Formation — clicking Friends slot...")
  _click("assets/new_career/friends_slot.png", get_secs(5), "start_5")
  sleep(1)

  info("[start_6] Borrow Card — selecting Kitasan Black...")
  _click("assets/new_career/kitasan_black_card.png", get_secs(8), "start_6")
  sleep(1)

  info("[start_7] Support Formation — clicking Start Career!...")
  _click("assets/new_career/start_career_text.png", get_secs(5), "start_7")
  sleep(1)

  _handle_energy_popup()

  info("[start_8] Confirmation — clicking Start Career!...")
  _click("assets/new_career/start_career_text.png", get_secs(5), "start_8")
  sleep(2)

  info("[start_9] Skipping intro...")
  ok = device_action.locate_and_click(
    "assets/buttons/skip_btn.png",
    min_search_time=get_secs(15),
    region_ltrb=constants.SCREEN_BOTTOM_BBOX,
    text="start_9"
  )
  if not ok:
    warning("[start_9] Template not found: assets/buttons/skip_btn.png")
  sleep(1)

  info("[start_10] Setting Quick Mode skip...")
  _set_quick_mode_skip()

  info("Career started. Handing off to career loop.")


def _handle_energy_popup():
  """Handle the optional low-TP restore popup (energy_1–4).

  If the popup is absent this returns immediately. If present:
    energy_1: click Restore
    energy_2: use Toughness 30 if available, otherwise Carats
    energy_3: confirm OK
    energy_4: close the result dialog
  """
  restore_btn = device_action.locate(
    "assets/new_career/restore_btn.png",
    min_search_time=get_secs(2)
  )
  if not restore_btn:
    return

  info("Low-TP popup detected — restoring TP.")
  device_action.click(restore_btn, text="energy_1: Restore")
  sleep(1)

  # energy_2: prefer Toughness 30; fall back to Carats.
  # locate() returns (center_x, center_y); add _USE_BTN_OFFSET_X to reach Use button.
  toughness_row = device_action.locate(
    "assets/new_career/toughness_30_row.png",
    min_search_time=get_secs(3)
  )
  if toughness_row:
    cx, cy = toughness_row
    device_action.click((cx + _USE_BTN_OFFSET_X, cy), text="energy_2: Use Toughness 30")
  else:
    warning("Toughness 30 not found — using Carats instead.")
    carats_row = device_action.locate(
      "assets/new_career/carats_row.png",
      min_search_time=get_secs(3)
    )
    if carats_row:
      cx, cy = carats_row
      device_action.click((cx + _USE_BTN_OFFSET_X, cy), text="energy_2: Use Carats")
  sleep(1)

  # energy_3: confirm the quantity dialog
  device_action.locate_and_click(
    "assets/buttons/ok_btn.png",
    min_search_time=get_secs(5),
    text="energy_3: OK"
  )
  sleep(1)

  # energy_4: dismiss the result
  device_action.locate_and_click(
    "assets/buttons/close_btn.png",
    min_search_time=get_secs(5),
    text="energy_4: Close"
  )
  sleep(1)


def _set_quick_mode_skip():
  """Cycle the Quick Mode skip button to 'Skip >>' then click Confirm.

  The button has three states stored as existing assets:
    skip_off.png  → "Skip Off"  (initial state)
    skip_x1.png   → "Skip >"   (after one click)
    skip_x2.png   → "Skip >>"  (after two clicks; this is the target)

  We detect the current state and click the button until skip_x2 is active,
  then confirm.
  """
  bottom = constants.SCREEN_BOTTOM_BBOX

  for _ in range(3):  # at most 2 clicks needed; 3rd iteration is a safety check
    if device_action.locate("assets/buttons/skip_x2.png", min_search_time=get_secs(1), region_ltrb=bottom):
      break  # already at "Skip >>"
    # click whichever state is currently visible to advance it
    for state in ("skip_off.png", "skip_x1.png"):
      btn = device_action.locate(f"assets/buttons/{state}", min_search_time=0.5, region_ltrb=bottom)
      if btn:
        device_action.click(btn, text=f"start_10: advance skip ({state})")
        sleep(0.5)
        break
  else:
    warning("Quick Mode skip button did not reach 'Skip >>' state.")

  device_action.locate_and_click(
    "assets/buttons/confirm_btn.png",
    min_search_time=get_secs(5),
    text="start_10: Confirm Quick Mode"
  )
  sleep(1)
