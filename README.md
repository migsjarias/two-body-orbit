# Rotating Earth — ECI vs ECEF reference frames

Four animations of a rotating Earth, built in **increasing levels of
sophistication** with progressively more capable rendering libraries. Each one
shows the same piece of orbital mechanics — the relationship between an inertial
frame and an Earth-fixed frame — so you can compare what each tool brings to the
table.

| # | File | Library | Output |
|---|------|---------|--------|
| 1 | [`01_matplotlib_earth.py`](01_matplotlib_earth.py) | Matplotlib | animated GIF / live window |
| 2 | [`02_vpython_earth.py`](02_vpython_earth.py) | VPython | live, mouse-orbitable browser scene |
| 3 | [`03_pyvista_earth.py`](03_pyvista_earth.py) | PyVista (VTK) | interactive window / exported GIF |
| 4 | [`04_webgl_earth.html`](04_webgl_earth.html) | WebGL (three.js) | real-time, photoreal browser app |

---

## The physics being visualised

Two coordinate frames share the same origin at the Earth's centre.

### ECI — Earth-Centred Inertial (fixed in space)

A non-rotating frame. It does **not** turn with the Earth, so Newton's laws hold
without fictitious forces — this is the frame you integrate orbits in.

* **Z** — the spin axis, through the **North Pole**. Drawn **red** in every
  animation, as requested.
* **X** — initially points through the **prime meridian** (0° longitude, 0°
  latitude) at *t = 0*.
* **Y** — completes the right-handed triad (`Y = Z × X`).

### ECEF — Earth-Centred, Earth-Fixed (rotates with the crust)

Bolted to the planet, so a point on the ground keeps constant coordinates. This
is the frame of latitude/longitude, GPS and ground stations.

* Its **Z** is identical to the ECI Z (same spin axis), so only **X** and **Y**
  are drawn to keep the picture clean.
* At *t = 0* it coincides with ECI. After that it rotates about Z by the Earth
  rotation angle θ(t) = ω·t (eastward / right-handed):

  ```
  X_ECEF(t) = [ cos θ,  sin θ, 0 ]   (in ECI components)
  Y_ECEF(t) = [-sin θ,  cos θ, 0 ]
  ```

### Stationary Sun

For this experiment the Sun is held **fixed in inertial space** (a constant
direction in the ECI frame). The lit hemisphere and the day/night terminator
therefore stay put while the globe turns underneath them — exactly the view you
would get watching Earth from a fixed point in deep space. Lighting is pure
Lambertian diffuse (plus a specular ocean glint and city lights in the WebGL
version).

### Run length

Every animation runs for **exactly five full rotations** of the Earth and then
holds / loops.

> **Note on time scale.** A real sidereal day is 23 h 56 m, but these clips are
> not real-time — each "rotation" is simply 2π of spin, played back at a speed
> chosen for watchability. The *kinematics* (which frame moves, and how) are
> faithful; only the wall-clock rate is compressed.

---

## 1 · Matplotlib

The minimal, dependency-light version. Pure Matplotlib 3-D: a shaded textured
sphere plus `quiver` arrows for the frames. Good for a quick look or for
dropping a GIF into a slide deck.

```bash
pip install numpy matplotlib pillow
python 01_matplotlib_earth.py                 # writes earth_matplotlib.gif
python 01_matplotlib_earth.py --show          # also open an interactive window
python 01_matplotlib_earth.py --rotations 2   # shorter / faster
```

It tries to download a 2K Blue-Marble texture and **falls back to a procedurally
generated continents map** if there's no network, so it always runs offline.

## 2 · VPython

One step up: a real-time 3-D scene you can orbit with the mouse, using VPython's
built-in Earth texture and lighting model. Opens automatically in your browser.

```bash
pip install vpython
python 02_vpython_earth.py
```

A single stationary `distant_light` plays the Sun; the textured globe spins
about Z while the ECEF arrows are re-pointed each frame.

## 3 · PyVista

GPU-quality rendering via VTK: true texture mapping, anti-aliasing, a proper
scene light for a crisp terminator, and a clean path to either an interactive
window **or** an exported movie.

```bash
pip install pyvista
python 03_pyvista_earth.py            # interactive window if a display exists
python 03_pyvista_earth.py --gif      # force a headless GIF export
```

Uses PyVista's bundled globe + texture when available, otherwise builds a
UV-sphere with a procedural texture. Headless export needs an off-screen GL
stack (e.g. `pyvista.start_xvfb()` on Linux, called automatically).

## 4 · WebGL — the showpiece

A self-contained, real-time WebGL app built on **three.js**, with a custom GLSL
shader. Just open the file in any modern browser — no build step, no server:

```bash
# macOS
open 04_webgl_earth.html
# Linux
xdg-open 04_webgl_earth.html
# …or simply double-click it.
```

What makes this one special:

* **Custom Earth shader** combining a day map, **night-side city lights**,
  a glossy **ocean sun-glint**, normal-mapped surface relief, and **lit, drifting
  clouds** — with a soft, physically plausible day/night terminator.
* **Volumetric-style atmosphere** — an additive Fresnel rim shell that brightens
  on the sunlit limb.
* **Procedural starfield**, a glowing **Sun sprite**, and ACES filmic tone
  mapping.
* **Interactive HUD**: live rotation counter / progress bar, legend, play-pause,
  replay, a speed slider, and an axes toggle. Drag to orbit, scroll to zoom.

Textures stream from the jsDelivr CDN at runtime; if a texture can't be reached
the shader falls back to solid-colour placeholders so the scene still renders.

---

## Frame colour key (consistent across all four)

| Axis | Colour | Meaning |
|------|--------|---------|
| `Z_ECI`  | **red**     | spin axis, through the North Pole |
| `X_ECI`  | orange      | prime meridian at *t = 0* |
| `Y_ECI`  | green       | completes the inertial triad |
| `X_ECEF` | cyan        | rotates with the crust |
| `Y_ECEF` | magenta     | rotates with the crust |
| Sun      | yellow      | stationary lighting direction |

## Tweakable knobs

All four scripts expose the same constants near the top:

* `ROTATIONS` / `--rotations` — number of turns (default **5**).
* `SUN_DIR` — the fixed inertial Sun direction.
* `PRIME_MERIDIAN_OFFSET` (WebGL) — aligns 0° longitude to +X at *t = 0* for a
  given texture.

## Verification

The Matplotlib animation and the WebGL app were both rendered and inspected
during development (the WebGL shaders were confirmed to compile and run in a
headless Chromium with the animation loop advancing and zero GL errors). The
PyVista and VPython programs were validated against their library APIs.
