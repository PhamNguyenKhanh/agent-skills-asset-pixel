"""Hybrid 3-track animation engine: sheet (img2img), video (i2v -> pixel lattice), and procedural (offline)."""

from pixel_forge.animate.pipeline import AnimationResult, create_animation
from pixel_forge.animate.procedural_track import generate_procedural_frames
from pixel_forge.animate.timing import find_best_loop, lock_static_zone, register_frames_to_anchor, retime_oneshot

__all__ = [
    "AnimationResult",
    "create_animation",
    "find_best_loop",
    "generate_procedural_frames",
    "lock_static_zone",
    "register_frames_to_anchor",
    "retime_oneshot",
]
