from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def _continuation_arrivals():
    """粤A1 跑 T1 到终点 8:18，2 分钟后又以 T3 从起点发出（折返 2 分钟）。"""
    base = datetime(2026, 1, 1, 8, 0)
    return [
        {"stop_name": "起点站", "trip_no": "T1", "vehicle_no": "粤A1", "actual_arrive": base},
        {"stop_name": "终点站", "trip_no": "T1", "vehicle_no": "粤A1", "actual_arrive": base + timedelta(minutes=18)},
        {"stop_name": "起点站", "trip_no": "T2", "vehicle_no": "粤A2", "actual_arrive": base + timedelta(minutes=18)},
        {"stop_name": "终点站", "trip_no": "T2", "vehicle_no": "粤A2", "actual_arrive": base + timedelta(minutes=36)},
        {"stop_name": "起点站", "trip_no": "T3", "vehicle_no": "粤A1", "actual_arrive": base + timedelta(minutes=20)},
        {"stop_name": "终点站", "trip_no": "T3", "vehicle_no": "粤A1", "actual_arrive": base + timedelta(minutes=38)},
    ]

def test_short_turnaround_not_bunching():
    events = detect_bunching(_continuation_arrivals(), 8.0, 3.0, 15.0,
                             min_turnaround_min=6.0, terminal_stop="终点站")
    t3_events = [e for e in events if e.later_trip == "T3"]
    assert t3_events, "应存在 T3 相关事件"
    for e in t3_events:
        assert e.status == "turnaround_short"
        assert e.turnaround_min == 2.0
        assert "折返" in e.suggestion
        assert "串车" not in e.suggestion

def test_sufficient_turnaround_uses_normal_thresholds():
    events = detect_bunching(_continuation_arrivals(), 8.0, 3.0, 15.0,
                             min_turnaround_min=2.0, terminal_stop="终点站")
    t3_events = [e for e in events if e.later_trip == "T3"]
    assert all(e.status == "bunching" for e in t3_events)

def test_no_turnaround_config_unchanged():
    events = detect_bunching(_continuation_arrivals(), 8.0, 3.0, 15.0)
    t3_events = [e for e in events if e.later_trip == "T3"]
    assert all(e.status == "bunching" for e in t3_events)
    assert all(e.turnaround_min is None for e in events)
