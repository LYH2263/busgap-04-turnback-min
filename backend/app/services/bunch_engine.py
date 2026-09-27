"""Bus bunching: planned headway vs actual arrival gaps."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime

@dataclass
class GapEvent:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    planned_headway_min: float
    status: str
    suggestion: str
    turnaround_min: float | None = None

def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    return ("normal", f"间隔接近计划 {planned_headway_min:.1f} 分钟，保持即可。")

def short_turnarounds(arrivals: list[dict], terminal_stop: str, min_turnaround_min: float) -> dict[str, float]:
    """同车到达终点后接续的下一班：折返时间低于最小折返的班次 -> 实际折返分钟。"""
    by_vehicle: dict[str, list[dict]] = {}
    for a in arrivals:
        vehicle = a.get("vehicle_no") or ""
        if vehicle:
            by_vehicle.setdefault(vehicle, []).append(a)
    short: dict[str, float] = {}
    for items in by_vehicle.values():
        items = sorted(items, key=lambda x: x["actual_arrive"])
        for i, cur in enumerate(items):
            if cur["stop_name"] != terminal_stop:
                continue
            for nxt in items[i + 1:]:
                if nxt["trip_no"] == cur["trip_no"]:
                    continue
                turn_min = (nxt["actual_arrive"] - cur["actual_arrive"]).total_seconds() / 60.0
                if turn_min < min_turnaround_min:
                    short[nxt["trip_no"]] = round(turn_min, 2)
                break
    return short

def detect_bunching(arrivals: list[dict], planned_headway_min: float, bunch_threshold: float, large_threshold: float,
                    min_turnaround_min: float | None = None, terminal_stop: str | None = None) -> list[GapEvent]:
    short = short_turnarounds(arrivals, terminal_stop, min_turnaround_min) \
        if min_turnaround_min is not None and terminal_stop else {}
    by_stop: dict[str, list[dict]] = {}
    for a in arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)
    events: list[GapEvent] = []
    for stop, items in by_stop.items():
        items = sorted(items, key=lambda x: x["actual_arrive"])
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            status, suggestion = classify_gap(gap_min, planned_headway_min, bunch_threshold, large_threshold)
            turn_min = short.get(cur["trip_no"])
            if turn_min is not None and status == "bunching":
                status = "turnaround_short"
                suggestion = (f"同车终点折返 {turn_min:.1f} 分钟，低于最小折返 {min_turnaround_min:g} 分钟，"
                              f"建议延长终点折返时间或调整接续班次。")
            events.append(GapEvent(stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2),
                                   planned_headway_min, status, suggestion, turn_min))
    return events

def events_to_dicts(events: list[GapEvent]) -> list[dict]:
    return [asdict(e) for e in events]
