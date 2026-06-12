"""
game_logic.py
=============
Pure game-logic helpers (no Streamlit, no Firebase).

Changes vs original:
  - generate_map() now places ~10 obstacles total (reduced from heavy clusters).
  - All other logic (powerups, collision, spawn, fmt_time) unchanged.
"""

import random
import time

# ─── Constants ────────────────────────────────────────────────────────────────
MAP_SIZE         = 20    # 20×20 grid
GAME_DURATION    = 120   # seconds (2 minutes)
POWERUP_DURATION = 5     # seconds for speed / shield boosts
SPEED_BOOST      = 2     # multiplier when speed powerup active

# ─── Tile IDs ─────────────────────────────────────────────────────────────────
TILE_EMPTY   = 0
TILE_TREE    = 1
TILE_ROCK    = 2
TILE_BUSH    = 3
TILE_WATER   = 4
TILE_HEART   = 5   # powerup: male speed boost
TILE_FLOWER  = 6   # powerup: female speed boost
TILE_STAR    = 7   # powerup: shield
TILE_COMPASS = 8   # powerup: show female direction

# Emoji rendering for each tile
TILE_EMOJIS = {
    TILE_EMPTY:   "⬛",
    TILE_TREE:    "🌳",
    TILE_ROCK:    "🪨",
    TILE_BUSH:    "🌿",
    TILE_WATER:   "💧",
    TILE_HEART:   "❤️",
    TILE_FLOWER:  "🌸",
    TILE_STAR:    "⭐",
    TILE_COMPASS: "🔍",
}

# Tiles that block movement
BLOCKED_TILES = {TILE_TREE, TILE_ROCK, TILE_WATER}

# Background colour hints per tile (for HTML rendering)
TILE_COLORS = {
    TILE_EMPTY:   "#0d0d22",
    TILE_TREE:    "#0e2010",
    TILE_ROCK:    "#1e1e1e",
    TILE_BUSH:    "#122012",
    TILE_WATER:   "#060e28",
    TILE_HEART:   "#280a0a",
    TILE_FLOWER:  "#280a18",
    TILE_STAR:    "#1e1a08",
    TILE_COMPASS: "#0a181e",
}


# ─── Map generation ───────────────────────────────────────────────────────────
def generate_map() -> list:
    """
    Generate a 20×20 map with sparse obstacles (~10 total blocking tiles).
    Returns a 2D list (row-major: map[y][x]).

    Obstacle strategy:
      - Border trees on all 4 edges (structural walls).
      - ~5 interior trees/rocks placed as single-tile obstacles.
      - ~3 water tiles placed as single-tile obstacles.
      - ~2 bush tiles (non-blocking, decorative cover).
      - Powerups: 2 hearts, 2 flowers, 1 star, 1 compass.
    """
    grid = [[TILE_EMPTY] * MAP_SIZE for _ in range(MAP_SIZE)]

    # ── Border walls (trees) ──────────────────────────────────────────────────
    for i in range(MAP_SIZE):
        grid[0][i]            = TILE_TREE
        grid[MAP_SIZE - 1][i] = TILE_TREE
        grid[i][0]            = TILE_TREE
        grid[i][MAP_SIZE - 1] = TILE_TREE

    # ── Interior blocking obstacles (~10 total cells) ─────────────────────────
    # Place as individual tiles spread around the interior to keep it sparse
    blocking_specs = [
        # (tile_type, list_of_(x,y) positions)
        (TILE_TREE,  [(5, 5), (14, 5), (5, 14), (14, 14)]),   # 4 corner trees
        (TILE_ROCK,  [(10, 7), (10, 12)]),                      # 2 central rocks
        (TILE_WATER, [(7, 10), (13, 10), (10, 10)]),            # 3 water tiles (horizontal strip)
    ]
    for tile, positions in blocking_specs:
        for x, y in positions:
            if 1 <= x < MAP_SIZE - 1 and 1 <= y < MAP_SIZE - 1:
                if grid[y][x] == TILE_EMPTY:
                    grid[y][x] = tile

    # ── Decorative bushes (non-blocking) ─────────────────────────────────────
    _place_scattered(grid, TILE_BUSH, count=4)

    # ── Powerups ──────────────────────────────────────────────────────────────
    _place_scattered(grid, TILE_HEART,   count=2)
    _place_scattered(grid, TILE_FLOWER,  count=2)
    _place_scattered(grid, TILE_STAR,    count=1)
    _place_scattered(grid, TILE_COMPASS, count=1)

    return grid


