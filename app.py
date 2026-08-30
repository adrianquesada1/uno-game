import base64
import io
import math
import random
import string
import struct
import threading
import time
import wave
from collections import Counter

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ----------------------------------------------------------------------------
# CONFIGURACIÓN VISUAL
# ----------------------------------------------------------------------------
st.set_page_config(page_title="UNO", page_icon="🎴", layout="wide")

_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>
html, body, .stApp, [class*="css"] { font-family: 'Fredoka', 'Segoe UI', sans-serif; }
.stApp {
    background:
        radial-gradient(circle at 20% 0%, #241a3d 0%, transparent 45%),
        radial-gradient(circle at 80% 10%, #1a2e3d 0%, transparent 45%),
        linear-gradient(180deg, #100a22 0%, #0a0715 100%);
    color: #f4f1fa;
}
.stApp h1, .stApp h2 { text-align: center; font-weight: 800 !important; }
h3 { font-weight: 700 !important; }
.stButton>button {
    border-radius: 18px !important;
    border: none !important;
    padding: 0.55rem 0.4rem !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    font-family: 'Fredoka', sans-serif !important;
    box-shadow: 0 6px 14px rgba(0,0,0,0.45) !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    min-height: 4.6rem !important;
}
.stButton>button:hover:not(:disabled) {
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 10px 20px rgba(0,0,0,0.55) !important;
}
.stButton>button:disabled { opacity: 0.3 !important; box-shadow: none !important; }
.stButton>button[kind="primary"] { box-shadow: 0 0 0 3px #ffd60a55, 0 6px 14px rgba(0,0,0,0.5) !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px !important;
    background: linear-gradient(160deg, #1c1433 0%, #14102a 100%);
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}
.room-code {
    font-size: 2.6rem; letter-spacing: 0.5rem; color: #ffd60a; font-weight: 900;
    text-align:center; text-shadow: 0 3px 0 #7a5c00;
}

/* --- Animaciones --- */
@keyframes cardEnter {
    from { opacity: 0; transform: translateY(18px) scale(0.9) rotate(-2deg); }
    to   { opacity: 1; transform: translateY(0) scale(1) rotate(0deg); }
}
.uno-card { animation: cardEnter 0.35s cubic-bezier(.22,1.3,.4,1); }

@keyframes playableGlow {
    0%, 100% { box-shadow: 0 12px 26px rgba(0,0,0,0.55), 0 0 0 0 rgba(255,255,255,0); }
    50%      { box-shadow: 0 12px 26px rgba(0,0,0,0.55), 0 0 18px 4px rgba(255,255,255,0.55); }
}
.uno-card-playable { animation: cardEnter 0.35s cubic-bezier(.22,1.3,.4,1), playableGlow 1.8s ease-in-out infinite; }

@keyframes turnPulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,214,10,0.55), 0 8px 20px rgba(0,0,0,0.4); transform: scale(1); }
    50%      { box-shadow: 0 0 0 16px rgba(255,214,10,0), 0 8px 20px rgba(0,0,0,0.4); transform: scale(1.012); }
}
.turn-banner-mine {
    text-align: center; font-size: 1.5rem; font-weight: 900; color: #161616;
    background: linear-gradient(135deg,#ffe066,#ffb703);
    border-radius: 16px; padding: 0.75rem; margin-bottom: 1.1rem;
    animation: turnPulse 1.7s ease-in-out infinite;
}
.turn-banner-wait {
    text-align: center; font-size: 1.05rem; font-weight: 600; color: #c9c3e6;
    background: #1c1640; border: 1px solid #332a55; border-radius: 14px;
    padding: 0.65rem; margin-bottom: 1.1rem;
}
@keyframes panelGlow {
    0%, 100% { box-shadow: 0 0 0 3px #ffd60a66, 0 10px 22px rgba(255,214,10,0.2); }
    50%      { box-shadow: 0 0 0 3px #ffd60a, 0 10px 26px rgba(255,214,10,0.45); }
}
.player-panel-turn { animation: panelGlow 1.7s ease-in-out infinite; }
@keyframes dotPulse {
    0%, 100% { box-shadow: 0 0 6px 1px var(--glow); }
    50%      { box-shadow: 0 0 14px 5px var(--glow); }
}
</style>
"""

# st.html() (si existe) inyecta HTML/CSS de forma mucho más fiable que
# st.markdown(..., unsafe_allow_html=True): no pasa el contenido por el
# parser de Markdown, así que un <style> largo no corre riesgo de romperse a
# medio camino. Streamlit lo incorporó hace relativamente poco; en versiones
# más antiguas (por ejemplo, algunas instalaciones de Anaconda) no existe
# todavía, así que caemos de vuelta a st.markdown si hace falta.
if hasattr(st, "html"):
    st.html(_CSS)
else:
    st.markdown(_CSS, unsafe_allow_html=True)

COLORS = ["red", "yellow", "green", "blue"]
COLOR_HEX = {"red": "#e63946", "yellow": "#f4c430", "green": "#2a9d8f", "blue": "#3a7bd5", "wild": "#1d1a2f"}
COLOR_EMOJI = {"red": "🟥", "yellow": "🟨", "green": "🟩", "blue": "🟦"}
COLOR_NAME_ES = {"red": "Rojo", "yellow": "Amarillo", "green": "Verde", "blue": "Azul"}
HAND_SIZE = 7


# ----------------------------------------------------------------------------
# SONIDO DE AVISO ("te toca") — generado en memoria, sin ficheros externos
# ----------------------------------------------------------------------------
@st.cache_data
def generate_turn_chime():
    """Un 'ding-dong' de dos notas ascendentes, generado como WAV puro en
    memoria (sin depender de ningún fichero de audio ni conexión a internet)."""
    sample_rate = 44100
    notes = [(880.0, 0.14), (1318.5, 0.20)]  # A5 -> E6, un aviso corto y agradable
    frames = bytearray()
    for freq, duration in notes:
        n = int(sample_rate * duration)
        for i in range(n):
            t = i / sample_rate
            fade = min(1.0, i / 300.0, (n - i) / 300.0)  # evita "clics" al empezar/acabar
            val = int(32767 * 0.28 * fade * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", val)
        frames += b"\x00\x00" * int(sample_rate * 0.02)  # pequeño silencio entre notas
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def flag_turn_chime_on_transition(is_my_turn):
    """Marca que hay que sonar el aviso solo la primera vez que detectamos
    que 'ahora te toca a ti' (no en cada auto-refresco mientras sigue
    siendo tu turno)."""
    prev = st.session_state.get("_prev_was_my_turn", False)
    if is_my_turn and not prev:
        st.session_state["_chime_flag"] = True
    st.session_state["_prev_was_my_turn"] = is_my_turn


def play_chime_if_flagged():
    """Reproduce el aviso sin mostrar ninguna barra de reproductor: en vez de
    st.audio() (que siempre dibuja sus propios controles) inyectamos un
    <audio autoplay> sin el atributo 'controls', que por definición en HTML
    no muestra nada en pantalla."""
    if st.session_state.get("_chime_flag"):
        st.session_state["_chime_flag"] = False
        b64 = base64.b64encode(generate_turn_chime()).decode("ascii")
        html = (
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/wav;base64,{b64}" type="audio/wav">'
            f"</audio>"
        )
        if hasattr(st, "html"):
            st.html(html)
        else:
            st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# CARTAS Y MAZO (funciones puras, sin estado)
# ----------------------------------------------------------------------------
def make_card(cid, color, kind, value=None):
    return {"id": cid, "color": color, "kind": kind, "value": value}


def create_deck():
    deck = []
    cid = 0
    for color in COLORS:
        deck.append(make_card(cid, color, "number", 0))
        cid += 1
        for v in range(1, 10):
            for _ in range(2):
                deck.append(make_card(cid, color, "number", v))
                cid += 1
        for kind in ("skip", "reverse", "draw2"):
            for _ in range(2):
                deck.append(make_card(cid, color, kind))
                cid += 1
    for _ in range(4):
        deck.append(make_card(cid, "wild", "wild"))
        cid += 1
    for _ in range(4):
        deck.append(make_card(cid, "wild", "wild4"))
        cid += 1
    random.shuffle(deck)
    return deck


def card_symbol(card):
    """Símbolo corto mostrado en el centro y las esquinas de la carta."""
    if card["kind"] == "number":
        return str(card["value"])
    return {"skip": "⊘", "reverse": "⇄", "draw2": "+2", "wild": "★", "wild4": "+4"}[card["kind"]]


def card_html(card, w=130, h=182, muted=False, highlight=False):
    """Carta grande estilo UNO real: óvalo blanco + índices en las esquinas.
    muted=True atenúa la carta (no jugable). highlight=True le da un brillo
    pulsante (jugable ahora mismo, para que salte a la vista)."""
    color = COLOR_HEX[card["color"]]
    symbol = card_symbol(card)
    corner_size = int(h * 0.13)
    filt = "filter:grayscale(0.75) brightness(0.55);" if muted else ""
    css_class = "uno-card" + (" uno-card-playable" if highlight else "")
    return f"""
    <div class="{css_class}" style="position:relative;width:{w}px;height:{h}px;border-radius:20px;margin:auto;
        background:linear-gradient(150deg,{color} 0%,{color}cc 100%);{filt}
        box-shadow:0 12px 26px rgba(0,0,0,0.55);border:6px solid #ffffff;overflow:hidden;
        transition:filter 0.15s ease;">
      <div style="position:absolute;top:50%;left:50%;width:{int(w*0.74)}px;height:{int(h*0.88)}px;
        transform:translate(-50%,-50%) rotate(-20deg);background:#ffffffee;border-radius:50%;
        box-shadow:0 2px 6px rgba(0,0,0,0.15) inset;"></div>
      <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
        font-size:{int(h*0.36)}px;font-weight:900;color:{color};z-index:2;font-family:'Fredoka',sans-serif;">
        {symbol}
      </div>
      <div style="position:absolute;top:8px;left:11px;font-size:{corner_size}px;font-weight:800;
        color:#ffffff;text-shadow:0 2px 3px rgba(0,0,0,0.4);">{symbol}</div>
      <div style="position:absolute;bottom:8px;right:11px;font-size:{corner_size}px;font-weight:800;
        color:#ffffff;text-shadow:0 2px 3px rgba(0,0,0,0.4);transform:rotate(180deg);">{symbol}</div>
    </div>
    """


def card_back_stack_html(count, size="normal"):
    """Pequeño montoncito de cartas boca abajo (para representar la mano de un rival)."""
    dims = {"normal": (34, 48), "small": (26, 37)}[size]
    w, h = dims
    n_shown = min(count, 3)
    if n_shown == 0:
        return "<div style='opacity:.35;font-size:0.8rem;padding-top:0.6rem;'>sin cartas</div>"
    layers = "".join(
        f"<div style='position:absolute;top:{i*4}px;left:{i*6}px;width:{w}px;height:{h}px;"
        f"border-radius:6px;background:linear-gradient(150deg,#3d2f78 0%,#241a4d 100%);"
        f"border:2px solid #8b7bd8;box-shadow:0 3px 6px rgba(0,0,0,0.45);"
        f"display:flex;align-items:center;justify-content:center;'>"
        + (f"<span style='color:#ffd60a;font-weight:900;font-size:{int(h*0.4)}px;'>🎴</span>" if i == n_shown - 1 else "")
        + "</div>"
        for i in range(n_shown)
    )
    total_w = w + (n_shown - 1) * 6
    total_h = h + (n_shown - 1) * 4
    return f"<div style='position:relative;width:{total_w}px;height:{total_h}px;margin:0.3rem auto;'>{layers}</div>"


def player_panel_html(name, emoji, count, is_turn, you=False, uno=False):
    """Panel de un jugador con una mini pila de cartas boca abajo, estilo mesa de juego."""
    if is_turn:
        border = "#ffd60a"
        bg = "linear-gradient(160deg,#2b2350 0%,#1c1640 100%)"
        css_class = "player-panel-turn"
    else:
        border = "#332a55"
        bg = "linear-gradient(160deg,#181233 0%,#120d28 100%)"
        css_class = ""
    you_tag = " <span style='color:#ffd60a;'>· tú</span>" if you else ""
    uno_tag = (
        "<div style='margin-top:0.35rem;display:inline-block;background:#f4a300;color:#161616;"
        "font-weight:900;font-size:0.75rem;padding:0.15rem 0.6rem;border-radius:999px;"
        "box-shadow:0 2px 6px rgba(0,0,0,0.4);'>📣 ¡UNO!</div>"
        if uno
        else ""
    )
    return f"""
    <div class="{css_class}" style="position:relative;background:{bg};border-radius:18px;padding:0.7rem 0.5rem;
        border:2.5px solid {border};text-align:center;min-height:128px;">
      <div style="font-weight:800;font-size:0.95rem;white-space:nowrap;overflow:hidden;
        text-overflow:ellipsis;">{emoji} {name}{you_tag}</div>
      {card_back_stack_html(count)}
      <div style="font-weight:800;color:#ffd60a;font-size:0.95rem;">{count} 🎴</div>
      {uno_tag}
    </div>
    """


def render_log(gs, n=8):
    if not gs.log:
        return
    rows = "".join(
        f"<div style='padding:0.35rem 0.2rem;border-bottom:1px solid #2a2350;font-size:0.9rem;"
        f"opacity:0.9;'>{line}</div>"
        for line in gs.log[-n:][::-1]
    )
    with st.expander("📜 Últimas jugadas", expanded=False):
        st.markdown(
            f"<div style='max-height:230px;overflow-y:auto;'>{rows}</div>",
            unsafe_allow_html=True,
        )


def is_playable(card, current_color, top):
    if card["color"] == "wild":
        return True
    if card["color"] == current_color:
        return True
    if card["kind"] == "number" and top["kind"] == "number" and card["value"] == top["value"]:
        return True
    if card["kind"] == top["kind"] and card["kind"] != "number":
        return True
    return False


def uno_wordmark():
    # OJO: el color :rojo[...] solo se interpreta si es Markdown "puro" (sin
    # envolverlo en HTML crudo). Si se mete dentro de un <h1> con
    # unsafe_allow_html=True, Streamlit lo trata como HTML literal y el
    # ":red[U]" sale escrito tal cual en vez de en color.
    st.markdown("# :red[U]:orange[N]:blue[O]")


# ----------------------------------------------------------------------------
# ESTADO DE PARTIDA
# ----------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.code = None
        self.phase = "lobby"  # lobby | playing | gameover (solo relevante en modo online)
        self.players = []
        self.discard = []
        self.draw_pile = []
        self.turn = 0
        self.direction = 1
        self.current_color = "red"
        self.log = []
        self.winner = None
        self.lock = threading.Lock()  # bloqueo propio de ESTA sala, no de toda la app


def ensure_draw_pile(gs):
    if not gs.draw_pile:
        if len(gs.discard) <= 1:
            return False
        top = gs.discard[-1]
        rest = gs.discard[:-1]
        random.shuffle(rest)
        gs.draw_pile = rest
        gs.discard = [top]
        gs.log.append("🔀 Se baraja el mazo de descarte para seguir robando.")
    return True


def draw_one(gs, player):
    if not ensure_draw_pile(gs):
        return None
    card = gs.draw_pile.pop()
    player["hand"].append(card)
    if len(player["hand"]) != 1:
        player["called_uno"] = False
    return card


def advance_turn(gs, steps=1):
    gs.turn = (gs.turn + gs.direction * steps) % len(gs.players)


def resolve_after_play(gs, card):
    n = len(gs.players)
    if card["kind"] == "reverse":
        if n > 2:
            gs.direction *= -1
            advance_turn(gs, 1)
        else:
            advance_turn(gs, 2)
    elif card["kind"] == "skip":
        advance_turn(gs, 2)
    elif card["kind"] == "draw2":
        victim = gs.players[(gs.turn + gs.direction) % n]
        for _ in range(2):
            draw_one(gs, victim)
        gs.log.append(f"➕ {victim['name']} roba 2 cartas y pierde turno.")
        advance_turn(gs, 2)
    elif card["kind"] == "wild4":
        victim = gs.players[(gs.turn + gs.direction) % n]
        for _ in range(4):
            draw_one(gs, victim)
        gs.log.append(f"➕ {victim['name']} roba 4 cartas y pierde turno.")
        advance_turn(gs, 2)
    else:
        advance_turn(gs, 1)


def play_card(gs, player, card, chosen_color=None, auto_call_uno=False):
    player["hand"].remove(card)
    gs.discard.append(card)
    gs.current_color = chosen_color if card["color"] == "wild" else card["color"]
    gs.log.append(f"🎴 {player['name']} jugó {card_symbol(card)}.")

    if len(player["hand"]) == 0:
        gs.winner = gs.players.index(player)
        gs.phase = "gameover"
        gs.log.append(f"🏆 ¡{player['name']} se ha quedado sin cartas!")
        return

    if len(player["hand"]) == 1:
        player["called_uno"] = player["is_bot"] or auto_call_uno
    else:
        player["called_uno"] = False

    resolve_after_play(gs, card)


def player_draws_and_passes(gs, player):
    card = draw_one(gs, player)
    gs.log.append(f"🃏 {player['name']} roba una carta." if card else f"⚠️ {player['name']} no pudo robar.")
    advance_turn(gs, 1)


def call_uno(player):
    if len(player["hand"]) == 1:
        player["called_uno"] = True


def catch_uno(gs, accuser, target):
    if target["called_uno"] or len(target["hand"]) != 1:
        return False
    for _ in range(2):
        draw_one(gs, target)
    target["called_uno"] = False
    gs.log.append(f"🎯 ¡{accuser['name']} pilló a {target['name']} sin cantar UNO! (+2 cartas)")
    return True


def init_game(gs, names, flags):
    gs.players = [{"name": n, "hand": [], "is_bot": b, "called_uno": False} for n, b in zip(names, flags)]
    deck = create_deck()
    for p in gs.players:
        p["hand"] = [deck.pop() for _ in range(HAND_SIZE)]

    top = deck.pop()
    while top["kind"] == "wild4":
        deck.insert(0, top)
        random.shuffle(deck)
        top = deck.pop()

    gs.discard = [top]
    gs.draw_pile = deck
    gs.direction = 1
    gs.turn = 0
    gs.winner = None
    gs.log = ["🎲 ¡Empieza la partida!"]
    gs.current_color = top["color"] if top["color"] != "wild" else random.choice(COLORS)

    if top["kind"] == "skip":
        gs.turn = 1 % len(gs.players)
    elif top["kind"] == "draw2":
        victim = gs.players[0]
        for _ in range(2):
            draw_one(gs, victim)
        gs.turn = 1 % len(gs.players)
    elif top["kind"] == "reverse" and len(gs.players) > 2:
        gs.direction = -1
        gs.turn = len(gs.players) - 1

    gs.phase = "playing"
    process_bot_turns(gs)


# ----------------------------------------------------------------------------
# BOTS
# ----------------------------------------------------------------------------
def bot_choose_card(gs, hand):
    top = gs.discard[-1]
    playable = [c for c in hand if is_playable(c, gs.current_color, top)]
    if not playable:
        return None
    non_wild = [c for c in playable if c["color"] != "wild"]
    pool = non_wild if non_wild else playable
    color_counts = Counter(c["color"] for c in hand if c["color"] != "wild")

    def score(c):
        s = color_counts.get(c["color"], 0)
        if c["kind"] != "number":
            s += 1
        return s

    pool.sort(key=score, reverse=True)
    return pool[0]


def bot_choose_color(hand):
    counts = Counter(c["color"] for c in hand if c["color"] != "wild")
    if counts:
        return counts.most_common(1)[0][0]
    return random.choice(COLORS)


BOT_MIN_DELAY = 3.0
BOT_MAX_DELAY = 5.0
BOT_CATCH_CHANCE = 0.5  # los bots no vigilan al instante: solo lo intentan cuando les toca pensar su turno


def find_vulnerable_human(gs):
    """Un humano con 1 carta que todavía no ha cantado UNO."""
    for p in gs.players:
        if not p["is_bot"] and len(p["hand"]) == 1 and not p["called_uno"]:
            return p
    return None


def bot_take_turn(gs, idx):
    time.sleep(random.uniform(BOT_MIN_DELAY, BOT_MAX_DELAY))  # el bot "piensa" antes de actuar
    player = gs.players[idx]

    # Antes de jugar, el bot puede fijarse en si algún humano se ha quedado
    # en 1 carta sin cantar UNO. Ojo: esto SOLO se comprueba aquí, tras el
    # retraso normal del turno del bot -- así el humano siempre tiene, como
    # mínimo, esos 3-5 segundos para pulsar "¡CANTO UNO!" antes de que
    # ningún bot pueda pillarlo. Nunca se pilla al instante.
    victim = find_vulnerable_human(gs)
    if victim is not None and random.random() < BOT_CATCH_CHANCE:
        catch_uno(gs, player, victim)
        return

    card = bot_choose_card(gs, player["hand"])
    if card is None:
        player_draws_and_passes(gs, player)
        return
    chosen_color = bot_choose_color(player["hand"]) if card["color"] == "wild" else None
    play_card(gs, player, card, chosen_color, auto_call_uno=True)


def process_bot_turns(gs):
    safety = 0
    while True:
        safety += 1
        if safety > 500 or gs.phase == "gameover":
            return
        player = gs.players[gs.turn]
        if not player["is_bot"]:
            return
        bot_take_turn(gs, gs.turn)


# ----------------------------------------------------------------------------
# SALAS ONLINE
# ----------------------------------------------------------------------------
@st.cache_resource
def get_rooms_store():
    return {}


@st.cache_resource
def get_store_lock():
    """Protege solo el diccionario de salas (crear sala nueva). Cada sala
    tiene además su propio gs.lock para no bloquear otras salas activas."""
    return threading.Lock()


def generate_room_code():
    rooms = get_rooms_store()
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code


# ----------------------------------------------------------------------------
# COMPONENTES DE INTERFAZ COMPARTIDOS
# ----------------------------------------------------------------------------
def render_top_area(gs):
    # Todo en una única llamada a st.markdown: abrir un <div> en una llamada y
    # cerrarlo en otra posterior es un truco frágil que depende de cómo cada
    # versión de Streamlit sanea el HTML (a veces "arregla" las etiquetas sin
    # cerrar de cada llamada por separado y rompe el anidado). Por eso el
    # indicador de color usa aquí el hex directo en vez del badge de Markdown
    # (":color-badge[...]" no se interpreta dentro de HTML crudo).
    top = gs.discard[-1]
    color_hex = COLOR_HEX[gs.current_color]
    n = len(gs.players)
    arrow = ("&nbsp;➡️" * n) if gs.direction == 1 else ("&nbsp;⬅️" * n)
    html = f"""
    <div style="background:radial-gradient(ellipse at center,#0f3d2e 0%,#0a2a20 70%,#071c16 100%);
        border-radius:28px;padding:1.6rem 1rem 1.2rem 1rem;
        box-shadow:inset 0 0 40px rgba(0,0,0,0.55),0 10px 30px rgba(0,0,0,0.5);
        border:6px solid #07130f;margin-bottom:1.2rem;text-align:center;">
      {card_html(top)}
      <div style="margin-top:0.8rem;font-size:1.15rem;font-weight:700;">
        <span style="--glow:{color_hex}aa;display:inline-block;width:1rem;height:1rem;border-radius:50%;
          background:{color_hex};vertical-align:middle;margin-right:0.5rem;
          animation:dotPulse 1.6s ease-in-out infinite;"></span>
        Color: {COLOR_NAME_ES[gs.current_color]}
      </div>
      <div style="margin-top:0.6rem;opacity:0.6;font-size:1.1rem;letter-spacing:0.15rem;">{arrow}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_opponents(gs, my_index):
    cols = st.columns(len(gs.players))
    for i, p in enumerate(gs.players):
        with cols[i]:
            is_turn = gs.turn == i
            emoji = "🤖" if p["is_bot"] else "🙋"
            uno = p["called_uno"] and len(p["hand"]) == 1
            st.markdown(
                player_panel_html(p["name"], emoji, len(p["hand"]), is_turn, you=(i == my_index), uno=uno),
                unsafe_allow_html=True,
            )
            if i != my_index and len(p["hand"]) == 1 and not p["called_uno"] and not p["is_bot"]:
                if st.button("¡Pillado!", key=f"catch_{i}", icon=":material/gavel:", help=f"{p['name']} no cantó UNO", use_container_width=True):
                    with gs.lock:
                        me = gs.players[my_index]
                        catch_uno(gs, me, p)
                    st.rerun()


def render_hand_and_actions(gs, player, my_index, on_turn_end, auto_call_uno):
    top = gs.discard[-1]
    is_my_turn = gs.turn == my_index

    # OJO: el aviso de "¡CANTO UNO!" NO debe depender de si es tu turno.
    # En cuanto juegas la penúltima carta, el turno pasa al siguiente
    # jugador en el mismo instante (resolve_after_play ya lo mueve dentro
    # de play_card), así que si este botón exigiera is_my_turn, jamás
    # llegarías a verlo: desaparecería justo cuando más lo necesitas.
    if len(player["hand"]) == 1 and not player["called_uno"]:
        if st.button("¡CANTO UNO!", type="primary", icon=":material/campaign:", use_container_width=True):
            call_uno(player)
            st.rerun()

    st.markdown("#### 🖐️ Tu mano")
    if not player["hand"]:
        st.caption("(vacía)")
    sorted_hand = sorted(player["hand"], key=lambda c: (c["color"], c["kind"] != "number", str(c.get("value", ""))))
    cols_per_row = 4
    cols = st.columns(cols_per_row)
    for i, c in enumerate(sorted_hand):
        playable = is_my_turn and is_playable(c, gs.current_color, top)
        with cols[i % cols_per_row]:
            st.markdown(card_html(c, w=92, h=128, muted=not playable, highlight=playable), unsafe_allow_html=True)
            if st.button(
                "Jugar" if playable else "—",
                key=f"card_{c['id']}",
                disabled=not playable,
                type="primary" if playable else "secondary",
                use_container_width=True,
            ):
                if c["color"] == "wild":
                    st.session_state.pending_wild = c["id"]
                else:
                    with gs.lock:
                        play_card(gs, player, c, auto_call_uno=auto_call_uno)
                        if gs.phase != "gameover":
                            process_bot_turns(gs)
                    on_turn_end(gs)
                st.rerun()

    if st.session_state.get("pending_wild"):
        card = next((c for c in player["hand"] if c["id"] == st.session_state.pending_wild), None)
        if card is None or not is_my_turn:
            # Por seguridad: si por lo que sea ya no es tu turno cuando esto
            # se procesa, cancelamos la selección en vez de arriesgarnos a
            # confirmar una jugada fuera de turno.
            st.session_state.pending_wild = None
        else:
            st.markdown("##### 🎨 Elige un color")
            cc = st.columns(4)
            for i, col in enumerate(COLORS):
                with cc[i]:
                    if st.button(f"{COLOR_EMOJI[col]} {COLOR_NAME_ES[col]}", key=f"choose_{col}", use_container_width=True):
                        st.session_state.pending_wild = None
                        with gs.lock:
                            play_card(gs, player, card, chosen_color=col, auto_call_uno=auto_call_uno)
                            if gs.phase != "gameover":
                                process_bot_turns(gs)
                        on_turn_end(gs)
                        st.rerun()
            if st.button("Cancelar", icon=":material/close:"):
                st.session_state.pending_wild = None
                st.rerun()

    if is_my_turn and not st.session_state.get("pending_wild"):
        any_playable = any(is_playable(c, gs.current_color, top) for c in player["hand"])
        if not any_playable:
            if st.button("No puedo jugar: robar carta", icon=":material/style:", use_container_width=True):
                with gs.lock:
                    player_draws_and_passes(gs, player)
                    if gs.phase != "gameover":
                        process_bot_turns(gs)
                on_turn_end(gs)
                st.rerun()
        else:
            st.caption("👆 Toca \"Jugar\" bajo una carta jugable.")


def render_gameover(gs, on_restart):
    winner = gs.players[gs.winner]
    st.markdown(
        f"<h1 style='text-align:center;'>🏆 {winner['name']} gana la partida 🏆</h1>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("##### Cartas restantes")
        rows = "".join(
            f"<div style='display:flex;justify-content:space-between;padding:0.4rem 0.2rem;"
            f"border-bottom:1px solid #2a2350;'><b>{'🏆 ' if i == 0 else ''}{p['name']}</b>"
            f"<span>{len(p['hand'])} cartas</span></div>"
            for i, p in enumerate(sorted(gs.players, key=lambda p: len(p["hand"])))
        )
        st.markdown(rows, unsafe_allow_html=True)
    on_restart(gs)


# ----------------------------------------------------------------------------
# MODO LOCAL: pasar el móvil
# ----------------------------------------------------------------------------
def run_local_app():
    if "local_screen" not in st.session_state:
        st.session_state.local_screen = "setup"

    if st.session_state.local_screen == "setup":
        uno_wordmark()
        st.caption("📱 Pasar el móvil — rellena los huecos con bots si vais menos de 4.")
        if st.button("Volver al menú", icon=":material/arrow_back:"):
            st.session_state.app_mode = None
            st.rerun()

        with st.container(border=True):
            n_humans = st.number_input("Jugadores humanos", 1, 4, 2)
            n_bots = st.number_input("Jugadores bot", 0, 3, 2)
            total = n_humans + n_bots
            if total < 2 or total > 4:
                st.warning("El total de jugadores debe estar entre 2 y 4.")
                return

            names = []
            for i in range(n_humans):
                names.append(st.text_input(f"Nombre del jugador humano {i + 1}", value=f"Jugador {i + 1}", key=f"local_name_{i}"))
            for i in range(n_bots):
                names.append(f"🤖 Bot {i + 1}")
            flags = [False] * n_humans + [True] * n_bots

            if st.button("Empezar partida", type="primary", icon=":material/play_arrow:", use_container_width=True):
                if len(set(names)) != len(names):
                    st.error("Los nombres deben ser distintos.")
                    return
                gs = GameState()
                init_game(gs, names, flags)
                st.session_state.local_gs = gs
                st.session_state.local_screen = "gameover" if gs.phase == "gameover" else "passscreen"
                st.rerun()
        return

    gs = st.session_state.local_gs

    if st.session_state.local_screen == "passscreen":
        player = gs.players[gs.turn]
        st.title("📱 Pasa el móvil")
        with st.container(border=True):
            st.markdown(f"### Turno de **{player['name']}**")
            st.write(f"Cartas en la mano: {len(player['hand'])}")
            st.markdown(card_html(gs.discard[-1], w=100, h=140), unsafe_allow_html=True)
        if gs.log:
            render_log(gs, n=6)
        if st.button(f"Soy {player['name']}, ¡listo!", type="primary", icon=":material/check_circle:", use_container_width=True):
            st.session_state.local_screen = "play"
            st.session_state["_chime_flag"] = True
            st.rerun()
        return

    if st.session_state.local_screen == "play":
        player = gs.players[gs.turn]
        uno_wordmark()
        play_chime_if_flagged()
        render_top_area(gs)
        render_opponents(gs, my_index=gs.turn)

        def on_turn_end(gs):
            st.session_state.local_screen = "gameover" if gs.phase == "gameover" else "passscreen"

        render_hand_and_actions(gs, player, my_index=gs.turn, on_turn_end=on_turn_end, auto_call_uno=True)
        return

    if st.session_state.local_screen == "gameover":
        def on_restart(gs):
            if st.button("Nueva partida", icon=":material/refresh:", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        render_gameover(gs, on_restart)
        return


# ----------------------------------------------------------------------------
# MODO ONLINE: sala con código
# ----------------------------------------------------------------------------
def render_online_landing():
    uno_wordmark()
    st.caption("🌐 Sala online — cada jugador entra desde su propio móvil.")
    if st.button("Volver al menú", icon=":material/arrow_back:"):
        st.session_state.app_mode = None
        st.rerun()

    tab_create, tab_join = st.tabs(["🆕 Crear sala", "🔑 Unirse a una sala"])

    with tab_create:
        with st.container(border=True):
            name = st.text_input("Tu nombre", key="create_name")
            if st.button("Crear sala nueva", type="primary", icon=":material/add_circle:", use_container_width=True):
                if not name.strip():
                    st.error("Ponte un nombre.")
                else:
                    with get_store_lock():
                        code = generate_room_code()
                        gs = GameState()
                        gs.code = code
                        gs.phase = "lobby"
                        gs.players = [{"name": name.strip(), "hand": [], "is_bot": False, "called_uno": False}]
                        get_rooms_store()[code] = gs
                    st.session_state.room_code = code
                    st.session_state.my_index = 0
                    st.rerun()

    with tab_join:
        with st.container(border=True):
            code = st.text_input("Código de sala", key="join_code", max_chars=4).upper()
            name = st.text_input("Tu nombre", key="join_name")
            if st.button("Unirse a la sala", type="primary", icon=":material/login:", use_container_width=True):
                rooms = get_rooms_store()
                gs = rooms.get(code)
                if gs is None:
                    st.error("No existe ninguna sala con ese código.")
                elif gs.phase != "lobby":
                    st.error("Esa partida ya ha empezado.")
                elif len(gs.players) >= 4:
                    st.error("Esa sala ya está completa (4 jugadores).")
                elif not name.strip():
                    st.error("Ponte un nombre.")
                elif name.strip() in [p["name"] for p in gs.players]:
                    st.error("Ya hay alguien con ese nombre en la sala, elige otro.")
                else:
                    with gs.lock:
                        idx = len(gs.players)
                        gs.players.append({"name": name.strip(), "hand": [], "is_bot": False, "called_uno": False})
                    st.session_state.room_code = code
                    st.session_state.my_index = idx
                    st.rerun()


def render_online_lobby(gs, my_index):
    st_autorefresh(interval=2500, key="lobby_refresh")
    uno_wordmark()
    st.markdown(f"<div class='room-code'>{gs.code}</div>", unsafe_allow_html=True)
    st.caption("Comparte este código con el resto para que se unan desde su móvil.")

    with st.container(border=True):
        st.markdown("##### Jugadores en la sala")
        rows = "".join(
            f"<div style='padding:0.5rem 0.7rem;margin-bottom:0.4rem;border-radius:10px;"
            f"background:#241a45;font-weight:700;'>{'🤖' if p['is_bot'] else '🙋'} {p['name']}"
            f"{' <span style=\"color:#ffd60a;\">· tú</span>' if i == my_index else ''}</div>"
            for i, p in enumerate(gs.players)
        )
        st.markdown(rows, unsafe_allow_html=True)

        is_host = my_index == 0
        total = len(gs.players)

        if is_host:
            c1, c2 = st.columns(2)
            if c1.button("Añadir bot", icon=":material/smart_toy:", disabled=total >= 4, use_container_width=True):
                with gs.lock:
                    n_bots = sum(1 for p in gs.players if p["is_bot"]) + 1
                    gs.players.append({"name": f"🤖 Bot {n_bots}", "hand": [], "is_bot": True, "called_uno": False})
                st.rerun()
            bot_indices = [i for i, p in enumerate(gs.players) if p["is_bot"]]
            if c2.button("Quitar último bot", icon=":material/person_remove:", disabled=not bot_indices, use_container_width=True):
                with gs.lock:
                    gs.players.pop(bot_indices[-1])
                st.rerun()

            st.divider()
            if st.button("Empezar partida", type="primary", icon=":material/play_arrow:", disabled=not (2 <= total <= 4), use_container_width=True):
                with gs.lock:
                    names = [p["name"] for p in gs.players]
                    flags = [p["is_bot"] for p in gs.players]
                    init_game(gs, names, flags)
                st.rerun()
            if not (2 <= total <= 4):
                st.info("Necesitáis entre 2 y 4 jugadores en total para empezar.", icon=":material/group:")
        else:
            st.info("Esperando a que el anfitrión empiece la partida…", icon=":material/hourglass_empty:")


def render_online_play(gs, my_index):
    with gs.lock:
        if gs.phase == "playing" and gs.players[gs.turn]["is_bot"]:
            process_bot_turns(gs)

    my_player = gs.players[my_index]
    is_my_turn = gs.turn == my_index
    flag_turn_chime_on_transition(is_my_turn)

    st.markdown(f"<h2 style='text-align:center;'>🎴 UNO — Sala {gs.code}</h2>", unsafe_allow_html=True)

    if is_my_turn:
        play_chime_if_flagged()
        st.markdown("<div class='turn-banner-mine'>🎯 ¡ES TU TURNO!</div>", unsafe_allow_html=True)
    else:
        st_autorefresh(interval=2000, key="play_refresh")
        st.markdown(
            f"<div class='turn-banner-wait'>⏳ Turno de <b>{gs.players[gs.turn]['name']}</b> — esperando…</div>",
            unsafe_allow_html=True,
        )

    render_top_area(gs)
    render_opponents(gs, my_index)

    def on_turn_end(gs):
        pass  # el estado ya vive en la sala compartida; no hace falta cambiar de pantalla

    render_hand_and_actions(gs, my_player, my_index, on_turn_end, auto_call_uno=False)

    if gs.log:
        render_log(gs, n=8)


def run_online_app():
    room_code = st.session_state.get("room_code")
    my_index = st.session_state.get("my_index")

    if room_code is None:
        render_online_landing()
        return

    gs = get_rooms_store().get(room_code)
    if gs is None or my_index is None or my_index >= len(gs.players):
        st.error("Esta sala ya no existe (puede que el servidor se haya reiniciado).")
        if st.button("Volver al inicio", icon=":material/arrow_back:"):
            st.session_state.room_code = None
            st.session_state.my_index = None
            st.rerun()
        return

    if gs.phase == "lobby":
        render_online_lobby(gs, my_index)
    elif gs.phase == "playing":
        render_online_play(gs, my_index)
    elif gs.phase == "gameover":
        def on_restart(gs):
            is_host = my_index == 0
            if is_host and st.button("Jugar otra partida en esta sala", icon=":material/refresh:", use_container_width=True):
                with gs.lock:
                    gs.phase = "lobby"
                st.rerun()
            elif not is_host:
                st.info("Esperando a que el anfitrión inicie otra partida…", icon=":material/hourglass_empty:")
                st_autorefresh(interval=3000, key="gameover_refresh")
            if st.button("Salir de la sala", icon=":material/logout:"):
                st.session_state.room_code = None
                st.session_state.my_index = None
                st.rerun()

        render_gameover(gs, on_restart)


# ----------------------------------------------------------------------------
# ROUTER PRINCIPAL
# ----------------------------------------------------------------------------
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    uno_wordmark()
    st.caption("Elige cómo vais a jugar.")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### 📱 Mismo móvil")
            st.write("Os vais pasando un único teléfono por turnos.")
            if st.button("Jugar pasando el móvil", type="primary", icon=":material/smartphone:", use_container_width=True):
                st.session_state.app_mode = "local"
                st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("#### 🌐 Sala online")
            st.write("Cada uno desde su propio móvil, con un código de sala.")
            if st.button("Crear o unirme a una sala", icon=":material/group:", use_container_width=True):
                st.session_state.app_mode = "online"
                st.rerun()
elif st.session_state.app_mode == "local":
    run_local_app()
elif st.session_state.app_mode == "online":
    run_online_app()
