"""Frames loaded once at startup, shared by every page.

Importing this module triggers data.load_all() exactly once (Python
caches module imports) — every page imports `state` and reads
`state.loaded`, never calling data.load_all() itself.
"""

import data

loaded = data.load_all()
