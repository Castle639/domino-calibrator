#!/usr/bin/env python3
"""S1 figure: the synthetic bias grid as small multiples (rows: nucleus share eta; columns: coma shape).
x: seeing FWHM in pixels (log); y: bias along the asymmetry in units of the FWHM (noiseless, phase-mean).
Series (fixed categorical order, validated palette, all-pairs safe for 3 slots): G at r = 2 (blue, circles),
G at zero aperture (orange, squares), M at zero aperture (aqua, triangles); the aqua slot is below 3:1 contrast,
so every series is also named in the legend and on the first panel, and the table is S1_RUNLOG.
Output: runs/S1_FIGURE_2026-09-27.png
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
C1, C2, C3 = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'

R = json.load(open(os.path.join(HERE, 'S1_RESULTS_2026-09-27.json')))
models = [('dipole', 0.1, None, 'dipole a = 0.1'), ('dipole', 0.3, None, 'dipole a = 0.3'),
          ('grow', 0.3, 2.0, 'grow a = 0.3, ρ_s = 2 FWHM'), ('fade', 0.3, 2.0, 'fade a = 0.3, ρ_s = 2 FWHM')]
etas = [0.0, 0.1, 1.0]
fig, axs = plt.subplots(3, 4, figsize=(15, 9.5), sharex=True)
fig.patch.set_facecolor(SURF)
for i, e in enumerate(etas):
    for j, (m, a, rs, title) in enumerate(models):
        ax = axs[i, j]; ax.set_facecolor(SURF)
        rows = sorted([v for v in R.values() if v['model'] == m and abs(v['a'] - a) < 1e-9 and abs(v['eta'] - e) < 1e-9], key=lambda v: v['FWHM'])
        f = np.array([v['FWHM'] for v in rows])
        g2 = np.array([v['G']['b2'] for v in rows]) / f
        g0 = np.array([v['G']['b0'] for v in rows]) / f
        m0 = np.array([v['M']['b0'] for v in rows]) / f
        ax.axhline(0, color=INK2, lw=0.8)
        ax.plot(f, g2, '-o', color=C1, lw=2, ms=6, mec=SURF, mew=1.5, label='G, r = 2 px')
        ax.plot(f, g0, '-s', color=C2, lw=2, ms=6, mec=SURF, mew=1.5, label='G, zero aperture')
        ax.plot(f, m0, '-^', color=C3, lw=2, ms=6, mec=SURF, mew=1.5, label='M, zero aperture')
        ax.set_xscale('log'); ax.set_xticks([1, 1.5, 2, 3, 4, 6]); ax.set_xticklabels(['1', '1.5', '2', '3', '4', '6'])
        ax.minorticks_off()
        ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=9)
        if i == 0:
            ax.set_title(title, color=INK, fontsize=11)
        if j == 0:
            ax.set_ylabel('η = %g\nbias / FWHM' % e, color=INK, fontsize=10)
        if i == 2:
            ax.set_xlabel('seeing FWHM (px)', color=INK, fontsize=10)
        if i == 0 and j == 0:
            for y, c, t in ((g2[-1], C1, 'G r=2'), (g0[-1], C2, 'G r=0'), (m0[-1], C3, 'M r=0')):
                ax.annotate(t, (f[-1], y), xytext=(4, 0), textcoords='offset points', color=INK2, fontsize=8, va='center')
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc='upper center', bbox_to_anchor=(0.5, 0.965), ncol=3, frameon=False, fontsize=10, labelcolor=INK)
fig.suptitle('Synthetic comets: photocentre bias along the asymmetry (noiseless, 36-phase mean), in units of the seeing FWHM', color=INK, fontsize=12, y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(os.path.join(HERE, 'S1_FIGURE_2026-09-27.png'), dpi=110, facecolor=SURF)
print('wrote S1_FIGURE_2026-09-27.png')
