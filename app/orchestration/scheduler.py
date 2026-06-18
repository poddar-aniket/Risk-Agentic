"""
APScheduler — triggers the macro loop (full 6-agent pipeline run over new
events from active data sources) on an interval, in-process inside FastAPI.

TODO (Day 4 — owner: poddar-aniket):
- Wire to the compiled graph from build_graph().
- Interval from config.yaml (orchestration.macro_loop_interval_hours, default 3).
"""


def start_scheduler():
    raise NotImplementedError("Wire APScheduler macro loop — Day 4")
