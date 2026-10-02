"""domino_calibrator - open zero-aperture comet astrometry (the shrinking-aperture method), with the tools to test it.

A Castle product from Domino Observatory. Built by Annie, the Castle's AI. 27 Sept 2026. Its record:
archive/CALIBRATOR_2026-09-27.md.
Modules: apertures (exact circle-pixel overlaps), estimators (M, G, P), shrink (the 2.0-6.0 px sequence and
its extrapolation), synth (synthetic comets), ades (the ADES record).
Coordinates: 0-based, pixel centres on integers, x = column, y = row.
"""
from .apertures import circle_moments, pixel_overlap
from .estimators import moment_centroid, gauss_fit, peak_quadratic, annulus_background
from .shrink import shrink, linear_extrapolate, PUBLISHED_RADII
from . import synth, ades

__version__ = '0.1.0'
__credit__ = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
