#!/usr/bin/env python3
"""H3 figures, from H3_SUMMARY_2026-09-27.json (h3_report.py's output).

1. H3_FIGURE_BIAS_2026-09-27.png - small multiples by ground pixel scale: |b| (arcsec) against seeing FWHM, visit mean
   with the visit range as bars; G at r = 2 (blue, circles), G at zero aperture (orange, squares), M at zero aperture
   (aqua, triangles). Validated palette (3 slots, all-pairs); aqua < 3:1 contrast -> legend + the table in H3_RUNLOG.
2. H3_FIGURE_DIRECTION_2026-09-27.png - per visit, the sky plane (north up, east left): the G b2 and G b0 vectors for
   two typical set-ups (professional: 1.0" seeing, 0.44"/px; amateur: 3.0" seeing, 1.50"/px), with the antisolar
   (PsAng) and negative-velocity (PsAMV) directions drawn as grey rays.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
C1, C2, C3 = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
S = json.load(open(os.path.join(HERE, 'H3_SUMMARY_2026-09-27.json')))
VIS = ['22', '03', '04', '05', '06']
SCALES = [0.24, 0.44, 0.70, 1.00, 1.50, 2.00]


def figure_bias():
    fig, axs = plt.subplots(1, 6, figsize=(17, 4.2), sharey=True)
    fig.patch.set_facecolor(SURF)
    for ax, gs in zip(axs, SCALES):
        ax.set_facecolor(SURF)
        fws = sorted(set(r['fw'] for r in S.values() if abs(r['gs'] - gs) < 1e-9))
        for est, key, c, mk, lab in (('G', 'b2', C1, 'o', 'G, r = 2 px'), ('G', 'b0', C2, 's', 'G, zero aperture'), ('M', 'b0', C3, '^', 'M, zero aperture')):
            mu, lo, hi = [], [], []
            for fw in fws:
                v = [S['%s|%.1f|%.2f' % (vv, fw, gs)][est][key]['len'] for vv in VIS if '%s|%.1f|%.2f' % (vv, fw, gs) in S]
                mu.append(np.mean(v)); lo.append(np.min(v)); hi.append(np.max(v))
            mu, lo, hi = map(np.array, (mu, lo, hi))
            ax.errorbar(fws, mu, yerr=[mu - lo, hi - mu], fmt='-' + mk, color=c, lw=2, ms=6, mec=SURF, mew=1.5, capsize=3, elinewidth=1, label=lab)
        ax.set_title('%.2f"/px' % gs, color=INK, fontsize=11)
        ax.set_xlabel('seeing FWHM (")', color=INK, fontsize=10)
        ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=9)
        ax.set_xlim(0.5, 4.3)
    axs[0].set_ylabel('bias against HST\'s zero-aperture position (")', color=INK, fontsize=10)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper center', bbox_to_anchor=(0.5, 0.92), ncol=3, frameon=False, fontsize=10, labelcolor=INK)
    fig.suptitle('3I/ATLAS, Hubble frames degraded to the ground: length of the photocentre bias (visit mean; bars: the five visits\' range)', color=INK, fontsize=12, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(os.path.join(HERE, 'H3_FIGURE_BIAS_2026-09-27.png'), dpi=110, facecolor=SURF)


def figure_direction(hz):
    setups = [((1.0, 0.44), 'professional: 1.0" seeing, 0.44"/px', '-'), ((3.0, 1.50), 'amateur: 3.0" seeing, 1.50"/px', '--')]
    fig, axs = plt.subplots(1, 5, figsize=(17, 4.0))
    fig.patch.set_facecolor(SURF)
    lim = 0.0
    for (fw, gs), _, _ in setups:
        for v in VIS:
            r = S['%s|%.1f|%.2f' % (v, fw, gs)]['G']
            lim = max(lim, r['b2']['len'], r['b0']['len'])
    lim *= 1.25
    for ax, v in zip(axs, VIS):
        ax.set_facecolor(SURF)
        for pa, name in ((hz[v]['psang'], 'antisolar'), (hz[v]['psamv'], '-v')):
            t = np.radians(pa)
            ax.plot([0, lim * np.sin(t)], [0, lim * np.cos(t)], color=INK2, lw=1, ls=':')   # x axis inverted: +xi (east) plots left
            ax.annotate(name, (0.92 * lim * np.sin(t), 0.92 * lim * np.cos(t)), color=INK2, fontsize=8, ha='center')
        for (fw, gs), lab, ls in setups:
            r = S['%s|%.1f|%.2f' % (v, fw, gs)]['G']
            for key, c in (('b2', C1), ('b0', C2)):
                xi, eta = r[key]['xi'], r[key]['eta']
                ax.annotate('', xy=(xi, eta), xytext=(0, 0), arrowprops=dict(arrowstyle='-|>', color=c, lw=2, ls=ls))
        ax.set_xlim(lim, -lim); ax.set_ylim(-lim, lim)   # east (positive xi) to the left
        ax.set_aspect('equal'); ax.grid(True, color=GRID, lw=0.6)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.set_title('visit %s (phase %.1f°)' % (v, hz[v]['phase']), color=INK, fontsize=10)
        ax.set_xlabel('east  ←  (")  →  west', color=INK2, fontsize=8)
    axs[0].set_ylabel('north (")', color=INK2, fontsize=9)
    from matplotlib.lines import Line2D
    hs = [Line2D([0], [0], color=C1, lw=2), Line2D([0], [0], color=C2, lw=2), Line2D([0], [0], color=INK2, lw=2, ls='-'), Line2D([0], [0], color=INK2, lw=2, ls='--')]
    fig.legend(hs, ['G at r = 2 px', 'G at zero aperture', setups[0][1], setups[1][1]], loc='upper center', bbox_to_anchor=(0.5, 0.92), ncol=4, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle('Direction of the bias on the sky (north up, east left), against HST\'s zero-aperture position', color=INK, fontsize=12, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.83))
    fig.savefig(os.path.join(HERE, 'H3_FIGURE_DIRECTION_2026-09-27.png'), dpi=110, facecolor=SURF)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, HERE)
    from h3_report import horizons_table
    cols, rows = horizons_table()
    idx = {c.strip(): i for i, c in enumerate(cols)}
    hz = {}
    for v, r in zip(VIS, rows):
        hz[v] = dict(psang=float(r[idx['PsAng']]), psamv=float(r[idx['PsAMV']]), phase=float(r[idx['S-T-O']]))
    figure_bias()
    figure_direction(hz)
    print('wrote H3_FIGURE_BIAS / H3_FIGURE_DIRECTION')
