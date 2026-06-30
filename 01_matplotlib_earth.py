#!/usr/bin/env python3
"""
01 - Rotating Earth with ECI & ECEF frames  (Matplotlib edition)
================================================================

The simplest of the four iterations. Everything is drawn with pure
Matplotlib 3-D primitives, so the only hard dependencies are NumPy and
Matplotlib (Pillow is used to read a texture / write the GIF).

What is shown
-------------
* A unit Earth rendered as a shaded, textured sphere.
* The **ECI** frame  (Earth-Centred Inertial) - fixed in space:
      Z  -> spin axis, through the North Pole          (drawn RED)
      X  -> initially through the prime meridian        (orange)
      Y  -> completes the right-handed triad            (lime)
* The **ECEF** frame (Earth-Centred Earth-Fixed) - rotates with the
  crust.  Only X and Y are drawn (its Z is identical to the ECI Z):
      X_ECEF (cyan)  and  Y_ECEF (magenta)
* A *stationary* Sun.  The day/night terminator is computed from a fixed
  inertial Sun direction, so as the globe turns the lit hemisphere stays
  put in space - exactly what you would see from deep space.

The clip runs for exactly five sidereal rotations.

Run
---
    python 01_matplotlib_earth.py                # save earth_matplotlib.gif
    python 01_matplotlib_earth.py --show         # also pop up a window
    python 01_matplotlib_earth.py --rotations 3  # fewer turns / faster test
"""
from __future__ import annotations

import argparse
import io
import urllib.request

import numpy as np
import matplotlib

import matplotlib.pyplot as plt
from matplotlib import animation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers '3d')

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
N_LON, N_LAT = 120, 60          # sphere mesh resolution (vertices)
FRAMES_PER_ROT = 60             # animation frames per Earth rotation
AMBIENT = 0.12                  # how much the night side still glows
# Fixed Sun direction in the ECI frame (does NOT move during the clip).
SUN_DIR = np.array([1.0, -0.35, 0.25])
SUN_DIR /= np.linalg.norm(SUN_DIR)

# A reliable, CORS-friendly 2k Blue-Marble style texture (jsDelivr mirror of
# the three.js example assets).  If the download fails we fall back to a
# procedurally generated continents map so the script is always self-contained.
TEXTURE_URL = (
    "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/"
    "examples/textures/planets/earth_atmos_2048.jpg"
)


# --------------------------------------------------------------------------- #
#  Texture handling
# --------------------------------------------------------------------------- #
def _procedural_earth(width: int = 1024, height: int = 512) -> np.ndarray:
    """A cheap but recognisable ocean/land/ice map used as an offline fallback."""
    lon = np.linspace(-np.pi, np.pi, width)
    lat = np.linspace(np.pi / 2, -np.pi / 2, height)
    LON, LAT = np.meshgrid(lon, lat)

    # Sum of a few rotated sinusoids -> blobby "continents".
    land = (
        np.sin(2.1 * LON + 1.2) * np.cos(1.7 * LAT)
        + 0.6 * np.sin(3.7 * LON - 2.0) * np.cos(2.9 * LAT + 0.5)
        + 0.4 * np.sin(5.3 * LON + 0.7) * np.cos(4.1 * LAT)
    )
    img = np.empty((height, width, 3), dtype=float)
    ocean = np.array([0.06, 0.18, 0.38])
    green = np.array([0.16, 0.42, 0.18])
    sand = np.array([0.45, 0.40, 0.24])

    is_land = land > 0.25
    img[:] = ocean
    img[is_land] = green
    img[land > 0.75] = sand

    # Polar ice caps.
    ice = np.abs(LAT) > np.radians(72)
    img[ice] = np.array([0.92, 0.94, 0.97])
    return img


def load_texture() -> np.ndarray:
    """Return an (H, W, 3) float texture in [0, 1]; download or fall back."""
    try:
        from PIL import Image  # local import keeps Pillow optional

        with urllib.request.urlopen(TEXTURE_URL, timeout=15) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.asarray(img, dtype=float) / 255.0
        print(f"[texture] downloaded {img.size[0]}x{img.size[1]} Blue Marble")
        return arr
    except Exception as exc:  # noqa: BLE001 - any failure -> procedural map
        print(f"[texture] download failed ({exc}); using procedural Earth")
        return _procedural_earth()


