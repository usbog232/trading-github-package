from trade_events import append_event, latest_events


def test_trade_events_append_and_read():
    append_event({'kind': 'test_event', 'status': 'ok'})
    events = latest_events(1)
    assert events[-1]['kind'] == 'test_event'
