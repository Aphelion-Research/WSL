import pytest

from domdata_pkg.safety import BLOCKED_COMMANDS, blocked_command


def test_blocked_commands_include_trading_words():
    assert {"order-send", "order-check", "buy", "sell", "close", "modify"} <= BLOCKED_COMMANDS


def test_blocked_command_exits_nonzero():
    with pytest.raises(SystemExit) as exc:
        blocked_command(None)
    assert exc.value.code != 0
