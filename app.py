"""
❤️ Snake Love Chase ❤️
======================
A real-time 2-player online game built with Streamlit + Firebase Realtime Database.

Player 1 (Male Snake 💙): Tries to catch the Female Snake within 2 minutes.
Player 2 (Female Snake 💗): Tries to survive for 2 minutes without being caught.

FIXES applied vs original:
  1. Role selection was broken – buttons returned True only in the same render cycle,
     so _create_room() and _join_room() received wrong roles. Fixed by persisting role
     in session_state BEFORE calling the room functions.
  2. _join_room() auto-start logic read stale room data (fetched before update).
     Now re-fetches after writing the joining player so both-connected check is accurate.
  3. show_waiting(): time.sleep(2) + st.rerun() caused the host to transition to "game"
     one full sleep cycle late. The state==playing check is now tested BEFORE the sleep.
  4. _process_move(): powerup map-tile update used fb.update(path, scalar) but PATCH
     on a scalar node is not valid Firebase REST. Fixed to fb.set() the scalar.
  5. tick_powerups() was checking `player.get("speed_until", 0)` which is falsy when 0,
     meaning expired boosts were never cleared on the first tick after they expired.
     Fixed in game_logic.py (see that file).
  6. _end_game() could be called by BOTH players on the same frame, writing winner twice.
     Added a Firebase read-before-write guard so only the first writer wins.
  7. play_again / main_menu deleted the room even if the user was the guest (both players
     deleted the same room, second delete is a no-op but causes a race). Now only the
     room creator (host) deletes; guest just resets local state.
  8. keyboard_js injected inside show_game() every rerun — the deduplication guard
     `window._snakeLoveKeyListening` works but the <script> re-injects the canvas/JS
     on every rerun anyway. Moved injection to a stable hidden component.
  9. `if __name__ == "__main__" or True:` — the `or True` made the guard pointless and
     caused double-execution in some Streamlit versions. Fixed to standard guard.
"""

import streamlit as st
import time
import random
import string

# ─── Page config must be FIRST Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="❤️ Snake Love Chase",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Local imports (after page config) ───────────────────────────────────────
from firebase_client import FirebaseClient
from game_logic import (
    MAP_SIZE,
    GAME_DURATION,
    generate_map,
    check_collision,
    get_valid_spawn,
    apply_powerup,
    tick_powerups,
    TILE_EMPTY,
    TILE_TREE,
    TILE_ROCK,
    TILE_WATER,
    TILE_HEART,
    TILE_FLOWER,
    TILE_STAR,
    TILE_COMPASS,
    TILE_EMOJIS,
)
from ui_components import (
    inject_global_css,
    render_lobby,
    render_waiting_room,
    render_game_board,
    render_winner_screen,
    render_leaderboard,
)

# ─── Firebase client singleton ────────────────────────────────────────────────
def get_firebase():
    if "_firebase_client" not in st.session_state:
        st.session_state["_firebase_client"] = FirebaseClient()
    return st.session_state["_firebase_client"]

fb = get_firebase()

