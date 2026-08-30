# 🎴 UNO

UNO para 2-4 jugadores, con reglas completas y un diseño cuidado, en dos modos:

- **📱 Mismo móvil** — os vais pasando un único teléfono por turnos.
- **🌐 Sala online** — cada uno desde su propio móvil, con un código de sala
  de 4 letras (misma arquitectura que `rummikub`: estado compartido en
  memoria + auto-refresco).

Rellena huecos con bots si vais menos de 4.

## Diseño visual (v2)

Esta versión usa a fondo funciones **nativas** de Streamlit para verse
profesional sin depender de trucos frágiles de JavaScript que podrían
romperse en un redeploy:

- **Badges de color reales** (`:red-badge[...]`, `:blue-badge[...]`, etc.) en
  cada carta de tu mano — no son emojis de colores, es el propio motor de
  Streamlit pintando el fondo del badge con el color exacto de la carta.
- **Iconos Material Design** (`:material/block:`, `:material/swap_horiz:`,
  `:material/palette:`...) en vez de emojis genéricos para Salta, Reversa y
  Comodín.
- **Carta grande estilo UNO real** para el mazo de descarte: óvalo blanco de
  fondo, símbolo grande en el centro e índices en las esquinas, como una
  carta física.
- Fondo tipo "mesa de fieltro" para la zona de juego, contenedores con borde
  para paneles (lobby, resumen final), y alertas nativas con icono para el
  turno ("¡Es tu turno!" / "Turno de X — esperando…").
- Tipografía **Fredoka** (Google Fonts) en toda la app.

### Por qué no usé cartas 100% "de verdad" arrastrables

Para lograr cartas completamente personalizadas (fondo de color exacto por
carta, animaciones de arrastre, flip 3D) habría que salir de los widgets
nativos de Streamlit y construir un componente HTML/JS con un canal de
comunicación de vuelta a Python — eso normalmente se hace con
`window.parent.postMessage` o un componente bidireccional completo. Es
factible, pero es un mecanismo bastante fràgil que no he podido probar en un
navegador real desde aquí, y en un juego que quieres que funcione bien en
producción prefiero no arriesgar esa pieza. Lo que hay ahora (badges de color
nativos + iconos + carta grande en HTML puro para la parte no interactiva)
da un resultado muy cuidado sin ese riesgo. Si más adelante quieres dar el
salto al componente 100% custom, se puede hacer como siguiente iteración.

## Reglas implementadas

- Mazo completo de 108 cartas (4 colores x 25 + 4 comodín + 4 comodín+4).
- Emparejar por color, número o símbolo.
- **Salta**, **Reversa** (actúa como Salta en partidas de 2), **+2**,
  **Comodín** (elige color) y **Comodín +4**.
- Si no tienes ninguna carta jugable, robas una y pasas turno.
- El mazo de descarte se reutiliza automáticamente si se agota el mazo de
  robo.
- **Cantar UNO**: al quedarte con 1 carta debes pulsar "¡CANTO UNO!". En la
  sala online, si no lo haces a tiempo cualquier otro jugador puede pulsar
  "¡Pillado!" y te hace robar 2 cartas. En modo "mismo móvil" se canta
  automáticamente.
- Gana quien se queda sin cartas primero.

## Probarlo en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Desplegarlo en Streamlit Community Cloud

Mismo proceso que con tus otras apps (`vinted-analyzer`, `rummikub`):

1. Sube `app.py`, `requirements.txt` y este `README.md` a un repo de GitHub
   (p. ej. `uno-online`).
2. [share.streamlit.io](https://share.streamlit.io) → conecta el repo →
   archivo principal `app.py` → deploy.
3. Compartes la URL; en modo sala online, uno crea la sala y pasa el código
   de 4 letras al resto.

**Nota:** igual que en `rummikub`, el estado de las salas online vive en
memoria mientras el proceso esté vivo — si Streamlit Cloud reinicia la app
(redeploy o inactividad prolongada), las salas activas se pierden. Para
partidas puntuales con amigos no es un problema.
