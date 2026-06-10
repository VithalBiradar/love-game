"""
game_logic.py
=============
Pure game-logic helpers (no Streamlit, no Firebase).

FIXES applied vs original:
  FIX #5: tick_powerups() checked `player.get("speed_until", 0)` – falsy when 0,
           so the condition `if player.get("speed_until", 0) and now > ...` was
           always False after expiry (speed_until was already 0 but the AND
           short-circuits). Changed to explicit `is not None` and `> 0` guard.
"""

import random
import time

# ─── Constants ────────────────────────────────────────────────────────────────
MAP_SIZE        = 20    # 20×20 grid
GAME_DURATION   = 120   # seconds (2 minutes)
POWERUP_DURATION = 5    # seconds for speed / shield boosts
SPEED_BOOST     = 2     # multiplier when speed powerup active

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
    TILE_EMPTY:   "#1a1a2e",
    TILE_TREE:    "#1a3a1a",
    TILE_ROCK:    "#2a2a2a",
    TILE_BUSH:    "#1a2a1a",
    TILE_WATER:   "#0a1a3a",
    TILE_HEART:   "#3a1a1a",
    TILE_FLOWER:  "#3a1a2a",
    TILE_STAR:    "#2a2a1a",
    TILE_COMPASS: "#1a2a2a",
}


# ─── Map generation ───────────────────────────────────────────────────────────
def generate_map() -> list:
    """
    Generate a 20×20 map with randomised terrain.
    Returns a 2D list (row-major: map[y][x]).
    Firebase requires plain lists, not nested generics.
    """
    grid = [[TILE_EMPTY] * MAP_SIZE for _ in range(MAP_SIZE)]

    # Border trees
    for i in range(MAP_SIZE):
        grid[0][i]           = TILE_TREE
        grid[MAP_SIZE - 1][i] = TILE_TREE
        grid[i][0]           = TILE_TREE
        grid[i][MAP_SIZE - 1] = TILE_TREE

    _place_clusters(grid, TILE_TREE,  count=8,  size=3)
    _place_clusters(grid, TILE_ROCK,  count=10, size=2)
    _place_clusters(grid, TILE_BUSH,  count=12, size=2)
    _place_clusters(grid, TILE_WATER, count=4,  size=4)

    _place_scattered(grid, TILE_HEART,   count=3)
    _place_scattered(grid, TILE_FLOWER,  count=3)
    _place_scattered(grid, TILE_STAR,    count=2)
    _place_scattered(grid, TILE_COMPASS, count=2)

    return grid


def _place_clusters(grid, tile, count, size):
    rows = len(grid)
    cols = len(grid[0])
    for _ in range(count):
        cx = random.randint(2, cols - 3)
        cy = random.randint(2, rows - 3)
        for _ in range(size * 3):
            nx = cx + random.randint(-size, size)
            ny = cy + random.randint(-size, size)
            if 1 <= nx < cols - 1 and 1 <= ny < rows - 1:
                if grid[ny][nx] == TILE_EMPTY:
                    grid[ny][nx] = tile


def _place_scattered(grid, tile, count):
    rows = len(grid)
    cols = len(grid[0])
    placed = 0
    attempts = 0
    while placed < count and attempts < 500:
        attempts += 1
        x = random.randint(1, cols - 2)
        y = random.randint(1, rows - 2)
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
    """
    FIX #5: original used `if player.get("speed_until", 0) and now > ...`
    which is falsy when speed_until == 0, so boosts were never cleared on
    the very first tick after they expired (speed_until had already been set
    to 0 by the previous tick that found the expiry).  Use explicit > 0 guard.
    """
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