# --------------------------------------------------------------------------- #
#  Geometry
# --------------------------------------------------------------------------- #
def build_sphere(texture: np.ndarray):
    """Body-fixed (ECEF at t=0) vertices + per-vertex RGB sampled from texture.

    Convention:  lon = 0  -> +X (prime meridian),   lat = +90 -> +Z (N pole).
    """
    lon = np.linspace(-np.pi, np.pi, N_LON)
    lat = np.linspace(np.pi / 2, -np.pi / 2, N_LAT)
    LON, LAT = np.meshgrid(lon, lat)

    x = np.cos(LAT) * np.cos(LON)
    y = np.cos(LAT) * np.sin(LON)
    z = np.sin(LAT)
    verts = np.stack([x, y, z], axis=-1)          # (N_LAT, N_LON, 3)

    # Sample the texture at every vertex.
    h, w, _ = texture.shape
    col = ((LON + np.pi) / (2 * np.pi) * (w - 1)).astype(int)
    row = ((np.pi / 2 - LAT) / np.pi * (h - 1)).astype(int)
    rgb = texture[row, col]                        # (N_LAT, N_LON, 3)
    return verts, rgb


def rot_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


# --------------------------------------------------------------------------- #
#  Drawing helpers
# --------------------------------------------------------------------------- #
def draw_axis(ax, vec, color, label, lw=2.4):
    """Draw an arrow from the origin plus a text label at the tip."""
    ax.quiver(0, 0, 0, *vec, color=color, linewidth=lw,
              arrow_length_ratio=0.12)
    ax.text(*(vec * 1.12), label, color=color, fontsize=10,
            fontweight="bold", ha="center", va="center")


# --------------------------------------------------------------------------- #
#  Main animation
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotations", type=float, default=5.0)
    parser.add_argument("--out", default="earth_matplotlib.gif")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    if not args.show:
        matplotlib.use("Agg")  # headless rendering

    texture = load_texture()
    verts, rgb = build_sphere(texture)
    flat = verts.reshape(-1, 3)                    # (Nv, 3) for fast rotation

    n_frames = int(round(args.rotations * FRAMES_PER_ROT))
    axis_len = 1.7

    fig = plt.figure(figsize=(8, 8), facecolor="black")
    ax = fig.add_subplot(111, projection="3d", facecolor="black")

    def render(frame: int):
        ax.clear()
        ax.set_axis_off()
        ax.set_box_aspect((1, 1, 1))
        lim = 1.9
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.view_init(elev=22, azim=35)

        theta = 2 * np.pi * args.rotations * frame / n_frames
        R = rot_z(theta)

        # Rotate vertices into ECI; normals == positions on a unit sphere.
        eci = (flat @ R.T).reshape(N_LAT, N_LON, 3)
        normals = eci                                  # already unit length
        shade = AMBIENT + (1 - AMBIENT) * np.clip(normals @ SUN_DIR, 0, 1)
        face_rgb = np.clip(rgb * shade[..., None], 0, 1)

        # plot_surface wants per-face colours -> sample top-left corner.
        facecolors = np.empty((N_LAT - 1, N_LON - 1, 4))
        facecolors[..., :3] = face_rgb[:-1, :-1]
        facecolors[..., 3] = 1.0

        ax.plot_surface(
            eci[..., 0], eci[..., 1], eci[..., 2],
            rstride=1, cstride=1, facecolors=facecolors,
            linewidth=0, antialiased=False, shade=False,
        )

        # --- ECI frame (fixed) --------------------------------------------- #
        draw_axis(ax, np.array([axis_len, 0, 0]), "#ff9500", "X_ECI")
        draw_axis(ax, np.array([0, axis_len, 0]), "#7CFC00", "Y_ECI")
        draw_axis(ax, np.array([0, 0, axis_len]), "#ff2d2d", "Z_ECI (spin)")

        # --- ECEF frame (rotates) ------------------------------------------ #
        xe = R @ np.array([axis_len, 0, 0])
        ye = R @ np.array([0, axis_len, 0])
        draw_axis(ax, xe, "#00e5ff", "X_ECEF")
        draw_axis(ax, ye, "#ff4dd2", "Y_ECEF")

        # --- Sun direction indicator --------------------------------------- #
        sun_tip = SUN_DIR * 1.85
        ax.plot([sun_tip[0]], [sun_tip[1]], [sun_tip[2]],
                marker="o", color="#ffe066", markersize=12)
        ax.text(*(SUN_DIR * 2.05), "Sun", color="#ffe066",
                fontsize=10, ha="center")

        rot_done = args.rotations * frame / n_frames
        ax.set_title(
            f"Rotating Earth — ECI (fixed) vs ECEF (rotating)\n"
            f"rotation {rot_done:4.2f} / {args.rotations:.0f}",
            color="white", fontsize=11,
        )
        return []

    print(f"[render] {n_frames} frames ...")
    anim = animation.FuncAnimation(
        fig, render, frames=n_frames, interval=1000 / args.fps, blit=False
    )

    try:
        writer = animation.PillowWriter(fps=args.fps)
        anim.save(args.out, writer=writer, dpi=90)
        print(f"[done] wrote {args.out}")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not save GIF ({exc})")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