def _place_scattered(grid, tile, count):
    rows = len(grid)
    cols = len(grid[0])
    placed   = 0
    attempts = 0
    while placed < count and attempts < 500:
        attempts += 1
        x = random.randint(2, cols - 3)
        y = random.randint(2, rows - 3)
        if grid[y][x] == TILE_EMPTY:
            grid[y][x] = tile
            placed += 1


# ─── Spawn positions ──────────────────────────────────────────────────────────
def get_valid_spawn(grid) -> tuple:
    """Return two valid empty spawn positions (far apart) for male and female."""
    empties = []
    for y in range(len(grid)):
        for x in range(len(grid[y])):
            if grid[y][x] == TILE_EMPTY:
                empties.append([x, y])

    if len(empties) < 2:
        return [2, 2], [MAP_SIZE - 3, MAP_SIZE - 3]

    mid = MAP_SIZE // 2
    left_side  = [p for p in empties if p[0] < mid]
    right_side = [p for p in empties if p[0] >= mid]

    male_pos   = random.choice(left_side  if left_side  else empties)
    female_pos = random.choice(right_side if right_side else empties)
    return male_pos, female_pos


# ─── Collision ────────────────────────────────────────────────────────────────
def check_collision(pos_a, pos_b) -> bool:
    if not pos_a or not pos_b:
        return False
    return pos_a[0] == pos_b[0] and pos_a[1] == pos_b[1]


# ─── Power-up application ────────────────────────────────────────────────────
def apply_powerup(player: dict, role: str, tile: int,
                  room: dict, now: float) -> tuple:
    """Apply powerup effect. Returns (player, room)."""
    duration = POWERUP_DURATION

    if tile == TILE_HEART:
        target_role = "male"
    elif tile == TILE_FLOWER:
        target_role = "female"
    elif tile == TILE_STAR:
        target_role = role
    elif tile == TILE_COMPASS:
        target_role = "male"
    else:
        return player, room

    def _apply_to(p: dict, t: int) -> dict:
        p = dict(p)
        if t in (TILE_HEART, TILE_FLOWER):
            p["speed"]       = SPEED_BOOST
            p["speed_until"] = now + duration
        elif t == TILE_STAR:
            p["shield"]       = 1
            p["shield_until"] = now + duration
        elif t == TILE_COMPASS:
            p["compass"]       = 1
            p["compass_until"] = now + duration
        return p

    if target_role == role:
        player = _apply_to(player, tile)
    else:
        room = dict(room)
        room[target_role] = _apply_to(dict(room.get(target_role, {})), tile)

    return player, room


def tick_powerups(player: dict, now: float) -> dict:
    speed_until   = player.get("speed_until",   0) or 0
    shield_until  = player.get("shield_until",  0) or 0
    compass_until = player.get("compass_until", 0) or 0

    if speed_until > 0 and now > speed_until:
        player["speed"]       = 1
        player["speed_until"] = 0

    if shield_until > 0 and now > shield_until:
        player["shield"]       = 0
        player["shield_until"] = 0

    if compass_until > 0 and now > compass_until:
        player["compass"]       = 0
        player["compass_until"] = 0

    return player


# ─── Direction arrow for compass ─────────────────────────────────────────────
def get_compass_arrow(from_pos, to_pos) -> str:
    if not from_pos or not to_pos:
        return "❓"
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    if abs(dx) >= abs(dy):
        return "➡️" if dx > 0 else "⬅️"
    return "⬇️" if dy > 0 else "⬆️"


# ─── Format time ─────────────────────────────────────────────────────────────
def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"
