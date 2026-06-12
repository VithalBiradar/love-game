"""
ui_components.py  –  REDESIGNED EDITION
=========================================
Complete UI redesign:
  • Screen 1 (Lobby): Full-page centered card with branding, role selection,
    room create/join — everything on one screen, no scroll.
  • Screen 2 (Game Dashboard): Top bar + board + right panel, no scroll.
  • Board: ~35% smaller (CELL=12px → 20×12=240px board).
  • All Firebase/multiplayer/movement logic unchanged.
  • Modern neon dark theme: deep purple/indigo base, pink/blue/gold accents.
"""

import time as _time
import json
import streamlit as st
import streamlit.components.v1 as components
from game_logic import (
    MAP_SIZE, TILE_EMOJIS, TILE_COLORS, fmt_time, get_compass_arrow,
    TILE_EMPTY, TILE_TREE, TILE_ROCK, TILE_BUSH, TILE_WATER,
    TILE_HEART, TILE_FLOWER, TILE_STAR, TILE_COMPASS,
    GAME_DURATION, SPEED_BOOST, POWERUP_DURATION,
)


# ================================================================================
# GLOBAL CSS
# ================================================================================
def inject_global_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
    height: 100% !important;
    width:  100% !important;
}
html, body, [data-testid="stAppViewContainer"] {
    background: #07071a !important;
    font-family: 'Inter', system-ui, sans-serif;
    color: #e8deff;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
/* Allow scrolling on mobile for lobby */
@media (max-width: 600px) {
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="block-container"] {
        overflow-y: auto !important;
        height: auto !important;
        max-height: none !important;
    }
}
/* Desktop: keep no-overflow for game screen */
@media (min-width: 601px) {
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="block-container"] {
        overflow: hidden !important;
        max-height: 100vh !important;
    }
}
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* Ambient background glow */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse at 15% 20%, rgba(130,40,220,.20) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 80%, rgba(220,40,110,.16) 0%, transparent 55%),
        radial-gradient(ellipse at 50% 50%, rgba(40,40,160,.14) 0%, transparent 75%);
}
[data-testid="stMain"] { position: relative; z-index: 1; }

