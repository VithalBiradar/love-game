"""
app.py  –  REDESIGNED EDITION
==============================
Architecture (unchanged from original):
  - One-click-one-block movement inside JS iframe.
  - Python never calls st.rerun() during gameplay.
  - Firebase sync unchanged.
  - Game-end signal via hidden text-input.

UI changes:
  - Screen 1 (lobby):  full-page centered card, no scroll.
  - Screen 2 (game):   compact dashboard, no scroll.
  - Screen 3 (winner): centered winner card.
  - Branding: BIRADR'S GAMES header on lobby.
"""

import streamlit as st
import time
import random
import string

st.set_page_config(
    page_title="❤️ Snake Love Chase",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from firebase_client import FirebaseClient
from game_logic import (
    MAP_SIZE, GAME_DURATION,
    generate_map, get_valid_spawn,
)
from ui_components import (
    inject_global_css,
    render_lobby,
    render_waiting_room,
    render_game_board,
    render_winner_screen,
    render_leaderboard,
)

# ── Firebase singleton ─────────────────────────────────────────────────────────
def get_firebase():
    if "_firebase_client" not in st.session_state:
        st.session_state["_firebase_client"] = FirebaseClient()
    return st.session_state["_firebase_client"]

fb = get_firebase()

# ── Session-state defaults ─────────────────────────────────────────────────────
DEFAULTS = {
    "screen":       "lobby",
    "player_name":  "",
    "player_role":  None,
    "room_code":    None,
    "is_host":      False,
    "winner_data":  None,
    "_game_ended":  "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

inject_global_css()

def make_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ── Router ─────────────────────────────────────────────────────────────────────
def main():
    screen = st.session_state["screen"]
    if   screen == "lobby":   show_lobby()
    elif screen == "waiting": show_waiting()
    elif screen == "game":    show_game()
    elif screen == "winner":  show_winner()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 – LOBBY
# Full-page centered card.  Everything visible without scrolling.
# ══════════════════════════════════════════════════════════════════════════════
def show_lobby():
    render_lobby()

    # Three-column layout: narrow gutters, wide centre
    _, col, _ = st.columns([1, 2.2, 1])

    with col:
        st.markdown('<div class="slc-card">', unsafe_allow_html=True)

        # ── Name input ──────────────────────────────────────────────────────
        st.markdown('<div class="slc-label">Your Name</div>', unsafe_allow_html=True)
        name = st.text_input(
            "Your name", placeholder="e.g. Alex",
            key="name_input", max_chars=20,
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        # ── Role selection ──────────────────────────────────────────────────
        st.markdown('<div class="slc-label">Choose Role</div>', unsafe_allow_html=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(
                '<div class="role-card male">'
                '<span class="rc-icon">💙</span>'
                '<span>Male Snake</span><br>'
                '<span class="rc-hint">Catch her!</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Play as 💙 Male", use_container_width=True, key="btn_male"):
                st.session_state["player_role"] = "male"
        with rc2:
            st.markdown(
                '<div class="role-card female">'
                '<span class="rc-icon">💗</span>'
                '<span>Female Snake</span><br>'
                '<span class="rc-hint">Run away!</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Play as 💗 Female", use_container_width=True, key="btn_female"):
                st.session_state["player_role"] = "female"

        selected_role = st.session_state.get("player_role")
        if selected_role:
            label = "💙 Male Snake" if selected_role == "male" else "💗 Female Snake"
            st.markdown(
                f'<div style="text-align:center;font-size:.78rem;color:#9d6fff;'
                f'padding:.3rem 0 .1rem;font-weight:600">Selected: {label}</div>',
                unsafe_allow_html=True,
            )

        # ── Divider ─────────────────────────────────────────────────────────
        st.markdown(
            '<div style="border-top:1px solid rgba(160,100,255,.12);margin:.55rem 0"></div>',
            unsafe_allow_html=True,
        )

        # ── Create / Join ────────────────────────────────────────────────────
        st.markdown('<div class="slc-label">Create or Join Room</div>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            if st.button("＋ Create Room", use_container_width=True, key="btn_create"):
                _create_room(name)
        with cb:
            if st.button("🚪 Join Room", use_container_width=True, key="btn_join"):
                join_code = st.session_state.get("join_code_input", "").strip().upper()
                _join_room(name, join_code)

        join_code = st.text_input(
            "Room Code", placeholder="Enter 6-char code",
            key="join_code_input", max_chars=6,
            label_visibility="collapsed",
        )

        # ── Room address (shown after code generated, but we show placeholder) ─
        room_code = st.session_state.get("room_code")
        if room_code:
            st.markdown(
                f'<div style="margin:.45rem 0 .1rem"><span class="slc-label">Room Address</span></div>'
                f'<div class="room-code-box">{room_code}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # ── How to Play ──────────────────────────────────────────────────────
        st.markdown(
            '<div style="margin-top:.5rem"><div class="slc-label">How to Play</div>'
            '<div class="htp-grid">'
            '<div><span>💙 Male</span> catches female</div>'
            '<div><span>💗 Female</span> avoids male</div>'
            '<div><span>❤️🌸</span> speed boost</div>'
            '<div><span>⭐</span> shield · <span>🔍</span> compass</div>'
            '<div><span>WASD</span> for Male</div>'
            '<div><span>Arrows</span> for Female</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # ── Leaderboard ──────────────────────────────────────────────────────
        render_leaderboard(fb)

        st.markdown(
            '<div style="text-align:center;color:#4a3060;font-size:.68rem;margin-top:.6rem">'
            '💗 Made with love by Biradr\'s Games</div>',
            unsafe_allow_html=True,
        )


def _create_room(name: str):
    if not name.strip():
        st.error("Please enter your name first!"); return
    role = st.session_state.get("player_role")
    if not role:
        st.error("Please choose your role first!"); return

    code      = make_room_code()
    game_map  = generate_map()
    male_pos, female_pos = get_valid_spawn(game_map)

    def defaults(r):
        return {
            "name":          name.strip() if r == role else "Waiting…",
            "pos":           male_pos if r == "male" else female_pos,
            "dir":           "RIGHT"  if r == "male" else "LEFT",
            "speed": 1, "shield": 0, "compass": 0,
            "speed_until": 0, "shield_until": 0, "compass_until": 0,
            "connected":     r == role,
        }

    room_data = {
        "state":          "waiting",
        "created_at":     time.time(),
        "map":            game_map,
        "male":           defaults("male"),
        "female":         defaults("female"),
        "start_time":     0,
        "time_remaining": GAME_DURATION,
        "winner":         None,
    }
    result = fb.set(f"rooms/{code}", room_data)
    if result is None:
        st.error("⚠️ Could not create room. Check Firebase config."); return

    st.session_state.update({
        "screen":      "waiting",
        "player_name": name.strip(),
        "player_role": role,
        "room_code":   code,
        "is_host":     True,
    })
    st.rerun()


def _join_room(name: str, code: str):
    if not name.strip():
        st.error("Please enter your name first!"); return
    if not code:
        st.error("Please enter a room code!"); return

    room = fb.get(f"rooms/{code}")
    if not room:
        st.error(f"Room '{code}' not found."); return
    if room.get("state") not in ("waiting",):
        st.error("Room is already in progress or finished."); return

    male_connected   = room.get("male",   {}).get("connected", False)
    female_connected = room.get("female", {}).get("connected", False)
    if male_connected and female_connected:
        st.error("Room is full!"); return

    role = "female" if male_connected else "male"
    fb.update(f"rooms/{code}/{role}", {"name": name.strip(), "connected": True})

    updated = fb.get(f"rooms/{code}")
    if not updated:
        st.error("Room disappeared during join."); return

    other = "female" if role == "male" else "male"
    if updated.get(other, {}).get("connected", False):
        fb.update(f"rooms/{code}", {
            "state":          "playing",
            "start_time":     time.time(),
            "time_remaining": GAME_DURATION,
        })

    st.session_state.update({
        "screen":      "waiting",
        "player_name": name.strip(),
        "player_role": role,
        "room_code":   code,
        "is_host":     False,
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
        st.rerun(); return

    render_waiting_room(code, room, st.session_state["player_role"])

    if room.get("state") == "playing":
        st.session_state["screen"] = "game"
        st.rerun(); return

    time.sleep(1)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 – GAME  (no st.rerun() during play)
# ══════════════════════════════════════════════════════════════════════════════
def show_game():
    code = st.session_state["room_code"]
    role = st.session_state["player_role"]

    # Check if JS already signalled game-end
    ended_signal = st.session_state.get("_game_ended", "")
    if ended_signal:
        parts = ended_signal.split("||")
        st.session_state["winner_data"] = {
            "winner_role": parts[0] if len(parts) > 0 else "male",
            "reason":      parts[1] if len(parts) > 1 else "Game Over",
            "male_name":   parts[2] if len(parts) > 2 else "?",
            "female_name": parts[3] if len(parts) > 3 else "?",
        }
        st.session_state["_game_ended"] = ""
        st.session_state["screen"] = "winner"
        st.rerun(); return

    room = fb.get(f"rooms/{code}")
    if not room:
        st.error("Room disconnected.")
        st.session_state["screen"] = "lobby"
        st.rerun(); return

    if room.get("state") == "ended":
        st.session_state["winner_data"] = room.get("winner")
        st.session_state["screen"] = "winner"
        st.rerun(); return

    room["__code__"] = code
    db_url = fb.db_url

    render_game_board(room, role, db_url)

    # Hidden input: JS writes game-end signal here
    st.markdown("""
<style>
[data-testid="stTextInput"]:has(input[aria-label="game_ended_signal"]),
div:has(> [aria-label="game_ended_signal"]) { display:none !important; }
</style>
""", unsafe_allow_html=True)
    st.text_input(
        "game_ended_signal",
        key="_game_ended",
        label_visibility="hidden",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 – WINNER
# ══════════════════════════════════════════════════════════════════════════════
def show_winner():
    winner_data = st.session_state.get("winner_data") or {}
    render_winner_screen(winner_data)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if st.button("🔄 Play Again", use_container_width=True, key="play_again"):
            _cleanup_and_reset()
        if st.button("🏠 Main Menu", use_container_width=True, key="main_menu"):
            _cleanup_and_reset()


def _cleanup_and_reset():
    code    = st.session_state.get("room_code")
    is_host = st.session_state.get("is_host", False)
    if code and is_host:
        fb.delete(f"rooms/{code}")
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()


if __name__ == "__main__":
    main()
else:
    main()
