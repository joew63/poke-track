from poke_track.state import StateStore
from poke_track.models import StockStatus


def test_notifies_on_transition_to_in_stock(tmp_path):
    state = StateStore(tmp_path / "state.json")
    assert state.record_and_should_notify("bestbuy:1", StockStatus.OUT_OF_STOCK) is False
    assert state.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is True


def test_does_not_renotify_while_still_in_stock_by_default(tmp_path):
    state = StateStore(tmp_path / "state.json")
    assert state.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is True
    assert state.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is False


def test_renotifies_after_cooldown_elapses(tmp_path):
    state = StateStore(tmp_path / "state.json", renotify_after_seconds=0)
    assert state.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is True
    assert state.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is True


def test_unknown_status_preserves_last_known_status(tmp_path):
    state = StateStore(tmp_path / "state.json")
    assert state.record_and_should_notify("target:1", StockStatus.IN_STOCK) is True
    # a blocked/failed check shouldn't erase in_stock or trigger a duplicate notify
    assert state.record_and_should_notify("target:1", StockStatus.UNKNOWN) is False
    assert state._data["target:1"]["status"] == StockStatus.IN_STOCK.value
    assert state._data["target:1"]["last_check_result"] == StockStatus.UNKNOWN.value


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "state.json"
    first = StateStore(path)
    first.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK)
    first.save()

    reloaded = StateStore(path)
    # already in_stock, so a repeat check should not re-notify
    assert reloaded.record_and_should_notify("bestbuy:1", StockStatus.IN_STOCK) is False
