"""
Trackblazer scenario settings — module-level constants.

Following the core/post_career.py pattern: toggle by editing this file directly.
Do NOT add these to config.json or core/config.py.
"""

# Route selection
ROUTE = "triple_tiara"

# Shop automation
AUTO_SHOP = True
COIN_RESERVE = 150  # Save this many coins for the final shop (Twinkle Star races don't award coins)

# Item usage
USE_ITEMS = True
KALE_JUICE_ENERGY_THRESHOLD = 30   # Use Kale Juice when energy drops below this
MAX_KALE_JUICE_STOCKPILE = 3       # Don't buy more than this many
BUY_SCHOLARS_HAT = True            # Buy Scholar's Hat (Fast Learner, 280 coins) if affordable

# Racing
RACE_PRIORITY_GRADES = ["G1", "G2"]  # Grades to prioritize for GP-deficit racing
CANCEL_CONSECUTIVE_RACE_OVERRIDE = False  # TB needs many consecutive races; override core setting

# GP deficit thresholds — if remaining GP / remaining race turns > this ratio, force race
GP_DEFICIT_URGENCY_RATIO = 0.8  # When needed_gp_per_turn exceeds avg GP per race * this, force racing