/* ── Branding header ── */
.brand-tag {
    font-family: 'Orbitron', monospace;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .22em;
    color: #9d6fff;
    text-align: center;
    text-transform: uppercase;
    margin-bottom: .25rem;
    opacity: .85;
}
.brand-tag span { color: #ff6bba; }

.game-title {
    font-family: 'Orbitron', monospace;
    font-size: clamp(1.1rem, 2.8vw, 1.9rem);
    font-weight: 900;
    text-align: center;
    background: linear-gradient(120deg, #ff6bba 0%, #da70d6 40%, #9d6fff 70%, #6eb6ff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    filter: drop-shadow(0 0 14px rgba(200,100,255,.35));
    line-height: 1.15;
    margin-bottom: .15rem;
}
.game-subtitle {
    text-align: center;
    color: #9070b8;
    font-size: .78rem;
    letter-spacing: .08em;
    margin-bottom: .6rem;
}

/* ── Card ── */
.slc-card {
    background: rgba(255,255,255,.042);
    border: 1px solid rgba(160,100,255,.18);
    border-radius: 18px;
    padding: 1rem 1.2rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 6px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.07);
}

/* ── Section label ── */
.slc-label {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .14em;
    color: #9d6fff;
    text-transform: uppercase;
    margin-bottom: .4rem;
}

/* ── Role cards ── */
.role-card {
    border-radius: 12px;
    padding: .55rem .7rem;
    text-align: center;
    font-weight: 700;
    font-size: .82rem;
    line-height: 1.4;
    margin-bottom: .4rem;
    transition: transform .15s;
    cursor: default;
}
.role-card.male {
    background: linear-gradient(135deg, rgba(10,35,90,.9), rgba(20,60,140,.9));
    border: 1.5px solid rgba(110,182,255,.45);
}
.role-card.female {
    background: linear-gradient(135deg, rgba(80,8,35,.9), rgba(140,20,70,.9));
    border: 1.5px solid rgba(255,107,186,.45);
}
.role-card .rc-icon { font-size: 1.3rem; display: block; margin-bottom: .2rem; }
.role-card .rc-hint { font-size: .7rem; font-weight: 500; opacity: .75; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6b1fcf, #c2185b) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: .85rem !important;
    padding: .45rem .9rem !important;
    transition: all .18s !important;
    box-shadow: 0 3px 14px rgba(107,31,207,.32) !important;
    letter-spacing: .03em !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 22px rgba(107,31,207,.5) !important;
    background: linear-gradient(135deg, #7d30e0, #d4256b) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,.06) !important;
    border: 1.5px solid rgba(160,100,255,.28) !important;
    border-radius: 9px !important;
    color: #e8deff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .88rem !important;
    padding: .4rem .7rem !important;
}
.stTextInput > div > div > input::placeholder { color: rgba(200,160,255,.4) !important; }
.stTextInput > div > div > input:focus {
    border-color: #a060f0 !important;
    box-shadow: 0 0 0 2px rgba(160,96,240,.25) !important;
    outline: none !important;
}
.stTextInput > label { color: #9070b8 !important; font-size: .78rem !important; }

/* ── Room code display ── */
.room-code-box {
    font-family: 'Orbitron', monospace;
    font-size: 1.6rem;
    font-weight: 900;
    letter-spacing: .28em;
    color: #ffd700;
    text-align: center;
    background: rgba(255,215,0,.07);
    border: 1.5px solid rgba(255,215,0,.3);
    border-radius: 12px;
    padding: .5rem 1rem;
    text-shadow: 0 0 16px rgba(255,215,0,.5);
    display: block;
}

/* ── Player status rows (waiting room) ── */
.ps-row {
    display: flex; align-items: center; gap: .6rem;
    padding: .5rem .8rem; border-radius: 9px; margin: .25rem 0;
    font-weight: 600; font-size: .85rem;
}
.ps-row.ok  { background: rgba(40,200,90,.1);  border: 1px solid rgba(40,200,90,.28); }
.ps-row.wait{ background: rgba(200,90,40,.1);  border: 1px solid rgba(200,90,40,.28); }

/* ── How-to-play mini grid ── */
.htp-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .3rem .8rem;
    font-size: .72rem;
    color: #8868aa;
    line-height: 1.5;
}
.htp-grid span { color: #c09ae8; }

/* ── Winner screen ── */
.winner-wrap { text-align: center; padding: 1.2rem; }
.winner-emoji { font-size: 3.2rem; display: block; animation: wBounce .9s ease-in-out infinite alternate; margin: .5rem 0; }
@keyframes wBounce { from{transform:translateY(0) scale(1)} to{transform:translateY(-14px) scale(1.08)} }
.winner-title {
    font-family: 'Orbitron', monospace;
    font-size: clamp(1.4rem, 3.5vw, 2.4rem);
    font-weight: 900;
    background: linear-gradient(135deg, #ffd700, #ff69b4, #da70d6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin: .3rem 0;
}
.winner-sub { font-size: 1rem; color: #b890d8; }

/* ── Leaderboard ── */
.lb-row {
    display: flex; align-items: center; gap: .5rem;
    padding: .35rem .65rem; border-radius: 8px; margin: .18rem 0;
    background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.06);
    font-size: .78rem;
}
.lb-rank { font-family: 'Orbitron', monospace; font-size: .85rem; color: #ffd700; min-width: 1.6rem; }
.lb-name { flex: 1; font-weight: 600; }
.lb-w { color: #6eff9a; font-weight: 700; }
.lb-l { color: #ff6e6e; font-weight: 700; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,.03); }
::-webkit-scrollbar-thumb { background: rgba(160,80,200,.35); border-radius: 3px; }

/* ── Confetti canvas ── */
#confetti-canvas { position: fixed; inset: 0; z-index: 9999; pointer-events: none; }

/* ── Info/success/error tweaks ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: .82rem !important;
}

/* hide Streamlit column gaps bleeding into lobby */
[data-testid="column"] { padding: 0 4px !important; }

/* Mobile: make lobby full-width, remove gutters */
@media (max-width: 600px) {
    [data-testid="block-container"] {
        padding-left: 8px !important;
        padding-right: 8px !important;
    }
    /* Force gutter columns to zero on mobile */
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
        display: none !important;
        flex: 0 !important;
        min-width: 0 !important;
        width: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
        flex: 1 1 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
    }
    .slc-card {
        border-radius: 12px !important;
        padding: .75rem !important;
    }
    .game-title {
        font-size: 1.25rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ================================================================================
# LOBBY HEADER  (used by lobby + waiting room)
# ================================================================================
def render_lobby():
    st.markdown(
        '<div class="brand-tag">🎮 <span>BIRADR\'S GAMES</span></div>'
        '<div class="game-title">❤️ Snake Love Chase 💜</div>'
        '<div class="game-subtitle">A real-time 2-player love pursuit game</div>',
        unsafe_allow_html=True,
    )


# ================================================================================
# WAITING ROOM
# ================================================================================
def render_waiting_room(code: str, room: dict, my_role: str):
    render_lobby()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="slc-card">', unsafe_allow_html=True)
        st.markdown("### 🏠 Waiting Room")
        st.markdown(f'<div class="room-code-box">{code}</div>', unsafe_allow_html=True)
        st.markdown(
            '<p style="text-align:center;color:#806090;font-size:.78rem;margin:.4rem 0 .6rem">'
            'Share this code with your friend</p>',
            unsafe_allow_html=True,
        )

        for role_label, data, color in [
            ("💙 Male Snake",   room.get("male",   {}), "#6eb6ff"),
            ("💗 Female Snake", room.get("female", {}), "#ff8abf"),
        ]:
            connected = data.get("connected", False)
            name      = data.get("name", "Waiting…")
            status    = "ok" if connected else "wait"
            dot       = "🟢" if connected else "⏳"
            st.markdown(
                f'<div class="ps-row {status}">'
                f'<span>{dot}</span>'
                f'<span style="color:{color};font-size:.85rem">{role_label}</span>'
                f'<span style="margin-left:auto;color:#c8c0d8;font-size:.83rem">'
                f'{"<b>"+name+"</b>" if connected else "Waiting…"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if room.get("state") == "playing":
            st.success("🚀 Both players ready! Starting…")
        else:
            st.markdown(
                '<p style="text-align:center;margin-top:.6rem;color:#9070b8;font-size:.82rem">'
                '⏳ Waiting for the second player to join…</p>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;gap:1.2rem;justify-content:center;flex-wrap:wrap;'
            'font-size:.72rem;color:#806090;margin-top:.4rem">'
            '<span>💙 Male: <b style="color:#9d6fff">WASD</b></span>'
            '<span>💗 Female: <b style="color:#ff6bba">Arrow keys</b></span>'
            '</div>',
            unsafe_allow_html=True,
        )


# ================================================================================
# GAME BOARD  –  click-to-move, no-flicker, redesigned dashboard
# ================================================================================
def render_game_board(room: dict, my_role: str, db_url: str):
    """
    Renders the full game dashboard as a self-contained HTML iframe.
    Board cell size: 12 px  →  20×12 = 240 px  (≈35% smaller than original 360 px).
    All movement / Firebase / sync logic is identical to the original.
    Reduced obstacles handled in game_logic.py generate_map().
    """
    CELL     = 12           # px per cell  →  240 px board
    BOARD_PX = MAP_SIZE * CELL  # 240

    room_json        = json.dumps(room)
    tile_emojis_json = json.dumps(TILE_EMOJIS)
    tile_colors_json = json.dumps(TILE_COLORS)
    blocked_json     = json.dumps([TILE_TREE, TILE_ROCK, TILE_WATER])
    pu_tiles_json    = json.dumps([TILE_HEART, TILE_FLOWER, TILE_STAR, TILE_COMPASS])
    code             = room.get("__code__", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{
  width:100%;height:100%;overflow:hidden;
  background:#07071a;color:#e8deff;
  font-family:'Inter',system-ui,sans-serif;
  -webkit-tap-highlight-color:transparent;
}}
body{{
  display:flex;flex-direction:column;
  height:100%;
}}

/* ── TOP BAR ── */
#topbar{{
  display:flex;align-items:center;justify-content:space-between;
  padding:7px 14px 6px;
  background:linear-gradient(90deg,rgba(30,10,70,.85),rgba(10,10,40,.85));
  border-bottom:1px solid rgba(160,100,255,.18);
  flex-shrink:0;
  gap:6px;
}}
.tb-player{{
  display:flex;align-items:center;gap:6px;
  font-size:.78rem;font-weight:600;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.1);
  border-radius:8px;padding:4px 10px;
  min-width:0;flex-shrink:1;
}}
.tb-player.mine {{ border-color:rgba(110,182,255,.3); }}
.tb-player.theirs{{ border-color:rgba(255,107,186,.3); }}
.tb-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.tb-dot.m{{background:#6eb6ff;box-shadow:0 0 5px #6eb6ff}}
.tb-dot.f{{background:#ff6bba;box-shadow:0 0 5px #ff6bba}}
.tb-name{{font-size:.8rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:90px}}
.tb-boost{{font-size:.72rem;opacity:.85}}
#timer{{
  font-family:'Orbitron',monospace;
  font-size:1.05rem;font-weight:900;
  color:#ffd700;
  text-shadow:0 0 10px rgba(255,215,0,.5);
  letter-spacing:.06em;
  flex-shrink:0;
  white-space:nowrap;
}}
#timer.urgent{{color:#ff4040;animation:blinkT .5s ease-in-out infinite alternate}}
@keyframes blinkT{{from{{text-shadow:0 0 6px rgba(255,50,50,.3)}}to{{text-shadow:0 0 18px rgba(255,50,50,.9)}}}}

/* ── MAIN ROW: board + right panel ── */
#main{{
  display:flex;
  flex:1;
  overflow:hidden;
  padding:8px 10px 8px;
  gap:10px;
  align-items:flex-start;
  justify-content:center;
}}

/* ── BOARD column ── */
#board-col{{
  display:flex;flex-direction:column;align-items:center;gap:6px;
  flex-shrink:0;
}}
#board{{
  border-radius:6px;
  box-shadow:0 0 28px rgba(160,80,220,.25),0 0 6px rgba(110,182,255,.1);
  image-rendering:pixelated;
  display:block;
}}
.board-label{{
  font-size:.65rem;color:#604880;letter-spacing:.1em;
}}

/* ── RIGHT PANEL ── */
#panel{{
  display:flex;flex-direction:column;gap:8px;
  width:148px;flex-shrink:0;
}}

