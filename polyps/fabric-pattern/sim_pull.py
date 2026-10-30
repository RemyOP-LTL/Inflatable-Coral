"""What happens when the string is pulled: a step-by-step simulation.

Run:  python3 sim_pull.py --out designs                (about 1-3 minutes)
Makes: <name>-pull.png (snapshots and a force curve) and <name>-pull.csv (the numbers).
(It stops early if the fingers can't fold any further.)
Options: --hitch 1.0      where the five strings meet, this far below the centre point (in)
         --pull-max 10    how far the hitch is pulled down in total (in)
         --steps 10       how many pulls between 0 and --pull-max
         --name design    start of the file names (default: the design's name)
The pattern settings are the same as make_pattern.py (use POLYP="FINGER_LENGTH=7,..." to change them).

How it works. It starts from the inflated polyp (sim_polyp.py). Each finger has a cord, anchored
at the fingertip, running along the inner seam to the centre point, then straight down to the
hitch. The cord can't stretch. The hitch is pulled down a little at a time. Each time, the
fabric settles into its new shape, so you see the fingers fold in as the cord shortens.

Assumptions: the air pressure stays constant (the blower keeps up); there is no friction in the
tunnel; the tube is open (a thin wall), so the top of the polyp can be pulled down into it; the
cord is just taut when the polyp is fully inflated. Not simulated: fingers pressing on each other
(it holds one finger between mirror planes, so neighbours can't cross), gravity, fabric thickness.

Forces are in pounds-force for 1 psi of air pressure inside. Multiply by your real pressure,
for example 0.25 psi (about 7 inches of water) gives a quarter of the numbers shown.
"""
import math
import os
import sys
import time
import numpy as np

import make_pattern as P
import sim_polyp as S

JAMMED = 1.05                 # fabric stretched more than 5 %: the fingers can't fold any further
STRING_STIFFNESS = 1000.0     # how hard the cord pulls back if it would stretch (a stiff spring)
FINGERS_PER_POLYP = P.THUMBS


def _opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def string_state(m, X, H, length):
    """Cord length (path along the seam + last stretch to the hitch) and its pull force."""
    p, c = m["string_path"], m["centre"]
    seg = np.linalg.norm(np.diff(X[p], axis=0), axis=1).sum()
    ell = seg + np.linalg.norm(X[c] - H)
    tension = 2 * STRING_STIFFNESS * max(0.0, ell - length)
    return ell, tension


def run(hitch=1.0, pull_max=10.0, steps=10, iters=3000):
    m = S.build(single=True)
    print("inflating the polyp...", flush=True)
    X = S.relax(m, iters=6000)
    X = S.relax(m, iters=iters, x0=X, hollow=True)           # same shape, with the tube open
    c = m["centre"]
    H0 = np.array([0.0, 0.0, X[c, 2] - hitch])
    p = m["string_path"]
    length = np.linalg.norm(np.diff(X[p], axis=0), axis=1).sum() + np.linalg.norm(X[c] - H0)
    print(f"centre point {X[c, 2]:.2f} in above the tube end; hitch {hitch:g} in below it; "
          f"cord {length:.2f} in from tip to hitch", flush=True)
    frames, jammed_at = [], None
    for i, d in enumerate(np.linspace(0, pull_max, steps + 1)):
        H = H0 - [0, 0, d]
        string = dict(path=p, centre=c, hitch=H, length=length, k=STRING_STIFFNESS)
        t0 = time.time()
        X = S.relax(m, iters=iters, x0=X, hollow=True, string=string)
        ell, T = string_state(m, X, H, length)
        tip = X[m["tips"][0]]
        # air volume, from the same formula the solver uses
        a, b, cc = (X[m["F"][:, k]] - [0, 0, -P.CUFF_HEIGHT] for k in range(3))
        vol = np.einsum("ij,ij->", a, np.cross(b, cc)) / 6 * FINGERS_PER_POLYP
        frames.append(dict(pull=d, X=X.copy(), H=H, force=FINGERS_PER_POLYP * T, tip_z=tip[2],
                           tip_r=math.hypot(tip[0], tip[1]), centre_z=X[c, 2], volume=vol,
                           stretch=float(np.max(np.linalg.norm(X[m["E"][:, 1]] - X[m["E"][:, 0]], axis=1) / m["L"]))))
        f = frames[-1]
        if f["stretch"] > JAMMED:       # the cord can't shorten any more: the numbers are meaningless
            frames.pop()
            jammed_at = d
            print(f"pull {d:4.1f} in: jammed (fabric would stretch {100 * (f['stretch'] - 1):.0f} %). "
                  f"The most the hitch can be pulled is between {frames[-1]['pull']:g} and {d:g} in.", flush=True)
            break
        print(f"pull {d:4.1f} in: force {f['force']:6.2f} lbf/psi, tip height {f['tip_z']:5.2f}, "
              f"tip out {f['tip_r']:4.2f}, fabric stretch max {f['stretch']:.3f}  ({time.time() - t0:.0f} s)", flush=True)
    return m, frames, jammed_at


