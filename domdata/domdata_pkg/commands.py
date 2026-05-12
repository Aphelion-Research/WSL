from __future__ import annotations

from typing import Any

from . import __version__
from .config import doctor_rows
from .mt5_client import connect, load_mt5, parse_dt, runtime_env_summary, shutdown, timeframe
from .serializers import emit


def _emit(args: Any, value: Any) -> None:
    emit(value, getattr(args, "format", "json"), getattr(args, "out", None))


def doctor(_args: Any) -> None:
    print("DOMDATA DOCTOR")
    for key, value in doctor_rows():
        print(f"{key}: {value}")
    print(f"runtime_env: {runtime_env_summary()}")
    try:
        mt5 = load_mt5()
        print("MetaTrader5 import: OK")
        print(f"MetaTrader5 version attr: {getattr(mt5, '__version__', 'unknown')}")
    except SystemExit:
        print("MetaTrader5 import: FAIL")


def version(args: Any) -> None:
    mt5 = connect(args)
    try:
        _emit(args, {"domdata": __version__, "mt5": mt5.version()})
    finally:
        shutdown(mt5)


def terminal_info(args: Any) -> None:
    mt5 = connect(args)
    try:
        _emit(args, mt5.terminal_info())
    finally:
        shutdown(mt5)


def account_info(args: Any) -> None:
    mt5 = connect(args)
    try:
        _emit(args, mt5.account_info())
    finally:
        shutdown(mt5)


def symbols_get(args: Any) -> None:
    mt5 = connect(args)
    try:
        _emit(args, mt5.symbols_get(group=args.group) if args.group else mt5.symbols_get())
    finally:
        shutdown(mt5)


def select_symbol(args: Any) -> None:
    mt5 = connect(args)
    try:
        ok = mt5.symbol_select(args.symbol, True)
        _emit(args, {"symbol": args.symbol, "selected": bool(ok), "last_error": mt5.last_error(), "info": mt5.symbol_info(args.symbol)})
    finally:
        shutdown(mt5)


def symbol_info(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select(args.symbol, True)
        _emit(args, mt5.symbol_info(args.symbol))
    finally:
        shutdown(mt5)


def symbol_tick(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select(args.symbol, True)
        tick = mt5.symbol_info_tick(args.symbol)
        if tick is None:
            _emit(args, {"symbol": args.symbol, "tick": None, "last_error": mt5.last_error(), "hint": "Symbol may not be streaming right now, but history may still work."})
        else:
            _emit(args, tick)
    finally:
        shutdown(mt5)


def rates_pos(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select(args.symbol, True)
        _emit(args, mt5.copy_rates_from_pos(args.symbol, timeframe(mt5, args.timeframe), args.start_pos, args.count))
    finally:
        shutdown(mt5)


def ticks_from(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select(args.symbol, True)
        _emit(args, mt5.copy_ticks_from(args.symbol, parse_dt(args.start), args.count, mt5.COPY_TICKS_ALL))
    finally:
        shutdown(mt5)


def ticks_range(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select(args.symbol, True)
        _emit(args, mt5.copy_ticks_range(args.symbol, parse_dt(args.start), parse_dt(args.end), mt5.COPY_TICKS_ALL))
    finally:
        shutdown(mt5)


def xau(args: Any) -> None:
    mt5 = connect(args)
    try:
        mt5.symbol_select("XAUUSD", True)
        _emit(args, {"symbol": "XAUUSD", "info": mt5.symbol_info("XAUUSD"), "tick": mt5.symbol_info_tick("XAUUSD")})
    finally:
        shutdown(mt5)


def xautick(args: Any) -> None:
    args.symbol = "XAUUSD"
    symbol_tick(args)


def xaurates(args: Any) -> None:
    args.symbol = "XAUUSD"
    args.timeframe = "M1"
    args.start_pos = 0
    rates_pos(args)


def xauticks(args: Any) -> None:
    args.symbol = "XAUUSD"
    ticks_from(args)