/* ── Panel card ── */
.pc{{
  background:rgba(255,255,255,.04);
  border:1px solid rgba(160,100,255,.14);
  border-radius:12px;padding:8px 10px;
}}
.pc-title{{
  font-size:.64rem;font-weight:700;letter-spacing:.14em;
  color:#7050a0;text-transform:uppercase;margin-bottom:5px;
}}

/* ── Players card ── */
.pl-row{{
  display:flex;align-items:center;gap:6px;
  padding:5px 8px;border-radius:8px;margin-bottom:4px;
  font-size:.75rem;font-weight:600;
}}
.pl-row.m{{background:rgba(30,70,180,.15);border:1px solid rgba(110,182,255,.2)}}
.pl-row.f{{background:rgba(160,20,80,.15);border:1px solid rgba(255,107,186,.2)}}
.pl-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.pl-dot.m{{background:#6eb6ff}}
.pl-dot.f{{background:#ff6bba}}
.pl-online{{width:6px;height:6px;border-radius:50%;background:#44ee88;box-shadow:0 0 5px #44ee88;flex-shrink:0;margin-left:auto}}

/* ── D-pad ── */
#dpad{{
  display:flex;flex-direction:column;align-items:center;gap:3px;
  user-select:none;
}}
.drow{{display:flex;gap:3px}}
.dbtn{{
  width:38px;height:38px;font-size:16px;
  border-radius:9px;
  background:linear-gradient(135deg,#5b1aaf,#a01048);
  border:none;color:#fff;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 8px rgba(100,30,180,.4);
  touch-action:manipulation;
  transition:transform .07s,background .07s;
}}
.dbtn:active,.dbtn.pressed{{
  transform:scale(.82);
  background:linear-gradient(135deg,#3a0e80,#780828);
}}
.dspacer{{width:38px;height:38px}}
#kb-hint{{font-size:.62rem;color:#604880;text-align:center;margin-top:2px;line-height:1.7}}

/* ── Game info card ── */
.gi-row{{
  display:flex;align-items:center;gap:5px;
  font-size:.72rem;color:#9070b8;margin-bottom:2px;
}}
.gi-row b{{color:#e8deff;font-weight:600}}

/* ── Overlay ── */
#overlay{{
  display:none;position:fixed;inset:0;z-index:100;
  background:rgba(7,7,26,.92);backdrop-filter:blur(10px);
  flex-direction:column;align-items:center;justify-content:center;gap:12px;
}}
#overlay.show{{display:flex}}
#ov-title{{
  font-family:'Orbitron',monospace;
  font-size:1.7rem;font-weight:900;text-align:center;line-height:1.3;
  background:linear-gradient(135deg,#ffd700,#ff69b4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
#ov-sub{{font-size:.95rem;color:#c8a0e8;text-align:center}}
#ov-note{{font-size:.7rem;color:#604880;margin-top:4px}}

/* ── Mobile ── */
@media(max-width:520px){{
  #main{{padding:4px 4px 4px;gap:4px;}}
  #panel{{width:100px}}
  .dbtn{{width:36px;height:36px;font-size:15px}}
  .dspacer{{width:36px;height:36px}}
  .tb-name{{max-width:55px}}
  #topbar{{padding:5px 8px 4px;}}
  #timer{{font-size:.9rem;}}
  .tb-player{{padding:3px 6px;}}
  .pc{{padding:6px 7px;border-radius:9px;}}
  .pc-title{{font-size:.6rem;margin-bottom:3px;}}
  .pl-row{{padding:4px 6px;font-size:.7rem;}}
  .gi-row{{font-size:.66rem;}}
}}
</style>
</head>
<body>

<!-- TOP BAR -->
<div id="topbar">
  <div class="tb-player mine" id="tb-me">
    <div class="tb-dot m" id="tb-dot-me"></div>
    <span class="tb-name" id="tb-me-name">You</span>
    <span class="tb-boost" id="tb-me-boost"></span>
  </div>

  <div id="timer">⏱ 02:00</div>

  <div class="tb-player theirs" id="tb-op">
    <div class="tb-dot f" id="tb-dot-op"></div>
    <span class="tb-name" id="tb-op-name">Opponent</span>
    <span class="tb-boost" id="tb-op-boost"></span>
  </div>
</div>

<!-- MAIN -->
<div id="main">

  <!-- BOARD -->
  <div id="board-col">
    <canvas id="board" width="{BOARD_PX}" height="{BOARD_PX}"></canvas>
    <div class="board-label" id="role-lbl">…</div>
  </div>

  <!-- RIGHT PANEL -->
  <div id="panel">

    <!-- Players -->
    <div class="pc">
      <div class="pc-title">Players</div>
      <div class="pl-row m">
        <div class="pl-dot m"></div>
        <span id="pn-male" style="color:#6eb6ff">Male</span>
        <div class="pl-online"></div>
      </div>
      <div class="pl-row f">
        <div class="pl-dot f"></div>
        <span id="pn-female" style="color:#ff6bba">Female</span>
        <div class="pl-online"></div>
      </div>
    </div>

    <!-- Controls -->
    <div class="pc">
      <div class="pc-title">Controls</div>
      <div id="dpad">
        <div class="drow">
          <div class="dspacer"></div>
          <button class="dbtn" id="db-UP"    onpointerdown="dpad(event,'UP')">⬆</button>
          <div class="dspacer"></div>
        </div>
        <div class="drow">
          <button class="dbtn" id="db-LEFT"  onpointerdown="dpad(event,'LEFT')">⬅</button>
          <button class="dbtn" id="db-DOWN"  onpointerdown="dpad(event,'DOWN')">⬇</button>
          <button class="dbtn" id="db-RIGHT" onpointerdown="dpad(event,'RIGHT')">➡</button>
        </div>
      </div>
      <div id="kb-hint">💙 WASD &nbsp; 💗 Arrows</div>
    </div>

    <!-- Game Info -->
    <div class="pc">
      <div class="pc-title">Game Info</div>
      <div class="gi-row">❤️ <b>Heart</b> → speed boost</div>
      <div class="gi-row">🌸 <b>Flower</b> → speed boost</div>
      <div class="gi-row">⭐ <b>Star</b> → shield</div>
      <div class="gi-row">🔍 <b>Lens</b> → compass</div>
      <div class="gi-row" style="margin-top:4px">🌳🪨💧 → blocked</div>
    </div>

  </div>
</div>

<div id="overlay">
  <div id="ov-title">Game Over</div>
  <div id="ov-sub"></div>
  <div id="ov-note">Returning to menu…</div>
</div>

<script>
// ═══════════════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════════════
const DB_URL     = {json.dumps(db_url)};
const MY_ROLE    = {json.dumps(my_role)};
const OTHER_ROLE = MY_ROLE === 'male' ? 'female' : 'male';
const ROOM_CODE  = {json.dumps(code)};
const MAP_SZ     = {MAP_SIZE};
const GAME_DUR   = {GAME_DURATION};
const SPD_BOOST  = {SPEED_BOOST};
const PU_DUR     = {POWERUP_DURATION};
const CELL       = {CELL};

const T_EMPTY=0,T_TREE=1,T_ROCK=2,T_BUSH=3,T_WATER=4,
      T_HEART=5,T_FLOWER=6,T_STAR=7,T_COMPASS=8;
const BLOCKED  = new Set({blocked_json});
const PU_TILES = new Set({pu_tiles_json});
const EMOJIS   = {tile_emojis_json};
const COLORS   = {tile_colors_json};

// ═══════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════
let G        = JSON.parse({json.dumps(room_json)});
let myPos    = (G[MY_ROLE]||{{}}).pos  || [Math.floor(MAP_SZ/2), Math.floor(MAP_SZ/2)];
let myDir    = (G[MY_ROLE]||{{}}).dir  || (MY_ROLE==='male'?'RIGHT':'LEFT');
let myData   = Object.assign({{}}, G[MY_ROLE]||{{}});

let gameEnded = false;
let _moving   = false;

const canvas = document.getElementById('board');
const ctx    = canvas.getContext('2d');

// ═══════════════════════════════════════════════════════════════════════
// FIREBASE HELPERS  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
function fbUrl(path){{return DB_URL+'/'+path.replace(/^\\/+/,'')+'.json'}}
async function fbGet(path){{
  try{{const r=await fetch(fbUrl(path));return r.ok?r.json():null}}catch{{return null}}
}}
async function fbPatch(path,data){{
  try{{await fetch(fbUrl(path),{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}})}}catch{{}}
}}
async function fbPut(path,val){{
  try{{await fetch(fbUrl(path),{{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(val)}})}}catch{{}}
}}

// ═══════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════
function fmtTime(s){{
  s=Math.max(0,Math.floor(s));
  return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
}}
function tickPU(p,now){{
  if((p.speed_until||0)>0&&now>p.speed_until)  {{p.speed=1;p.speed_until=0}}
  if((p.shield_until||0)>0&&now>p.shield_until) {{p.shield=0;p.shield_until=0}}
  if((p.compass_until||0)>0&&now>p.compass_until){{p.compass=0;p.compass_until=0}}
  return p;
}}
function applyPU(p,tile,now){{
  const dur=PU_DUR;
  if(tile===T_HEART||tile===T_FLOWER){{p.speed=SPD_BOOST;p.speed_until=now+dur}}
  else if(tile===T_STAR)   {{p.shield=1;p.shield_until=now+dur}}
  else if(tile===T_COMPASS){{p.compass=1;p.compass_until=now+dur}}
  return p;
}}

// ═══════════════════════════════════════════════════════════════════════
// RENDER  (emoji font for tiles, glows for snakes)
// ═══════════════════════════════════════════════════════════════════════
function draw(){{
  const map   = G.map||[];
  const mPos  = (G.male||{{}}).pos||[0,0];
  const fPos  = (G.female||{{}}).pos||[MAP_SZ-1,MAP_SZ-1];
  const mSh   = (G.male||{{}}).shield;
  const fSh   = (G.female||{{}}).shield;

  for(let y=0;y<MAP_SZ;y++){{
    for(let x=0;x<MAP_SZ;x++){{
      const tile=(map[y]||[])[x]||0;
      const px=x*CELL, py=y*CELL;
      let bg,em,glow=null;

      if(mPos[0]===x&&mPos[1]===y){{
        em=mSh?'🛡️':'🐍'; bg='#0a1e60'; glow='#4a90e2';
      }}else if(fPos[0]===x&&fPos[1]===y){{
        em=fSh?'🛡️':'🐍'; bg='#500310'; glow='#e24a80';
      }}else{{
        em=EMOJIS[tile]||'⬛'; bg=COLORS[tile]||'#0d0d22';
      }}

      ctx.fillStyle=bg;
      ctx.fillRect(px,py,CELL,CELL);

      if(glow){{
        ctx.save();
        ctx.shadowColor=glow;ctx.shadowBlur=7;
        ctx.strokeStyle=glow;ctx.lineWidth=1.2;
        ctx.strokeRect(px+.6,py+.6,CELL-1.2,CELL-1.2);
        ctx.restore();
      }}

      ctx.strokeStyle='rgba(255,255,255,.025)';
      ctx.lineWidth=.5;
      ctx.strokeRect(px,py,CELL,CELL);

      ctx.font=Math.floor(CELL*.72)+'px serif';
      ctx.textAlign='center';
      ctx.textBaseline='middle';
      ctx.fillText(em,px+CELL/2,py+CELL/2);
    }}
  }}
}}

// ═══════════════════════════════════════════════════════════════════════
// HUD  (top bar + panel names)
// ═══════════════════════════════════════════════════════════════════════
function updateHUD(){{
  const now     = Date.now()/1000;
  const start   = G.start_time||now;
  const rem     = Math.max(0, GAME_DUR-(now-start));
  const ts      = fmtTime(rem);
  const urgent  = rem<=20;

  const tEl=document.getElementById('timer');
  tEl.textContent='⏱ '+ts;
  tEl.className=urgent?'urgent':'';

  const m=G.male||{{}}, f=G.female||{{}};
  const mBoost = m.speed>1?'⚡':(m.shield?'🛡️':(m.compass?'🔍':''));
  const fBoost = f.speed>1?'⚡':(f.shield?'🛡️':'');

  // top bar
  document.getElementById('tb-me-name').textContent  = MY_ROLE==='male'? (m.name||'You'):(f.name||'You');
  document.getElementById('tb-op-name').textContent  = MY_ROLE==='male'? (f.name||'Opp'):(m.name||'Opp');
  document.getElementById('tb-me-boost').textContent = MY_ROLE==='male'? mBoost:fBoost;
  document.getElementById('tb-op-boost').textContent = MY_ROLE==='male'? fBoost:mBoost;

  // dot colors
  const myDot=document.getElementById('tb-dot-me');
  const opDot=document.getElementById('tb-dot-op');
  if(MY_ROLE==='male'){{
    myDot.className='tb-dot m'; opDot.className='tb-dot f';
  }}else{{
    myDot.className='tb-dot f'; opDot.className='tb-dot m';
  }}

  // right panel names
  document.getElementById('pn-male').textContent   = m.name||'Male';
  document.getElementById('pn-female').textContent = f.name||'Female';

  // compass arrow hint
  if(MY_ROLE==='male'&&m.compass){{
    const mp=m.pos||[0,0], fp=f.pos||[0,0];
    const dx=fp[0]-mp[0], dy=fp[1]-mp[1];
    const arrow=Math.abs(dx)>=Math.abs(dy)?(dx>0?'→':'←'):(dy>0?'↓':'↑');
    document.getElementById('tb-me-boost').textContent='🔍'+arrow;
  }}
}}

// ═══════════════════════════════════════════════════════════════════════
// MOVE  (unchanged logic from original)
// ═══════════════════════════════════════════════════════════════════════
const OPPOSITES={{UP:'DOWN',DOWN:'UP',LEFT:'RIGHT',RIGHT:'LEFT'}};
const DX={{UP:0,DOWN:0,LEFT:-1,RIGHT:1}};
const DY={{UP:-1,DOWN:1,LEFT:0,RIGHT:0}};

async function moveOne(dir){{
  if(gameEnded||_moving) return;
  if(dir===OPPOSITES[myDir]) return;

  _moving=true;
  setTimeout(()=>{{_moving=false}},200);

  myDir=dir;
  const now=Date.now()/1000;
  const nx=((myPos[0]+DX[dir])+MAP_SZ)%MAP_SZ;
  const ny=((myPos[1]+DY[dir])+MAP_SZ)%MAP_SZ;
  const map=G.map||[];
  const tile=(map[ny]||[])[nx]||0;

  if(BLOCKED.has(tile)){{_moving=false;return}}

  myPos=[nx,ny];
  myData=tickPU(Object.assign({{}},myData),now);
  myData.pos=myPos;
  myData.dir=myDir;

  if(PU_TILES.has(tile)){{
    myData=applyPU(myData,tile,now);
    if(map[ny]) map[ny][nx]=T_EMPTY;
    fbPut('rooms/'+ROOM_CODE+'/map/'+ny+'/'+nx,T_EMPTY);
  }}

  G[MY_ROLE]=myData;
  await fbPatch('rooms/'+ROOM_CODE+'/'+MY_ROLE,myData);

  const other=G[OTHER_ROLE]||{{}};
  if(other.pos&&other.pos[0]===nx&&other.pos[1]===ny){{
    const mn=(G.male||{{}}).name||'Male Snake';
    await endGame('male',mn+' WINS!\\nLOVE FOUND ❤️');
    return;
  }}

  const start=G.start_time||(Date.now()/1000);
  if(GAME_DUR-(now-start)<=0){{
    const fn=(G.female||{{}}).name||'Female Snake';
    await endGame('female',fn+' WINS!\\nSUCCESSFULLY ESCAPED 🌸');
    return;
  }}

  draw(); updateHUD();
}}

// ═══════════════════════════════════════════════════════════════════════
// OPPONENT SYNC  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
async function syncOpponent(){{
  if(gameEnded) return;
  const fresh=await fbGet('rooms/'+ROOM_CODE);
  if(!fresh) return;

  if(fresh.state==='ended'){{
    const wd=fresh.winner||{{}};
    if(!gameEnded){{
      gameEnded=true;
      showOverlay((wd.reason)||'Game Over');
      signalParent(wd.winner_role||'male',wd.reason||'Game Over',
                   (fresh.male||{{}}).name||'?',(fresh.female||{{}}).name||'?');
    }}
    return;
  }}

  const myLocal=G[MY_ROLE];
  G=fresh;
  G[MY_ROLE]=myLocal;

  draw(); updateHUD();
}}

// ═══════════════════════════════════════════════════════════════════════
// TIMER  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
function timerTick(){{
  if(gameEnded) return;
  const now=Date.now()/1000;
  const start=G.start_time||now;
  const rem=GAME_DUR-(now-start);
  if(rem<=0&&MY_ROLE==='male'){{
    const fn=(G.female||{{}}).name||'Female Snake';
    endGame('female',fn+' WINS!\\nSUCCESSFULLY ESCAPED 🌸');
  }}
  updateHUD();
}}

// ═══════════════════════════════════════════════════════════════════════
// GAME END  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
async function endGame(winnerRole,reason){{
  if(gameEnded) return;
  gameEnded=true;

  const cur=await fbGet('rooms/'+ROOM_CODE+'/state');
  const m=G.male||{{}},f=G.female||{{}};

  if(cur!=='ended'){{
    const wd={{winner_role:winnerRole,reason,
               male_name:m.name||'?',female_name:f.name||'?'}};
    await fbPatch('rooms/'+ROOM_CODE,{{state:'ended',winner:wd}});

    if(winnerRole==='male'){{
      fbPatch('rooms/'+ROOM_CODE+'/male',   {{score_wins:(m.score_wins||0)+1,  score_matches:(m.score_matches||0)+1}});
      fbPatch('rooms/'+ROOM_CODE+'/female', {{score_losses:(f.score_losses||0)+1,score_matches:(f.score_matches||0)+1}});
    }}else{{
      fbPatch('rooms/'+ROOM_CODE+'/female', {{score_wins:(f.score_wins||0)+1,  score_matches:(f.score_matches||0)+1}});
      fbPatch('rooms/'+ROOM_CODE+'/male',   {{score_losses:(m.score_losses||0)+1,score_matches:(m.score_matches||0)+1}});
    }}
  }}

  showOverlay(reason);
  signalParent(winnerRole,reason,m.name||'?',f.name||'?');
}}

function showOverlay(reason){{
  const lines=reason.split('\\n');
  document.getElementById('ov-title').textContent=lines[0]||'Game Over';
  document.getElementById('ov-sub').textContent  =lines[1]||'';
  document.getElementById('overlay').classList.add('show');
}}

// ═══════════════════════════════════════════════════════════════════════
// SIGNAL PARENT  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
function signalParent(wr,reason,mn,fn){{
  const signal=[wr,reason,mn,fn].join('||');
  try{{
    let w=window;
    while(w.parent&&w.parent!==w) w=w.parent;
    const docs=[w.document];
    w.document.querySelectorAll('iframe').forEach(f=>{{
      try{{docs.push(f.contentDocument)}}catch(e){{}}
    }});
    for(const doc of docs){{
      if(!doc) continue;
      const inp=doc.querySelector('input[aria-label="game_ended_signal"]');
      if(inp){{
        const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        setter.call(inp,signal);
        inp.dispatchEvent(new Event('input',{{bubbles:true}}));
        return;
      }}
    }}
  }}catch(e){{}}
}}

// ═══════════════════════════════════════════════════════════════════════
// KEYBOARD INPUT  (unchanged from original)
// ═══════════════════════════════════════════════════════════════════════
const KEY_MAP={{
  ArrowUp:'UP',w:'UP',W:'UP',
  ArrowDown:'DOWN',s:'DOWN',S:'DOWN',
  ArrowLeft:'LEFT',a:'LEFT',A:'LEFT',
  ArrowRight:'RIGHT',d:'RIGHT',D:'RIGHT',
}};
function attachKb(win){{
  win.addEventListener('keydown',function(e){{
    const dir=KEY_MAP[e.key];
    if(!dir) return;
    e.preventDefault();
    moveOne(dir);
  }},{{passive:false}});
}}
try{{
  let top=window;
  while(top.parent&&top.parent!==top) top=top.parent;
  attachKb(top);
}}catch(e){{attachKb(window);}}

// ═══════════════════════════════════════════════════════════════════════
// D-PAD BUTTONS
// ═══════════════════════════════════════════════════════════════════════
function dpad(evt,dir){{
  evt.preventDefault();
  moveOne(dir);
  const btn=document.getElementById('db-'+dir);
  if(btn){{btn.classList.add('pressed');setTimeout(()=>btn.classList.remove('pressed'),140);}}
}}

// ═══════════════════════════════════════════════════════════════════════
// BOOT
// ═══════════════════════════════════════════════════════════════════════
(function init(){{
  const rc  = MY_ROLE==='male'?'#6eb6ff':'#ff6bba';
  const rl  = MY_ROLE==='male'?'💙 You (WASD)':'💗 You (Arrows)';
  const lbl = document.getElementById('role-lbl');
  lbl.textContent=rl; lbl.style.color=rc;

  myPos  = (G[MY_ROLE]||{{}}).pos || [Math.floor(MAP_SZ/2),Math.floor(MAP_SZ/2)];
  myDir  = (G[MY_ROLE]||{{}}).dir || (MY_ROLE==='male'?'RIGHT':'LEFT');
  myData = Object.assign({{}}, G[MY_ROLE]||{{}});
  // Set initial snake length to 8
  if(!myData.length) myData.length = 8;

  draw();
  updateHUD();

  setInterval(syncOpponent, 500);
  setInterval(timerTick,   1000);
}})();
</script>
</body>
</html>"""

    # Height: topbar ~46 + main ~370 + breathing room = 440
    components.html(html, height=440, scrolling=False)


# ================================================================================
# WINNER SCREEN
# ================================================================================
def render_winner_screen(winner_data: dict):
    wr     = winner_data.get("winner_role", "male")
    reason = winner_data.get("reason", "Game Over!")
    lines  = reason.split("\n")
    title  = lines[0] if lines else "Winner!"
    sub    = lines[1] if len(lines) > 1 else ""

    if wr == "male":
        emoji = "💙"; ca, cb = "#4a90e2", "#6eb6ff"; glow = "rgba(74,144,226,.12)"
    else:
        emoji = "💗"; ca, cb = "#e24a80", "#ff8abf"; glow = "rgba(226,74,128,.12)"

    st.markdown(f"""
<div style="background:radial-gradient(ellipse at center,{glow} 0%,transparent 70%);
            border-radius:22px;padding:1.2rem;text-align:center;">
  <div class="winner-wrap">
    <span class="winner-emoji">{emoji}</span>
    <div class="winner-title"
         style="background:linear-gradient(135deg,{ca},{cb},#ffd700);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{title}</div>
    <div class="winner-sub">{sub}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<canvas id="confetti-canvas"></canvas>
<script>
(function(){
  const c=document.getElementById('confetti-canvas');
  if(!c||c._r)return;c._r=true;
  const x=c.getContext('2d');
  c.width=window.innerWidth;c.height=window.innerHeight;
  const S=['❤️','🌸','⭐','✨','💖','🌟'];
  const p=Array.from({length:55},()=>({
    x:Math.random()*c.width,y:-20-Math.random()*140,
    size:9+Math.random()*14,
    shape:S[Math.floor(Math.random()*S.length)],
    vy:1.6+Math.random()*2.8,vx:(Math.random()-.5)*2,
    rot:Math.random()*Math.PI*2,vr:(Math.random()-.5)*.11,
    a:.7+Math.random()*.3
  }));
  let f=0;
  function a(){
    if(f++>280){x.clearRect(0,0,c.width,c.height);return;}
    x.clearRect(0,0,c.width,c.height);
    p.forEach(q=>{
      q.x+=q.vx;q.y+=q.vy;q.rot+=q.vr;
      if(q.y>c.height+30)q.y=-30;
      x.save();x.globalAlpha=q.a;x.translate(q.x,q.y);x.rotate(q.rot);
      x.font=q.size+'px serif';x.textAlign='center';x.textBaseline='middle';
      x.fillText(q.shape,0,0);x.restore();
    });
    requestAnimationFrame(a);
  }
  a();
})();
</script>""", unsafe_allow_html=True)


# ================================================================================
# LEADERBOARD
# ================================================================================
def render_leaderboard(fb):
    try:
        data = fb.get("leaderboard") or {}
        if not data:
            return
        values  = list(data.values()) if isinstance(data, dict) else [v for v in data if v]
        players = sorted(values, key=lambda p: (-p.get("wins", 0), -p.get("matches", 0)))[:8]
        if not players:
            return

        st.markdown(
            '<div class="slc-label" style="margin-top:.6rem">🏆 Leaderboard</div>',
            unsafe_allow_html=True,
        )
        ranks = ["🥇", "🥈", "🥉"]
        rows = []
        for i, p in enumerate(players):
            rank = ranks[i] if i < 3 else f"#{i+1}"
            rows.append(
                f'<div class="lb-row">'
                f'<span class="lb-rank">{rank}</span>'
                f'<span class="lb-name">{p.get("name","?")}</span>'
                f'<span class="lb-w">🏆{p.get("wins",0)}</span>'
                f'<span class="lb-l">💔{p.get("losses",0)}</span>'
                f'<span style="color:#604880;font-size:.7rem">🎮{p.get("matches",0)}</span>'
                f'</div>'
            )
        st.markdown("".join(rows), unsafe_allow_html=True)
    except Exception:
        pass
