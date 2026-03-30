# New-career setup screen templates

Capture these at game resolution (1080p) from a live session.
Exclude emulator chrome — crop only the game UI element.

| File | Screen | What to crop |
|------|--------|-------------|
| career_btn.png | start_1 | Centre text portion of the CAREER button on the home screen; avoid the Event banner that may overlap the edges |
| friends_slot.png | start_5 | The empty green + "Friends" slot rectangle in the Support Formation screen |
| kitasan_black_card.png | start_6 | A crop spanning the horse name "Kitasan Black" and the 4 blue diamond icons from any row in the Borrow Card list; this combination uniquely identifies the card |
| start_career_text.png | start_7/8 | The "Start Career!" text on the button, excluding the chibi character on the left (the chibi changes based on trainee selection) |
| restore_btn.png | energy_1 | Green "Restore" button in the low-TP "Confirm" popup |
| toughness_30_row.png | energy_2 | The Toughness 30 item icon and label text in the Recover TP list; used to locate the row — the Use button is clicked via a pixel offset to the right (_USE_BTN_OFFSET_X in post_career.py) |
| carats_row.png | energy_2 | The Carats item icon and label in the Recover TP list; fallback if Toughness 30 is not available |

## Offset constant

After capturing toughness_30_row.png and carats_row.png, measure the pixel distance
from the left edge of the row template to the centre of its "Use" button.
Update _USE_BTN_OFFSET_X in core/post_career.py with that value.
