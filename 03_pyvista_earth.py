#!/usr/bin/env python3
"""
03 - Rotating Earth with ECI & ECEF frames  (PyVista edition)
=============================================================

Third iteration.  PyVista wraps VTK, so we get GPU-quality rendering:
true texture mapping, physically-based-ish lighting, anti-aliasing and an
easy path to either an interactive window *or* an exported movie/GIF.

What is shown
-------------
* A texture-mapped Earth (PyVista's bundled globe, or a downloaded Blue
  Marble, or a procedural fallback - whichever is available).
* A single stationary "Sun" light fixed in inertial space, giving a crisp
  day/night terminator that does not move as the Earth turns.
* ECI frame (fixed):   X_ECI (orange), Y_ECI (lime), Z_ECI / spin axis (RED).
* ECEF frame (spins):  X_ECEF (cyan), Y_ECEF (magenta).
* Exactly five rotations.

Run
---
    pip install pyvista
    python 03_pyvista_earth.py            # interactive window if a display
                                          # exists, else writes a GIF
    python 03_pyvista_earth.py --gif      # force GIF export (headless)
    python 03_pyvista_earth.py --rotations 3
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pyvista as pv

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
STEPS_PER_ROT = 180
AXIS_LEN = 1.8
R = 1.0
_sun = np.array([1.0, -0.35, 0.25])
SUN_DIR = _sun / np.linalg.norm(_sun)


# --------------------------------------------------------------------------- #
#  Earth mesh + texture
# --------------------------------------------------------------------------- #
def make_earth():
    """Return (mesh, texture). Tries PyVista's globe, then falls back."""
    try:
        from pyvista import examples
        globe = examples.load_globe()              # lat/lon sphere, z = poles
        tex = examples.load_globe_texture()
        globe.points /= np.abs(globe.points).max() / R   # normalise radius
        print("[earth] using PyVista bundled globe")
        return globe, tex
    except Exception as exc:                       # noqa: BLE001
        print(f"[earth] bundled globe unavailable ({exc}); building sphere")

    # A plain UV sphere with z as the polar axis and proper texture coords.
    sphere = pv.Sphere(
        radius=R, theta_resolution=120, phi_resolution=60,
        start_theta=270.001, end_theta=270,
    )
    sphere.active_texture_coordinates = _spherical_uv(sphere.points)
    return sphere, _fallback_texture()


def _spherical_uv(points: np.ndarray) -> np.ndarray:
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    u = 0.5 + np.arctan2(y, x) / (2 * np.pi)
    v = 0.5 - np.arcsin(np.clip(z / R, -1, 1)) / np.pi
    return np.column_stack([u, v])


def _fallback_texture() -> pv.Texture:
    """Procedural ocean/land/ice texture so the script is self-contained."""
    h, w = 512, 1024
    lon = np.linspace(-np.pi, np.pi, w)
    lat = np.linspace(np.pi / 2, -np.pi / 2, h)
    LON, LAT = np.meshgrid(lon, lat)
    land = (np.sin(2.1 * LON + 1.2) * np.cos(1.7 * LAT)
            + 0.6 * np.sin(3.7 * LON - 2.0) * np.cos(2.9 * LAT + 0.5))
    img = np.empty((h, w, 3), np.uint8)
    img[:] = (16, 46, 97)
    img[land > 0.25] = (41, 107, 46)
    img[np.abs(LAT) > np.radians(72)] = (235, 240, 248)
    return pv.Texture(img)


# --------------------------------------------------------------------------- #
#  Axis helper
# --------------------------------------------------------------------------- #
def add_axis(plotter, direction, length, color, label):
    direction = np.asarray(direction, float)
    tip = direction * length
    arrow = pv.Arrow(start=(0, 0, 0), direction=direction, scale=length,
                     tip_length=0.12, tip_radius=0.03, shaft_radius=0.012)
    actor = plotter.add_mesh(arrow, color=color, ambient=0.4, diffuse=0.6,
                             specular=0.0)
    plotter.add_point_labels(
        [tip * 1.08], [label], text_color=color, font_size=14,
        shape=None, show_points=False, always_visible=True,
    )
    return actor


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotations", type=float, default=5.0)
    parser.add_argument("--gif", action="store_true",
                        help="force headless GIF export")
    parser.add_argument("--out", default="earth_pyvista.gif")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    headless = args.gif or not (os.environ.get("DISPLAY") or os.name == "nt")
    if headless:
        pv.OFF_SCREEN = True
        try:
            pv.start_xvfb()
        except Exception:                          # noqa: BLE001
            pass

    earth, texture = make_earth()

    plotter = pv.Plotter(window_size=(900, 900), lighting="none",
                         off_screen=headless)
    plotter.set_background("black")

    # --- stationary Sun ---------------------------------------------------- #
    sun = pv.Light(position=tuple(SUN_DIR * 100), focal_point=(0, 0, 0),
                   color="white", light_type="scene light")
    sun.intensity = 1.15
    plotter.add_light(sun)

    earth_actor = plotter.add_mesh(
        earth, texture=texture, smooth_shading=True,
        ambient=0.15, diffuse=1.0, specular=0.08,
    )
    plotter.add_point_labels([SUN_DIR * 2.1], ["Sun"], text_color="yellow",
                             font_size=14, shape=None, show_points=False,
                             always_visible=True)

    # --- ECI frame (fixed) ------------------------------------------------- #
    add_axis(plotter, (1, 0, 0), AXIS_LEN, "orange", "X_ECI")
    add_axis(plotter, (0, 1, 0), AXIS_LEN, "#7CFC00", "Y_ECI")
    add_axis(plotter, (0, 0, 1), AXIS_LEN, "red", "Z_ECI (spin)")

    # --- ECEF frame (rotating) -------------------------------------------- #
    ex = pv.Arrow(start=(0, 0, 0), direction=(1, 0, 0), scale=AXIS_LEN,
                  tip_length=0.12, tip_radius=0.035, shaft_radius=0.015)
    ey = pv.Arrow(start=(0, 0, 0), direction=(0, 1, 0), scale=AXIS_LEN,
                  tip_length=0.12, tip_radius=0.035, shaft_radius=0.015)
    ecef_x = plotter.add_mesh(ex, color="cyan", ambient=0.5)
    ecef_y = plotter.add_mesh(ey, color="magenta", ambient=0.5)

    plotter.camera_position = [(4.2, -4.2, 2.6), (0, 0, 0), (0, 0, 1)]

    n_steps = int(args.rotations * STEPS_PER_ROT)
    dtheta = 360.0 / STEPS_PER_ROT     # degrees per step

    def spin(actor):
        # Rotate an actor about the world Z axis through its origin (0,0,0).
        # rotate_z() composes with the actor's current orientation each call.
        actor.rotate_z(dtheta)

    if headless:
        plotter.open_gif(args.out, fps=args.fps)
        print(f"[render] {n_steps} frames -> {args.out}")
        for _ in range(n_steps):
            spin(earth_actor); spin(ecef_x); spin(ecef_y)
            plotter.write_frame()
        plotter.close()
        print(f"[done] wrote {args.out}")
    else:
        plotter.show(interactive_update=True, auto_close=False)
        for _ in range(n_steps):
            spin(earth_actor); spin(ecef_x); spin(ecef_y)
            plotter.update()
        plotter.show()


if __name__ == "__main__":
    main()
