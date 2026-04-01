import utils.device_action_wrapper as device_action
import utils.constants as constants
from utils.tools import sleep, get_secs
from utils.log import info, warning

# Pixel distance from the CENTRE of an item row template match to the
# centre of its "Use" button on the Recover TP screen (energy_2).
# Measured from sample screenshots at 803×1151 emulator resolution.
_USE_BTN_OFFSET_X = 519


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
  device_action.locate_and_click(
    "assets/buttons/complete_career_btn.png",
    min_search_time=get_secs(3),
    text="end_1: Complete Career"
  )
  sleep(1)

  # end_2: Confirmation dialog — click Finish
  device_action.locate_and_click(
    "assets/post_career/finish_btn.png",
    min_search_time=get_secs(5),
    text="end_2: Finish"
  )
  sleep(1)

  # end_3: Career Rank screen — click Next
  device_action.locate_and_click(
    "assets/buttons/next_btn.png",
    min_search_time=get_secs(5),
    text="end_3: Next (Career Rank)"
  )
  sleep(1)

  # end_4: SPARKS list — detect 3★ primary spark then click Next
  is_three_star = _check_three_star_spark()
  device_action.locate_and_click(
    "assets/buttons/next_btn.png",
    min_search_time=get_secs(5),
    text="end_4: Next (Sparks)"
  )
  sleep(1)

  # end_5: Umamusume Details — optionally favourite, then close
  if is_three_star:
    info("3★ primary spark detected — favouriting.")
    _favourite_spark()
  device_action.locate_and_click(
    "assets/buttons/close_btn.png",
    min_search_time=get_secs(5),
    text="end_5: Close (Umamusume Details)"
  )
  sleep(1)

  # end_6–8: three Next buttons (career results, rewards/fans, rewards/items)
  for label in ("end_6", "end_7", "end_8"):
    device_action.locate_and_click(
      "assets/buttons/next_btn.png",
      min_search_time=get_secs(8),
      text=f"{label}: Next"
    )
    sleep(1)

  # end_9: Career Complete dialog — To Home
  device_action.locate_and_click(
    "assets/post_career/to_home_btn.png",
    min_search_time=get_secs(8),
    text="end_9: To Home"
  )
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

  # start_1: home screen — click CAREER button (centre crop, avoids Event banner)
  device_action.locate_and_click(
    "assets/new_career/career_btn.png",
    min_search_time=get_secs(10),
    text="start_1: Career"
  )
  sleep(1)

  # start_2: Scenario Select — extra wait; buttons can be slow to become clickable
  device_action.locate_and_click(
    "assets/buttons/next_btn.png",
    min_search_time=get_secs(8),
    text="start_2: Next (Scenario Select)"
  )
  sleep(1)

  # start_3: Trainee Select
  device_action.locate_and_click(
    "assets/buttons/next_btn.png",
    min_search_time=get_secs(5),
    text="start_3: Next (Trainee Select)"
  )
  sleep(1)

  # start_4: Legacy Select
  device_action.locate_and_click(
    "assets/buttons/next_btn.png",
    min_search_time=get_secs(5),
    text="start_4: Next (Legacy Select)"
  )
  sleep(1)

  # start_5: Support Formation — click the empty Friends slot (green +)
  device_action.locate_and_click(
    "assets/new_career/friends_slot.png",
    min_search_time=get_secs(5),
    text="start_5: Friends slot"
  )
  sleep(1)

  # start_6: Borrow Card list — find and click Kitasan Black 4-diamond row.
  # The template covers the horse name "Kitasan Black" + 4 blue diamond icons
  # so it uniquely identifies the desired card regardless of trainer name.
  # Clicking the row auto-closes the dialog and fills the Friends slot.
  device_action.locate_and_click(
    "assets/new_career/kitasan_black_card.png",
    min_search_time=get_secs(8),
    text="start_6: Kitasan Black card"
  )
  sleep(1)

  # start_7: Support Formation (Friends slot now filled) — Start Career!
  # Then check for the optional low-TP popup before proceeding.
  device_action.locate_and_click(
    "assets/new_career/start_career_text.png",
    min_search_time=get_secs(5),
    text="start_7: Start Career!"
  )
  sleep(1)

  # Handle low-TP popup if it appears (energy_1–4)
  _handle_energy_popup()

  # start_8: Final Confirmation dialog — Start Career! (same template)
  device_action.locate_and_click(
    "assets/new_career/start_career_text.png",
    min_search_time=get_secs(5),
    text="start_8: Start Career! (confirmation)"
  )
  sleep(2)

  # start_9: Intro movie — click fast-forward (>>|)
  device_action.locate_and_click(
    "assets/buttons/skip_btn.png",
    min_search_time=get_secs(15),
    region_ltrb=constants.SCREEN_BOTTOM_BBOX,
    text="start_9: fast-forward intro"
  )
  sleep(1)

  # start_10a–c: Quick Mode Settings — cycle to "Skip >>" then Confirm
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
