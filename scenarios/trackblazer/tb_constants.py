"""
Trackblazer scenario constants — screen regions, GP objectives, item data, race schedules.

Do NOT modify utils/constants.py. All Trackblazer-specific constants live here.
"""
import json
import os

# ---------------------------------------------------------------------------
# Grade Point objectives (reset each year phase, do not carry over)
# ---------------------------------------------------------------------------
GP_OBJECTIVES = {
    "Junior": 60,
    "Classic": 300,
    "Senior": 300,
}

# Special characters with reduced GP requirements
# Key: character trait, Value: overrides for GP_OBJECTIVES
GP_OBJECTIVE_OVERRIDES = {
    # Dirt-focused characters (e.g., Haru Urara): reduced Junior + Classic
    "dirt_focused": {"Junior": 30, "Classic": 200, "Senior": 300},
    # Short-distance only (e.g., Curren Chan): reduced Classic
    "short_only": {"Junior": 60, "Classic": 200, "Senior": 300},
}

# Approximate GP per race grade (1st place)
GP_PER_GRADE = {
    "G1": 35,
    "G2": 18,
    "G3": 9,
    "OP": 4,
}

# Coins per race placing
COINS_PER_PLACE = {
    1: 100,
    2: 70,
    3: 50,
    4: 30,
    5: 20,
}

# ---------------------------------------------------------------------------
# Shop item data
# ---------------------------------------------------------------------------
ITEM_COSTS = {
    "stat_scroll": 120,    # +15 to a stat
    "manual": 60,          # +7 to a stat
    "kale_juice": 80,      # +100 energy, -1 mood
    "cupcake": 40,         # +1 mood
    "grilled_carrots": 60, # Friendship bond boost
    "scholars_hat": 280,   # Fast Learner condition (-10% skill cost)
    "vita_drink": 50,      # Energy recovery (save for summer camp)
}

# Buy priority order — higher index = lower priority
ITEM_PRIORITY = [
    "stat_scroll",
    "manual",
    "kale_juice",
    "cupcake",
    "grilled_carrots",
    "scholars_hat",
    "vita_drink",
]

# ---------------------------------------------------------------------------
# Triple Tiara mandatory races
# ---------------------------------------------------------------------------
TRIPLE_TIARA_RACES = {
    "Classic Year Early Apr": "Oka Sho",        # G1, Mile, 1600m, Hanshin
    "Classic Year Late May": "Japanese Oaks",    # G1, Medium, 2400m, Tokyo
    "Classic Year Late Oct": "Shuka Sho",        # G1, Medium, 2000m, Kyoto
}

# ---------------------------------------------------------------------------
# Recommended G1/G2 races per year for GP farming (Triple Tiara route, mile+medium focus)
# These supplement the mandatory races to meet GP objectives
# ---------------------------------------------------------------------------
RECOMMENDED_RACES = {
    "Junior Year": [
        # Need 60 GP — a few G3 races + debut suffice
        {"name": "Saudi Arabia Royal Cup", "date": "Early Oct", "grade": "G3"},
        {"name": "Artemis Stakes", "date": "Late Oct", "grade": "G3"},
        {"name": "Hanshin Juvenile Fillies", "date": "Early Dec", "grade": "G1"},
        {"name": "Hopeful Stakes", "date": "Late Dec", "grade": "G1"},
    ],
    "Classic Year": [
        # Need 300 GP — Triple Tiara + G1/G2 mile/medium races
        # Triple Tiara handled by TRIPLE_TIARA_RACES
        {"name": "Tulip Sho", "date": "Early Mar", "grade": "G2"},
        {"name": "NHK Mile Cup", "date": "Early May", "grade": "G1"},
        {"name": "Yasuda Kinen", "date": "Early Jun", "grade": "G1"},
        {"name": "Rose Stakes", "date": "Late Sep", "grade": "G2"},
        {"name": "Mile Championship", "date": "Late Nov", "grade": "G1"},
        {"name": "Arima Kinen", "date": "Late Dec", "grade": "G1"},
    ],
    "Senior Year": [
        # Need 300 GP — G1/G2 mile/medium races
        {"name": "Osaka Hai", "date": "Late Mar", "grade": "G1"},
        {"name": "Victoria Mile", "date": "Early May", "grade": "G1"},
        {"name": "Yasuda Kinen", "date": "Early Jun", "grade": "G1"},
        {"name": "Takarazuka Kinen", "date": "Late Jun", "grade": "G1"},
        {"name": "Mainichi Okan", "date": "Early Oct", "grade": "G2"},
        {"name": "Tenno Sho Autumn", "date": "Late Oct", "grade": "G1"},
        {"name": "Mile Championship", "date": "Late Nov", "grade": "G1"},
        {"name": "Arima Kinen", "date": "Late Dec", "grade": "G1"},
    ],
}

# Build a flat lookup: "Year Date" -> race name for quick scheduled race checks
SCHEDULED_RACE_LOOKUP = {}
for _year, _races in RECOMMENDED_RACES.items():
    for _race in _races:
        _key = f"{_year} {_race['date']}"
        SCHEDULED_RACE_LOOKUP[_key] = _race["name"]
# Add Triple Tiara races to the lookup
SCHEDULED_RACE_LOOKUP.update(TRIPLE_TIARA_RACES)

# ---------------------------------------------------------------------------
# Turns where races are available but should NOT be entered
# ---------------------------------------------------------------------------
NEVER_RACE_DATES = set()  # Could add dates here if needed

# ---------------------------------------------------------------------------
# Screen regions — placeholders, need calibration with real Trackblazer screenshots
# Start with URA regions as baseline since Trackblazer's main screen is closer to URA than Unity
# ---------------------------------------------------------------------------
# These will be populated once we have actual game screenshots to measure
# For now, the code uses the default URA regions from utils/constants.py
# TRACKBLAZER_COIN_BBOX = None
# TRACKBLAZER_GP_BBOX = None

# ---------------------------------------------------------------------------
# Template image paths
# ---------------------------------------------------------------------------
ASSET_DIR = "assets/trackblazer"

TEMPLATES = {
    "shop_btn": f"{ASSET_DIR}/shop_btn.png",
    "shop_header": f"{ASSET_DIR}/shop_header.png",
    "buy_btn": f"{ASSET_DIR}/buy_btn.png",
    "coin_icon": f"{ASSET_DIR}/coin_icon.png",
    "climax_race_btn": f"{ASSET_DIR}/climax_race_btn.png",
    "vs_icon": f"{ASSET_DIR}/vs_icon.png",
    "inventory_btn": f"{ASSET_DIR}/inventory_btn.png",
}

# Item template images for shop identification
ITEM_TEMPLATES = {
    "stat_scroll": f"{ASSET_DIR}/item_scroll.png",
    "manual": f"{ASSET_DIR}/item_manual.png",
    "kale_juice": f"{ASSET_DIR}/item_kale.png",
    "cupcake": f"{ASSET_DIR}/item_cupcake.png",
    "grilled_carrots": f"{ASSET_DIR}/item_carrots.png",
    "scholars_hat": f"{ASSET_DIR}/item_hat.png",
    "vita_drink": f"{ASSET_DIR}/item_vita.png",
}

# ---------------------------------------------------------------------------
# Twinkle Star Climax
# ---------------------------------------------------------------------------
CLIMAX_RACE_COUNT = 3       # 3 final races
CLIMAX_MAX_POINTS = 30      # 10 per race, 30 total