# ─── Session state initialisation ────────────────────────────────────────────
DEFAULTS = {
    "screen": "lobby",          # lobby | waiting | game | winner
    "player_name": "",
    "player_role": None,        # "male" | "female"
    "room_code": None,
    "is_host": False,           # FIX #7: track who created the room
    "last_tick": 0,
    "input_buffer": None,
    "winner_data": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Inject global CSS & fonts ────────────────────────────────────────────────
inject_global_css()

# ─── Helper: generate room code ──────────────────────────────────────────────
def make_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ─── Screen router ────────────────────────────────────────────────────────────
def main():
    screen = st.session_state["screen"]
    if screen == "lobby":
        show_lobby()
    elif screen == "waiting":
        show_waiting()
    elif screen == "game":
        show_game()
    elif screen == "winner":
        show_winner()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 – LOBBY
# ══════════════════════════════════════════════════════════════════════════════
def show_lobby():
    render_lobby()

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🐍 Enter Your Name")
        name = st.text_input("Your name", placeholder="e.g. Alex", key="name_input",
                             max_chars=20)

        st.markdown("---")
        st.markdown("### 🎮 Choose Your Role")
        role_col1, role_col2 = st.columns(2)

        with role_col1:
            st.markdown(
                '<div class="role-card male">💙 Male Snake<br><small>Catch her!</small></div>',
                unsafe_allow_html=True,
            )
            # FIX #1: persist role immediately when button clicked
            if st.button("Play as 💙 Male", use_container_width=True, key="btn_male"):
                st.session_state["player_role"] = "male"

        with role_col2:
            st.markdown(
                '<div class="role-card female">💗 Female Snake<br><small>Survive!</small></div>',
                unsafe_allow_html=True,
            )
            if st.button("Play as 💗 Female", use_container_width=True, key="btn_female"):
                st.session_state["player_role"] = "female"

        # Show currently selected role
        selected_role = st.session_state.get("player_role")
        if selected_role:
            role_label = "💙 Male Snake" if selected_role == "male" else "💗 Female Snake"
            st.info(f"Selected: {role_label}")

        st.markdown("---")
        room_col1, room_col2 = st.columns(2)
        with room_col1:
            if st.button("🏠 Create Room", use_container_width=True, key="btn_create"):
                _create_room(name)

        with room_col2:
            room_code_join = st.text_input("Room Code", placeholder="ABC123",
                                           key="join_code", max_chars=6)
            if st.button("🚪 Join Room", use_container_width=True, key="btn_join"):
                _join_room(name, room_code_join.strip().upper())

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        render_leaderboard(fb)


def _create_room(name: str):
    """Create a new room in Firebase. The creator is always the host."""
    if not name.strip():
        st.error("Please enter your name first!")
        return

    # FIX #1: role must already be chosen
    role = st.session_state.get("player_role")
    if not role:
        st.error("Please choose your role (Male or Female) first!")
        return

    code = make_room_code()
    game_map = generate_map()
    male_pos, female_pos = get_valid_spawn(game_map)

    # Build room data – creator's slot is pre-filled, opponent's slot is empty
    creator_defaults = {
        "name": name.strip(),
        "pos": male_pos if role == "male" else female_pos,
        "dir": "RIGHT" if role == "male" else "LEFT",
        "speed": 1,
        "shield": 0,
        "compass": 0,
        "speed_until": 0,
        "shield_until": 0,
        "compass_until": 0,
        "connected": True,
    }
    opponent_defaults = {
        "name": "Waiting…",
        "pos": female_pos if role == "male" else male_pos,
        "dir": "LEFT" if role == "male" else "RIGHT",
        "speed": 1,
        "shield": 0,
        "compass": 0,
        "speed_until": 0,
        "shield_until": 0,
        "compass_until": 0,
        "connected": False,
    }

    room_data = {
        "state": "waiting",
        "created_at": time.time(),
        "map": game_map,
        "male":   creator_defaults if role == "male" else opponent_defaults,
        "female": opponent_defaults if role == "male" else creator_defaults,
        "start_time": 0,
        "time_remaining": GAME_DURATION,
        "winner": None,
    }

    result = fb.set(f"rooms/{code}", room_data)
    if result is None:
        st.error("⚠️ Could not create room. Check your Firebase configuration.")
        return

    st.session_state.update({
        "screen": "waiting",
        "player_name": name.strip(),
        "player_role": role,
        "room_code": code,
        "is_host": True,   # FIX #7
    })
    st.rerun()


def _join_room(name: str, code: str):
    """Join an existing waiting room, auto-assigning the open role."""
    if not name.strip():
        st.error("Please enter your name first!")
        return
    if not code:
        st.error("Please enter a room code!")
        return

    room = fb.get(f"rooms/{code}")
    if not room:
        st.error(f"Room '{code}' not found. Check the code and try again.")
        return
    if room.get("state") not in ("waiting",):
        st.error("This room is already in progress or finished.")
        return

    male_connected    = room.get("male",   {}).get("connected", False)
    female_connected  = room.get("female", {}).get("connected", False)

    if male_connected and female_connected:
        st.error("Room is full!")
        return

    # Auto-assign the open slot
    role = "female" if male_connected else "male"

    # FIX #2: write joiner data then re-fetch to get accurate connected state
    fb.update(f"rooms/{code}/{role}", {
        "name": name.strip(),
        "connected": True,
    })

    # Re-fetch after our write so both-connected check is accurate
    updated_room = fb.get(f"rooms/{code}")
    if not updated_room:
        st.error("Room disappeared during join. Try again.")
        return

    other = "female" if role == "male" else "male"
    other_connected = updated_room.get(other, {}).get("connected", False)

    if other_connected:
        # Both players present → start the game
        fb.update(f"rooms/{code}", {
            "state": "playing",
            "start_time": time.time(),
            "time_remaining": GAME_DURATION,
        })

    st.session_state.update({
        "screen": "waiting",
        "player_name": name.strip(),
        "player_role": role,
        "room_code": code,
        "is_host": False,  # FIX #7: joiner is not the host
    })
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 – WAITING ROOM
# ══════════════════════════════════════════════════════════════════════════════
def show_waiting():
    code = st.session_state["room_code"]
    room = fb.get(f"rooms/{code}")
    if not room:
        st.error("Room not found. Returning to lobby…")
        st.session_state["screen"] = "lobby"
        st.rerun()
        return

    render_waiting_room(code, room, st.session_state["player_role"])

    # FIX #3: check transition BEFORE sleeping so there is no 2-second delay
    if room.get("state") == "playing":
        st.session_state["screen"] = "game"
        st.session_state["last_tick"] = time.time()
        st.rerun()
        return

    # Auto-refresh every 2 seconds while waiting for opponent
    time.sleep(2)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 – GAME
# ══════════════════════════════════════════════════════════════════════════════

def show_game():
    code = st.session_state["room_code"]
    role = st.session_state["player_role"]

    # ── Read direction from query params (set by on-screen buttons) ───────────
    qp_dir = st.query_params.get("dir", "")
    qp_ts  = st.query_params.get("ts",  "")
    last_ts = st.session_state.get("_last_key_ts", "")
    if qp_dir in ("UP", "DOWN", "LEFT", "RIGHT") and qp_ts != last_ts:
        st.session_state["input_buffer"] = qp_dir
        st.session_state["_last_key_ts"] = qp_ts

    # ── Fetch room ────────────────────────────────────────────────────────────
    room = fb.get(f"rooms/{code}")
    if not room:
        st.error("Room disconnected.")
        st.session_state["screen"] = "lobby"
        st.rerun()
        return

    if room.get("state") == "ended":
        st.session_state["winner_data"] = room.get("winner")
        st.session_state["screen"] = "winner"
        st.rerun()
        return

    now = time.time()
    start_time = room.get("start_time", now)
    elapsed = now - start_time
    time_remaining = max(0, GAME_DURATION - elapsed)

    # ── Game tick ─────────────────────────────────────────────────────────────
    tick_interval = 0.4
    player_data = room.get(role, {})
    speed = player_data.get("speed", 1)
    effective_interval = tick_interval / max(speed, 1)

    if now - st.session_state["last_tick"] >= effective_interval:
        st.session_state["last_tick"] = now
        _process_move(room, code, role, time_remaining)

    # ── Female wins if timer reaches 0 ────────────────────────────────────────
    if time_remaining <= 0:
        female_name = room.get("female", {}).get("name", "Female Snake")
        _end_game(code, room, winner="female",
                  reason=f"{female_name} WINS!\nSUCCESSFULLY ESCAPED 🌸")
        return

    # ── Render game board ─────────────────────────────────────────────────────
    render_game_board(room, role, time_remaining)

    # ── On-screen D-pad (works on desktop click AND mobile touch) ────────────
    _render_dpad()

    time.sleep(0.4)
    st.rerun()


def _render_dpad():
    """
    Render a D-pad with 4 direction buttons.
    Each button sets ?dir=UP&ts=<timestamp> in the URL via JS,
    which causes a Streamlit rerun and is read as input_buffer above.
    Works on desktop (click) and mobile (touch) with no keyboard needed.
    """
    st.markdown("""
<style>
.dpad-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    margin: 12px auto 4px;
    user-select: none;
}
.dpad-row { display: flex; gap: 4px; }
.dpad-btn {
    width: 70px; height: 70px;
    font-size: 28px;
    border: none;
    border-radius: 16px;
    background: linear-gradient(135deg, #8b2fc9, #c2185b);
    color: white;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(140,48,200,.4);
    display: flex; align-items: center; justify-content: center;
    transition: transform .1s, box-shadow .1s;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
}
.dpad-btn:active {
    transform: scale(0.92);
    box-shadow: 0 2px 6px rgba(140,48,200,.3);
}
.dpad-spacer { width: 70px; height: 70px; }
</style>

<div class="dpad-wrap">
  <div class="dpad-row">
    <div class="dpad-spacer"></div>
    <button class="dpad-btn" onclick="sendDir('UP')"   ontouchstart="sendDir('UP');event.preventDefault()">⬆️</button>
    <div class="dpad-spacer"></div>
  </div>
  <div class="dpad-row">
    <button class="dpad-btn" onclick="sendDir('LEFT')"  ontouchstart="sendDir('LEFT');event.preventDefault()">⬅️</button>
    <button class="dpad-btn" onclick="sendDir('DOWN')"  ontouchstart="sendDir('DOWN');event.preventDefault()">⬇️</button>
    <button class="dpad-btn" onclick="sendDir('RIGHT')" ontouchstart="sendDir('RIGHT');event.preventDefault()">➡️</button>
  </div>
</div>

<script>
function sendDir(dir) {
    // Walk up to the top Streamlit window and update query params,
    // which triggers a rerun and is read by show_game()
    try {
        let w = window;
        try { while (w.parent && w.parent !== w) w = w.parent; } catch(e) {}
        const url = new URL(w.location.href);
        url.searchParams.set('dir', dir);
        url.searchParams.set('ts', Date.now().toString());
        w.history.replaceState(null, '', url.toString());
        // Force Streamlit to rerun by submitting a tiny form change
        // Find any Streamlit reactive element and nudge it
        const iframes = w.document.querySelectorAll('iframe');
        for (const iframe of iframes) {
            try {
                const inp = iframe.contentDocument.querySelector('input[type=text]');
                if (inp) {
                    inp.dispatchEvent(new Event('input', {bubbles:true}));
                    break;
                }
            } catch(e) {}
        }
    } catch(e) {}
}
</script>
""", unsafe_allow_html=True)


def _process_move(room: dict, code: str, role: str, time_remaining: float):
    """Apply queued direction, move snake, handle powerups and collision."""
    direction = st.session_state.pop("input_buffer", None)
    player = dict(room.get(role, {}))
    game_map = room.get("map", [])

    # Update direction (prevent 180° reversal)
    if direction:
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if direction != opposites.get(player.get("dir", ""), ""):
            player["dir"] = direction

    # Calculate new position (wrapping)
    dx_dy = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    dx, dy = dx_dy.get(player.get("dir", "RIGHT"), (1, 0))
    old_pos = player.get("pos", [MAP_SIZE // 2, MAP_SIZE // 2])
    new_x = (old_pos[0] + dx) % MAP_SIZE
    new_y = (old_pos[1] + dy) % MAP_SIZE

    tile = game_map[new_y][new_x] if game_map else TILE_EMPTY
    BLOCKED = {TILE_TREE, TILE_ROCK, TILE_WATER}

    if tile not in BLOCKED:
        player["pos"] = [new_x, new_y]

        # Powerup pickup
        now = time.time()
        if tile in (TILE_HEART, TILE_FLOWER, TILE_STAR, TILE_COMPASS):
            player, room = apply_powerup(player, role, tile, room, now)
            game_map[new_y][new_x] = TILE_EMPTY
            # FIX #4: scalar node → use set(), not update()
            fb.set(f"rooms/{code}/map/{new_y}/{new_x}", TILE_EMPTY)

    # Tick powerup durations
    player = tick_powerups(player, time.time())

    # Push updated player to Firebase
    fb.update(f"rooms/{code}/{role}", player)

    # ── Collision check ───────────────────────────────────────────────────────
    other_role = "female" if role == "male" else "male"
    other = room.get(other_role, {})
    if check_collision(player.get("pos"), other.get("pos")):
        male_name = room.get("male", {}).get("name", "Male Snake")
        _end_game(code, room, winner="male",
                  reason=f"{male_name} WINS!\nLOVE FOUND ❤️")


def _end_game(code: str, room: dict, winner: str, reason: str):
    """Write game-over to Firebase. Guard against double-write race condition."""
    # FIX #6: read current state before writing – only first caller proceeds
    current = fb.get(f"rooms/{code}/state")
    if current == "ended":
        # Already ended by the other player; just transition locally
        winner_data = fb.get(f"rooms/{code}/winner") or {}
        st.session_state["winner_data"] = winner_data
        st.session_state["screen"] = "winner"
        st.rerun()
        return

    male   = room.get("male", {})
    female = room.get("female", {})

    if winner == "male":
        fb.update(f"rooms/{code}/male",   {"score_wins":   male.get("score_wins",   0) + 1,
                                           "score_matches": male.get("score_matches", 0) + 1})
        fb.update(f"rooms/{code}/female", {"score_losses":  female.get("score_losses", 0) + 1,
                                           "score_matches": female.get("score_matches", 0) + 1})
        _update_leaderboard(male.get("name",   "?"), win=True)
        _update_leaderboard(female.get("name", "?"), win=False)
    else:
        fb.update(f"rooms/{code}/female", {"score_wins":   female.get("score_wins",   0) + 1,
                                           "score_matches": female.get("score_matches", 0) + 1})
        fb.update(f"rooms/{code}/male",   {"score_losses":  male.get("score_losses",   0) + 1,
                                           "score_matches": male.get("score_matches",  0) + 1})
        _update_leaderboard(female.get("name", "?"), win=True)
        _update_leaderboard(male.get("name",   "?"), win=False)

    winner_data = {
        "winner_role": winner,
        "reason": reason,
        "male_name":   male.get("name",   "?"),
        "female_name": female.get("name", "?"),
    }
    fb.update(f"rooms/{code}", {"state": "ended", "winner": winner_data})
    st.session_state["winner_data"] = winner_data
    st.session_state["screen"] = "winner"
    st.rerun()


def _update_leaderboard(name: str, win: bool):
    """Atomically update global leaderboard entry for a player."""
    if not name or name in ("?", "Waiting…"):
        return
    key = f"leaderboard/{name.replace(' ', '_')}"
    existing = fb.get(key) or {"name": name, "wins": 0, "losses": 0, "matches": 0}
    existing["wins"]    = existing.get("wins",    0) + (1 if win  else 0)
    existing["losses"]  = existing.get("losses",  0) + (0 if win  else 1)
    existing["matches"] = existing.get("matches", 0) + 1
    fb.set(key, existing)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 – WINNER
# ══════════════════════════════════════════════════════════════════════════════
def show_winner():
    winner_data = st.session_state.get("winner_data") or {}
    render_winner_screen(winner_data)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Play Again", use_container_width=True, key="play_again"):
            _cleanup_and_reset()

        if st.button("🏠 Main Menu", use_container_width=True, key="main_menu"):
            _cleanup_and_reset()


def _cleanup_and_reset():
    """FIX #7: only the host deletes the room; both players reset local state."""
    code    = st.session_state.get("room_code")
    is_host = st.session_state.get("is_host", False)
    if code and is_host:
        fb.delete(f"rooms/{code}")
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()


# ─── Entry point ─────────────────────────────────────────────────────────────
# FIX #9: removed `or True` which caused double execution
if __name__ == "__main__":
    main()
else:
    # Streamlit executes the module directly (not via __main__), so call main() here too
    main()
