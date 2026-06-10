"""
ui_components.py
================
All Streamlit / HTML rendering for Snake Love Chase.

FIXES applied vs original:
  FIX U1: render_game_board() imported `time as _time` inside the function body
           on every call.  Moved to module-level import.
  FIX U2: render_leaderboard() called data.values() without first checking that
           `data` is a dict (Firebase sometimes returns a list when keys are
           integer-like).  Added isinstance guard.
  FIX U3: _get_powerup_badges() imported math inside the function; moved to top.
"""

import time as _time
import math
import streamlit as st
from game_logic import (
    MAP_SIZE, TILE_EMOJIS, TILE_COLORS, fmt_time, get_compass_arrow,
    TILE_EMPTY, TILE_TREE, TILE_ROCK, TILE_BUSH, TILE_WATER,
    TILE_HEART, TILE_FLOWER, TILE_STAR, TILE_COMPASS,
)


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_global_css():
    """Inject the full game stylesheet once per session."""
    st.markdown("""
<style>
/* ── Google Fonts ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@400;600;700;900&display=swap');

/* ── Reset & base ─────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #0d0d1a !important;
    font-family: 'Nunito', sans-serif;
    color: #f0e6ff;
}

/* Hide Streamlit chrome */
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Animated background ──────────────────────────────────── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background:
        radial-gradient(ellipse at 20% 30%, rgba(180,60,220,.18) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 70%, rgba(220,60,120,.15) 0%, transparent 60%),
        radial-gradient(ellipse at 50% 50%, rgba(60,60,180,.12) 0%, transparent 80%);
    animation: bgPulse 8s ease-in-out infinite alternate;
    pointer-events: none;
}
@keyframes bgPulse {
    from { opacity: .7; }
    to   { opacity: 1; }
}

/* ── Main content wrapper ─────────────────────────────────── */
[data-testid="stMain"] { position: relative; z-index: 1; }

/* ── Title ────────────────────────────────────────────────── */
.game-title {
    font-family: 'Fredoka One', cursive;
    font-size: clamp(2rem, 6vw, 4rem);
    text-align: center;
    background: linear-gradient(135deg, #ff69b4, #ff1493, #da70d6, #9370db, #6495ed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 20px rgba(255,100,180,.4));
    animation: titlePulse 3s ease-in-out infinite;
    margin: 1rem 0 0.25rem;
}
@keyframes titlePulse {
    0%,100% { filter: drop-shadow(0 0 15px rgba(255,100,180,.4)); }
    50%      { filter: drop-shadow(0 0 35px rgba(255,100,180,.8)); }
}

.game-subtitle {
    text-align: center;
    color: #c8a0e8;
    font-size: 1.05rem;
    margin-bottom: 1.5rem;
    letter-spacing: .08em;
}

/* ── Card ─────────────────────────────────────────────────── */
.card {
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 20px;
    padding: 1.6rem 2rem;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.1);
    margin-bottom: 1rem;
}

/* ── Role cards ───────────────────────────────────────────── */
.role-card {
    border-radius: 14px;
    padding: .9rem;
    text-align: center;
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: .6rem;
    line-height: 1.6;
    transition: transform .2s;
}
.role-card:hover { transform: translateY(-3px); }
.role-card.male {
    background: linear-gradient(135deg, #0d2b5e, #1a4a9e);
    border: 2px solid #4a90e2;
}
.role-card.female {
    background: linear-gradient(135deg, #5e0d2b, #9e1a4a);
    border: 2px solid #e24a90;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #8b2fc9, #c2185b) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: .6rem 1.2rem !important;
    transition: all .2s !important;
    box-shadow: 0 4px 15px rgba(140,48,200,.3) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(140,48,200,.5) !important;
    background: linear-gradient(135deg, #9b3fd9, #d2286b) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Text inputs ──────────────────────────────────────────── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,.07) !important;
    border: 1.5px solid rgba(255,255,255,.2) !important;
    border-radius: 10px !important;
    color: #f0e6ff !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 1rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #c060f0 !important;
    box-shadow: 0 0 0 2px rgba(192,96,240,.3) !important;
}

/* ── Game board wrapper ───────────────────────────────────── */
.game-board-wrapper {
    display: flex;
    justify-content: center;
    margin: 0 auto;
}
.game-board-table {
    border-collapse: collapse;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 0 40px rgba(200,80,200,.25);
}
.game-board-table td {
    width: 30px;
    height: 30px;
    text-align: center;
    font-size: 18px;
    line-height: 30px;
    border: 1px solid rgba(255,255,255,.04);
    transition: background .1s;
}

/* ── HUD ──────────────────────────────────────────────────── */
.hud {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 14px;
    padding: .7rem 1.2rem;
    margin-bottom: .8rem;
    backdrop-filter: blur(8px);
    flex-wrap: wrap;
    gap: .5rem;
}
.hud-player {
    display: flex;
    align-items: center;
    gap: .5rem;
    font-weight: 700;
    font-size: .95rem;
}
.hud-male   { color: #6eb6ff; }
.hud-female { color: #ff8abf; }
.hud-timer {
    font-family: 'Fredoka One', cursive;
    font-size: 1.4rem;
    color: #ffd700;
    text-shadow: 0 0 12px rgba(255,215,0,.5);
}
.hud-timer.urgent {
    color: #ff4444;
    animation: timerBlink .5s ease-in-out infinite alternate;
}
@keyframes timerBlink {
    from { text-shadow: 0 0 8px rgba(255,68,68,.4); }
    to   { text-shadow: 0 0 25px rgba(255,68,68,.9); }
}

/* ── Powerup badges ───────────────────────────────────────── */
.powerup-badge {
    display: inline-block;
    background: rgba(255,255,255,.1);
    border-radius: 8px;
    padding: 2px 8px;
    font-size: .85rem;
    margin: 0 2px;
    animation: badgePulse 1s ease-in-out infinite alternate;
}
@keyframes badgePulse {
    from { box-shadow: 0 0 4px rgba(255,215,0,.3); }
    to   { box-shadow: 0 0 12px rgba(255,215,0,.7); }
}

/* ── Winner screen ────────────────────────────────────────── */
.winner-screen {
    text-align: center;
    padding: 2rem;
    animation: winnerIn .6s cubic-bezier(.175,.885,.32,1.275);
}
@keyframes winnerIn {
    from { opacity: 0; transform: scale(.7) rotate(-5deg); }
    to   { opacity: 1; transform: scale(1)  rotate(0deg); }
}
.winner-emoji {
    font-size: 5rem;
    display: block;
    animation: bounceWinner 1s ease-in-out infinite alternate;
    margin: 1rem 0;
}
@keyframes bounceWinner {
    from { transform: translateY(0) scale(1); }
    to   { transform: translateY(-20px) scale(1.1); }
}
.winner-title {
    font-family: 'Fredoka One', cursive;
    font-size: clamp(2rem, 5vw, 3.5rem);
    background: linear-gradient(135deg, #ffd700, #ff69b4, #da70d6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: .5rem 0;
}
.winner-subtitle {
    font-size: 1.4rem;
    color: #c8a0e8;
    margin-bottom: 1.5rem;
}

/* ── Waiting room ─────────────────────────────────────────── */
.room-code-display {
    font-family: 'Fredoka One', cursive;
    font-size: 3rem;
    letter-spacing: .3em;
    color: #ffd700;
    text-align: center;
    text-shadow: 0 0 20px rgba(255,215,0,.5);
    background: rgba(255,215,0,.08);
    border: 2px solid rgba(255,215,0,.3);
    border-radius: 16px;
    padding: .8rem 1.5rem;
    margin: .8rem 0;
    display: inline-block;
    width: 100%;
}

.player-status {
    display: flex;
    align-items: center;
    gap: .8rem;
    padding: .7rem 1rem;
    border-radius: 12px;
    margin: .4rem 0;
    font-weight: 600;
}
.player-status.connected    { background: rgba(50,200,100,.12); border: 1px solid rgba(50,200,100,.3); }
.player-status.disconnected { background: rgba(200,100,50,.12); border: 1px solid rgba(200,100,50,.3); }

/* ── Leaderboard ──────────────────────────────────────────── */
.leaderboard-row {
    display: flex;
    align-items: center;
    padding: .5rem .8rem;
    border-radius: 10px;
    margin: .25rem 0;
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.07);
    font-size: .9rem;
    gap: .6rem;
}
.leaderboard-rank   { font-family: 'Fredoka One'; font-size: 1.1rem; color: #ffd700; min-width: 2rem; }
.leaderboard-name   { flex: 1; font-weight: 700; }
.leaderboard-wins   { color: #6eff9a; font-weight: 700; }
.leaderboard-losses { color: #ff6e6e; font-weight: 700; }

/* ── Controls legend ──────────────────────────────────────── */
.controls-legend {
    display: flex;
    gap: 1.5rem;
    justify-content: center;
    flex-wrap: wrap;
    font-size: .85rem;
    color: #a080c0;
    margin: .5rem 0;
}
.key-badge {
    background: rgba(255,255,255,.1);
    border: 1px solid rgba(255,255,255,.2);
    border-radius: 6px;
    padding: 1px 7px;
    font-family: monospace;
    font-size: .9rem;
}

/* ── Confetti canvas ──────────────────────────────────────── */
#confetti-canvas {
    position: fixed; inset: 0; z-index: 9999;
    pointer-events: none;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,.04); }
::-webkit-scrollbar-thumb { background: rgba(200,100,200,.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

    # Floating particle background
    st.markdown("""
<canvas id="particles-canvas" style="position:fixed;inset:0;z-index:0;pointer-events:none;"></canvas>
<script>
(function(){
    const canvas = document.getElementById('particles-canvas');
    if (!canvas || canvas._init) return;
    canvas._init = true;
    const ctx = canvas.getContext('2d');
    let W = canvas.width  = window.innerWidth;
    let H = canvas.height = window.innerHeight;
    window.addEventListener('resize', ()=>{ W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; });

    const EMOJIS = ['❤️','🌸','✨','💖','🌟','💕'];
    const particles = Array.from({length: 25}, () => ({
        x: Math.random() * W,
        y: Math.random() * H,
        emoji: EMOJIS[Math.floor(Math.random() * EMOJIS.length)],
        size: 12 + Math.random() * 16,
        vx: (Math.random() - .5) * .4,
        vy: -.2 - Math.random() * .4,
        alpha: .1 + Math.random() * .25,
        rot: Math.random() * Math.PI * 2,
        vrot: (Math.random() - .5) * .01,
    }));

    function draw() {
        ctx.clearRect(0, 0, W, H);
        particles.forEach(p => {
            p.x += p.vx; p.y += p.vy; p.rot += p.vrot;
            if (p.y < -30) { p.y = H + 10; p.x = Math.random() * W; }
            if (p.x < -30) p.x = W + 10;
            if (p.x > W + 30) p.x = -10;
            ctx.save();
            ctx.globalAlpha = p.alpha;
            ctx.translate(p.x, p.y);
            ctx.rotate(p.rot);
            ctx.font = p.size + 'px serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(p.emoji, 0, 0);
            ctx.restore();
        });
        requestAnimationFrame(draw);
    }
    draw();
})();
</script>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOBBY HEADER
# ══════════════════════════════════════════════════════════════════════════════
def render_lobby():
    st.markdown('<div class="game-title">❤️ Snake Love Chase ❤️</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="game-subtitle">A real-time 2-player love pursuit game</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# WAITING ROOM
# ══════════════════════════════════════════════════════════════════════════════
def render_waiting_room(code: str, room: dict, my_role: str):
    render_lobby()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🏠 Waiting Room")

        st.markdown(
            f'<div class="room-code-display">{code}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="text-align:center;color:#a080c0;margin-bottom:.8rem">'
            "Share this code with your friend</p>",
            unsafe_allow_html=True,
        )

        male_data   = room.get("male",   {})
        female_data = room.get("female", {})

        for role_label, data, emoji, color in [
            ("💙 Male Snake",   male_data,   "💙", "#6eb6ff"),
            ("💗 Female Snake", female_data, "💗", "#ff8abf"),
        ]:
            connected = data.get("connected", False)
            name      = data.get("name", "Waiting…")
            status    = "connected" if connected else "disconnected"
            dot       = "🟢" if connected else "🔴"
            st.markdown(
                f'<div class="player-status {status}">'
                f'<span>{dot}</span>'
                f'<span style="color:{color}">{role_label}</span>'
                f'<span style="margin-left:auto">{name if connected else "Waiting…"}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

        state = room.get("state", "waiting")
        if state == "playing":
            st.success("🚀 Both players ready! Starting game…")
        else:
            st.markdown(
                '<p style="text-align:center;margin-top:.8rem;color:#c8a0e8">'
                "⏳ Waiting for the second player to join…</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="controls-legend">
  <span>💙 Male:   <span class="key-badge">W</span><span class="key-badge">A</span><span class="key-badge">S</span><span class="key-badge">D</span></span>
  <span>💗 Female: <span class="key-badge">↑</span><span class="key-badge">←</span><span class="key-badge">↓</span><span class="key-badge">→</span></span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GAME BOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_game_board(room: dict, my_role: str, time_remaining: float):
    """Render HUD + board + controls legend."""
    # FIX U1: use module-level _time import instead of re-importing each call

    male_data   = room.get("male",   {})
    female_data = room.get("female", {})
    game_map    = room.get("map",    [])

    male_pos   = male_data.get("pos",   [0, 0])
    female_pos = female_data.get("pos", [MAP_SIZE - 1, MAP_SIZE - 1])

    male_name   = male_data.get("name",   "Male")
    female_name = female_data.get("name", "Female")

    urgency_class = "urgent" if time_remaining <= 20 else ""
    time_str = fmt_time(time_remaining)

    now = _time.time()
    male_badges   = _get_powerup_badges(male_data,   now)
    female_badges = _get_powerup_badges(female_data, now)

    compass_html = ""
    if male_data.get("compass"):
        arrow = get_compass_arrow(male_pos, female_pos)
        compass_html = f'<span class="powerup-badge">🔍{arrow}</span>'

    st.markdown(f"""
<div class="hud">
  <div class="hud-player hud-male">
    🐍💙 {male_name}
    {male_badges}
  </div>
  <div class="hud-timer {urgency_class}">⏱ {time_str}</div>
  <div class="hud-player hud-female">
    {female_badges}
    {female_name} 💗🐍
  </div>
</div>
{compass_html}
""", unsafe_allow_html=True)

    # ── Board HTML table ──────────────────────────────────────────────────────
    rows_html = []
    for y in range(MAP_SIZE):
        cols_html = []
        for x in range(MAP_SIZE):
            tile = game_map[y][x] if game_map else 0

            if [x, y] == male_pos:
                cell_emoji = "🛡️" if male_data.get("shield") else "🐍"
                bg   = "#0a2060"
                glow = "box-shadow:inset 0 0 8px #4a90e2;"
            elif [x, y] == female_pos:
                cell_emoji = "🛡️" if female_data.get("shield") else "🐍"
                bg   = "#60040a"
                glow = "box-shadow:inset 0 0 8px #e24a80;"
            else:
                cell_emoji = TILE_EMOJIS.get(tile, "⬛")
                bg   = TILE_COLORS.get(tile, "#1a1a2e")
                glow = ""

            cols_html.append(
                f'<td style="background:{bg};{glow}">{cell_emoji}</td>'
            )
        rows_html.append("<tr>" + "".join(cols_html) + "</tr>")

    board_html = (
        '<div class="game-board-wrapper">'
        '<table class="game-board-table">'
        + "".join(rows_html)
        + "</table></div>"
    )
    st.markdown(board_html, unsafe_allow_html=True)

    st.markdown("""
<div class="controls-legend" style="margin-top:.5rem">
  <span>💙 Male move:   <span class="key-badge">W</span><span class="key-badge">A</span><span class="key-badge">S</span><span class="key-badge">D</span></span>
  <span>💗 Female move: <span class="key-badge">↑</span><span class="key-badge">←</span><span class="key-badge">↓</span><span class="key-badge">→</span></span>
</div>
""", unsafe_allow_html=True)

    role_color = "#6eb6ff" if my_role == "male" else "#ff8abf"
    role_label = "Male (WASD)" if my_role == "male" else "Female (Arrow Keys)"
    role_emoji = "💙" if my_role == "male" else "💗"
    st.markdown(
        f'<p style="text-align:center;color:{role_color};font-weight:700;margin-top:.3rem">'
        f"You are: {role_emoji} {role_label}</p>",
        unsafe_allow_html=True,
    )


def _get_powerup_badges(player: dict, now: float) -> str:
    """Return HTML string of active powerup badges. FIX U3: math at module level."""
    badges = []
    if player.get("speed", 1) > 1:
        remaining = max(0, player.get("speed_until", 0) - now)
        badges.append(f'<span class="powerup-badge">⚡{math.ceil(remaining)}s</span>')
    if player.get("shield"):
        remaining = max(0, player.get("shield_until", 0) - now)
        badges.append(f'<span class="powerup-badge">🛡️{math.ceil(remaining)}s</span>')
    return " ".join(badges)


# ══════════════════════════════════════════════════════════════════════════════
# WINNER SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def render_winner_screen(winner_data: dict):
    """Display animated winner screen with confetti."""
    winner_role = winner_data.get("winner_role", "male")
    reason      = winner_data.get("reason", "Game Over!")
    lines       = reason.split("\n")
    title_line  = lines[0] if lines else "Winner!"
    sub_line    = lines[1] if len(lines) > 1 else ""

    if winner_role == "male":
        emoji   = "💙"
        color_a, color_b = "#4a90e2", "#6eb6ff"
        bg_glow = "rgba(74,144,226,.15)"
    else:
        emoji   = "💗"
        color_a, color_b = "#e24a80", "#ff8abf"
        bg_glow = "rgba(226,74,128,.15)"

    st.markdown(f"""
<div style="
    background: radial-gradient(ellipse at center, {bg_glow} 0%, transparent 70%);
    border-radius: 24px; padding: 2rem; text-align: center;
">
<div class="winner-screen">
  <span class="winner-emoji">{emoji}</span>
  <span class="winner-emoji">😊</span>
  <div class="winner-title" style="
    background: linear-gradient(135deg, {color_a}, {color_b}, #ffd700);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  ">{title_line}</div>
  <div class="winner-subtitle">{sub_line}</div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<canvas id="confetti-canvas"></canvas>
<script>
(function(){
    const canvas = document.getElementById('confetti-canvas');
    if (!canvas || canvas._confettiRunning) return;
    canvas._confettiRunning = true;
    const ctx = canvas.getContext('2d');
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;

    const COLORS = ['#ff69b4','#ffd700','#da70d6','#6eb6ff','#ff1493','#00fa9a'];
    const SHAPES = ['❤️','🌸','⭐','✨','💖','🌟'];

    const pieces = Array.from({length: 80}, () => ({
        x:     Math.random() * canvas.width,
        y:     -20 - Math.random() * 200,
        size:  10 + Math.random() * 20,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        shape: SHAPES[Math.floor(Math.random() * SHAPES.length)],
        vy:    2 + Math.random() * 4,
        vx:    (Math.random() - .5) * 3,
        rot:   Math.random() * Math.PI * 2,
        vrot:  (Math.random() - .5) * .15,
        alpha: .8 + Math.random() * .2,
    }));

    let frame = 0;
    function animate() {
        if (frame++ > 300) { ctx.clearRect(0,0,canvas.width,canvas.height); return; }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        pieces.forEach(p => {
            p.x   += p.vx;
            p.y   += p.vy;
            p.rot += p.vrot;
            if (p.y > canvas.height + 30) p.y = -30;
            ctx.save();
            ctx.globalAlpha = p.alpha;
            ctx.translate(p.x, p.y);
            ctx.rotate(p.rot);
            ctx.font = p.size + 'px serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(p.shape, 0, 0);
            ctx.restore();
        });
        requestAnimationFrame(animate);
    }
    animate();

    for (let i = 0; i < 15; i++) {
        const div = document.createElement('div');
        div.textContent = ['❤️','💖','💕','💗'][Math.floor(Math.random()*4)];
        div.style.cssText = `
            position:fixed; font-size:${20+Math.random()*30}px;
            left:${Math.random()*100}vw; bottom:-50px;
            animation: floatUp ${3+Math.random()*3}s ease-in forwards;
            z-index:10000; pointer-events:none;
            animation-delay:${Math.random()*2}s;
        `;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 6000);
    }
})();
</script>
<style>
@keyframes floatUp {
    to { transform: translateY(-110vh) rotate(360deg); opacity: 0; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_leaderboard(fb):
    """Fetch and display top 10 players from Firebase leaderboard."""
    try:
        data = fb.get("leaderboard") or {}
        if not data:
            return

        # FIX U2: Firebase can return a list if keys are 0-indexed integers
        if isinstance(data, list):
            values = [v for v in data if v]
        elif isinstance(data, dict):
            values = list(data.values())
        else:
            return

        players = sorted(
            values,
            key=lambda p: (-p.get("wins", 0), -p.get("matches", 0)),
        )[:10]

        if not players:
            return

        st.markdown("### 🏆 Leaderboard")
        rank_emojis = ["🥇", "🥈", "🥉"]
        rows_html = []
        for i, p in enumerate(players):
            rank = rank_emojis[i] if i < 3 else f"#{i+1}"
            rows_html.append(f"""
<div class="leaderboard-row">
  <span class="leaderboard-rank">{rank}</span>
  <span class="leaderboard-name">{p.get('name','?')}</span>
  <span class="leaderboard-wins">🏆 {p.get('wins',0)}W</span>
  <span class="leaderboard-losses">💔 {p.get('losses',0)}L</span>
  <span style="color:#a080c0">🎮 {p.get('matches',0)}</span>
</div>
""")
        st.markdown("".join(rows_html), unsafe_allow_html=True)
    except Exception:
        pass  # leaderboard is non-critical
