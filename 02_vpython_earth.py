#!/usr/bin/env python3
"""
02 - Rotating Earth with ECI & ECEF frames  (VPython edition)
=============================================================

Second iteration.  VPython gives us a real-time, mouse-orbitable 3-D scene
in the browser (or the Jupyter notebook) for almost no code, plus a built-in
Earth texture and a proper lighting model.

What is shown
-------------
* A texture-mapped Earth lit by a single, *stationary* distant light that
  plays the role of the Sun - the terminator therefore stays fixed in
  inertial space while the globe spins beneath it.
* ECI frame (fixed):   X_ECI (orange), Y_ECI (lime), Z_ECI / spin axis (RED).
* ECEF frame (spins):  X_ECEF (cyan), Y_ECEF (magenta).  Its Z coincides
  with the ECI Z, so only X and Y are drawn.
* The whole thing runs for exactly five rotations and then holds.

Run
---
    pip install vpython
    python 02_vpython_earth.py

VPython opens a tab at http://localhost:<port>/ automatically.  Drag to
orbit, scroll to zoom.
"""
from __future__ import annotations

import numpy as np
from vpython import (
    sphere, arrow, label, distant_light, vector, color, rate, scene,
    textures,
)

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
ROTATIONS = 5.0
STEPS_PER_ROT = 360          # angular resolution of the animation
FPS = 60                     # playback rate
AXIS_LEN = 1.8
R_EARTH = 1.0

# Stationary Sun direction in the ECI frame (unit vector).
_sun = np.array([1.0, -0.35, 0.25])
_sun /= np.linalg.norm(_sun)
SUN_DIR = vector(*_sun)


def rot_z(v: vector, theta: float) -> vector:
    """Rotate a VPython vector about the +Z (ECI spin) axis."""
    c, s = np.cos(theta), np.sin(theta)
    return vector(c * v.x - s * v.y, s * v.x + c * v.y, v.z)


def main() -> None:
    # --- scene / camera ---------------------------------------------------- #
    scene.title = ("<b>Rotating Earth — ECI (fixed) vs ECEF (rotating)</b>"
                   "<br>Z is the spin axis (North Pole). Drag to orbit, "
                   "scroll to zoom.\n")
    scene.background = color.black
    scene.up = vector(0, 0, 1)          # make +Z the world "up" (North Pole)
    scene.forward = vector(-0.6, -1, -0.45)
    scene.ambient = color.gray(0.22)    # faint glow on the night side
    scene.range = 2.4

    # --- stationary Sun lighting ------------------------------------------ #
    scene.lights = []                   # drop the two default headlights
    distant_light(direction=SUN_DIR, color=color.white)
    # A small yellow marker showing where the Sun is.
    label(pos=SUN_DIR * 2.1, text="Sun", color=color.yellow,
          box=False, opacity=0, height=14)

    # --- Earth ------------------------------------------------------------- #
    # VPython's built-in earth texture wraps its poles along the local +y
    # axis, so spin the body once about +x to bring the North Pole onto +Z.
    earth = sphere(
        pos=vector(0, 0, 0), radius=R_EARTH, texture=textures.earth,
        shininess=0.05,
    )
    earth.rotate(angle=np.pi / 2, axis=vector(1, 0, 0), origin=vector(0, 0, 0))

    # --- ECI frame (fixed) ------------------------------------------------- #
    def make_axis(direction, col, text):
        arr = arrow(pos=vector(0, 0, 0), axis=direction * AXIS_LEN,
                    color=col, shaftwidth=0.025)
        lab = label(pos=direction * AXIS_LEN * 1.08, text=text, color=col,
                    box=False, opacity=0, height=13)
        return arr, lab

    make_axis(vector(1, 0, 0), color.orange, "X_ECI")
    make_axis(vector(0, 1, 0), vector(0.5, 1, 0), "Y_ECI")
    make_axis(vector(0, 0, 1), color.red, "Z_ECI (spin)")

    # --- ECEF frame (rotating) -------------------------------------------- #
    ecef_x = arrow(pos=vector(0, 0, 0), axis=vector(AXIS_LEN, 0, 0),
                   color=color.cyan, shaftwidth=0.03)
    ecef_y = arrow(pos=vector(0, 0, 0), axis=vector(0, AXIS_LEN, 0),
                   color=color.magenta, shaftwidth=0.03)
    lab_x = label(text="X_ECEF", color=color.cyan, box=False, opacity=0,
                  height=13)
    lab_y = label(text="Y_ECEF", color=color.magenta, box=False, opacity=0,
                  height=13)

    counter = label(pos=vector(0, 0, -2.2), text="", color=color.white,
                    box=False, opacity=0, height=15)

    # --- animation loop ---------------------------------------------------- #
    total_steps = int(ROTATIONS * STEPS_PER_ROT)
    dtheta = 2 * np.pi / STEPS_PER_ROT
    theta = 0.0

    for step in range(total_steps + 1):
        rate(FPS)

        # Spin the textured globe about the ECI Z axis.
        earth.rotate(angle=dtheta, axis=vector(0, 0, 1),
                     origin=vector(0, 0, 0))

        # Re-point the ECEF axes.
        xe = rot_z(vector(1, 0, 0), theta) * AXIS_LEN
        ye = rot_z(vector(0, 1, 0), theta) * AXIS_LEN
        ecef_x.axis, ecef_y.axis = xe, ye
        lab_x.pos, lab_y.pos = xe * 1.08, ye * 1.08

        counter.text = f"rotation {theta / (2*np.pi):4.2f} / {ROTATIONS:.0f}"
        theta += dtheta

    counter.text = f"done — {ROTATIONS:.0f} rotations complete"


if __name__ == "__main__":
    main()