def picture(m, frames, path, title, jammed_at=None):
    import matplotlib.pyplot as plt
    n = len(frames)
    cols = 4
    rows = math.ceil((n + 1) / cols)
    fig = plt.figure(figsize=(3.1 * cols, 3.9 * rows + 0.8))
    rot = lambda k: np.array([[math.cos(2 * math.pi * k / P.THUMBS), -math.sin(2 * math.pi * k / P.THUMBS), 0],
                              [math.sin(2 * math.pi * k / P.THUMBS), math.cos(2 * math.pi * k / P.THUMBS), 0],
                              [0, 0, 1]])
    for i, fr in enumerate(frames):
        ax = fig.add_subplot(rows, cols, i + 1, projection="3d")
        full, Xf = S.replicate(m, fr["X"])
        lines = []
        for k in range(P.THUMBS):                      # the cord of each finger, then down to the hitch
            R = rot(k)
            lines.append(np.vstack([fr["X"][m["string_path"]], fr["H"]]) @ R.T)
        S.draw_polyp(ax, full, Xf, 14, 35, strings=lines)
        ax.set_title(f"pull {fr['pull']:.1f} in", fontsize=10)
    ax = fig.add_subplot(rows, cols, n + 1)
    pulls = [f["pull"] for f in frames]
    ax.plot(pulls, [f["force"] for f in frames], "o-", color="tab:blue", label="pull force (lbf per psi)")
    ax.set_xlabel("hitch pulled down (in)")
    ax.set_ylabel("force (lbf per 1 psi of air)")
    ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(pulls, [f["tip_z"] for f in frames], "s--", color="tab:red", label="fingertip height (in)")
    ax2.set_ylabel("fingertip height above tube end (in)")
    ax.set_title("force and fingertip height", fontsize=10)
    if jammed_at is not None:
        ax.axvline(frames[-1]["pull"] + 0.5, color="0.5", ls=":")
        ax.text(0.97, 0.5, f"jams near {frames[-1]['pull'] + 0.5:g} in:\nthe fingers can't fold\nany further",
                transform=ax.transAxes, ha="right", fontsize=8, color="0.3")
    fig.suptitle(title, fontsize=12)
    fig.text(0.5, 0.005, "Blue = cords (tip, along the seam, down to the hitch). Constant air pressure. "
             "Force is for 1 psi: multiply by your real pressure.", ha="center", fontsize=8.5)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else \
        f"polyp-{P.FINGERS}-taper" + ("-string" if P.TUNNEL else "") if P.TAPER else f"polyp-{P.FINGERS}-club"
    os.makedirs(out, exist_ok=True)
    hitch, pull_max, steps = _opt("--hitch", 1.0), _opt("--pull-max", 10.0), int(_opt("--steps", 10))
    m, frames, jammed_at = run(hitch, pull_max, steps)
    picture(m, frames, os.path.join(out, f"{name}-pull.png"),
            f"{name}: pulling the string (hitch {hitch:g} in below the centre point)", jammed_at)
    with open(os.path.join(out, f"{name}-pull.csv"), "w") as f:
        f.write("pull_in,force_lbf_per_psi,tip_height_in,tip_out_in,centre_height_in,air_volume_cu_in\n")
        for fr in frames:
            f.write(f"{fr['pull']:.2f},{fr['force']:.3f},{fr['tip_z']:.3f},{fr['tip_r']:.3f},"
                    f"{fr['centre_z']:.3f},{fr['volume']:.1f}\n")
    print("done")


if __name__ == "__main__":
    main()
