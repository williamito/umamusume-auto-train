import sys
import subprocess
import warnings
warnings.filterwarnings(
  "ignore",
  category=UserWarning,
  module=r"torch\.utils\.data\.dataloader"
)
MIN = (3, 10)
MAX = (3, 14)

if not (MIN <= sys.version_info < MAX):
  out = subprocess.check_output(
    ["py", "--list"],
    text=True,
    stderr=subprocess.DEVNULL
  )

  candidates = []
  for line in out.splitlines():
    line = line.strip()
    if line.startswith("-V:"):
      v = line.split()[0][3:]
      try:
        major, minor = map(int, v.split("."))
        if (major, minor) >= MIN and (major, minor) < MAX:
          candidates.append(v)
      except ValueError:
        pass

  if not candidates:
    raise RuntimeError("No compatible Python 3.10-3.13 installed")

  best = sorted(candidates)[-1]

  p = subprocess.Popen(
    ["py", f"-{best}", *sys.argv],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr
  )
  p.wait()
  sys.exit(p.returncode)

from utils.tools import sleep
import threading
import uvicorn
import keyboard
import socket

from utils.log import info, error, init_logging, args
from core.skeleton import career_lobby
from core.post_career import close_career, start_new_career
import core.config as config
import core.bot as bot
import utils.device_action_wrapper as device_action
from server.main import app
from update_config import update_config
from utils.notifications import on_started

# Re-use focus_umamusume from main without importing main's __main__ block
from main import focus_umamusume


def loop():
  config.reload_config()

  if args.use_adb:
    bot.use_adb = True
    bot.device_id = args.use_adb
  else:
    bot.use_adb = config.USE_ADB
    if config.DEVICE_ID and config.DEVICE_ID != "":
      bot.device_id = config.DEVICE_ID

  while bot.is_bot_running:
    config.reload_config()
    if not focus_umamusume():
      error("Failed to focus Umamusume window")
      break
    on_started()
    info(f"Config: {config.CONFIG_NAME}")
    career_lobby()

    # career_lobby() always returns via BotStopException, which sets
    # is_bot_running=False. Restore it so screenshots work for the
    # end-state check below (and for close_career/start_new_career).
    bot.is_bot_running = True

    # Check whether the career actually finished normally. If the user
    # pressed F1 to stop mid-career, the button won't be on screen and
    # we fall through to the bot.is_bot_running=False line below.
    if not device_action.locate("assets/buttons/complete_career_btn.png", min_search_time=1):
      info("Career did not finish normally — stopping loop.")
      bot.is_bot_running = False
      break

    close_career()
    start_new_career()

  bot.is_bot_running = False
  info("Auto-loop stopped.")


def run_start_career_only():
  """Run just start_new_career() for testing; mirrors the setup in loop()."""
  config.reload_config()
  if args.use_adb:
    bot.use_adb = True
    bot.device_id = args.use_adb
  else:
    bot.use_adb = config.USE_ADB
    if config.DEVICE_ID and config.DEVICE_ID != "":
      bot.device_id = config.DEVICE_ID
  if not focus_umamusume():
    error("Failed to focus Umamusume window")
    return
  bot.is_bot_running = True
  try:
    start_new_career()
  finally:
    bot.is_bot_running = False


def hotkey_listener():
  # ctrl+<hotkey> runs only start_new_career() for testing the start flow.
  keyboard.add_hotkey(f"ctrl+{bot.hotkey}", lambda: threading.Thread(
    target=run_start_career_only, daemon=True
  ).start())

  while True:
    keyboard.wait(bot.hotkey)
    if not bot.is_bot_running:
      print("[BOT] Starting auto-loop...")
      bot.is_bot_running = True
      t = threading.Thread(target=loop, daemon=True)
      t.start()
    else:
      print("[BOT] Stopping auto-loop after current career...")
      bot.is_bot_running = False
    sleep(0.5)


def is_port_available(host, port):
  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.close()
    return True
  except OSError:
    return False


def start_server():
  host = "127.0.0.1"
  start_port = 8000
  end_port = 8010
  for port in range(start_port, end_port):
    if is_port_available(host, port):
      bot.instance = port - start_port + 1
      bot.hotkey = f"f{bot.instance}"
      break
    else:
      print(f"[INFO] Port {port} is already in use. Trying {port + 1}...")

  threading.Thread(target=hotkey_listener, daemon=True).start()
  server_config = uvicorn.Config(app, host=host, port=port, workers=1, log_level="warning")
  server = uvicorn.Server(server_config)
  init_logging()
  info(f"Press '{bot.hotkey}' to start/stop the auto-loop. Press 'ctrl+{bot.hotkey}' to test start_new_career() only.")
  info(f"[SERVER] Open http://{host}:{port} to configure the bot.")
  server.run()


if __name__ == "__main__":
  update_config()
  config.reload_config()
  start_server()
