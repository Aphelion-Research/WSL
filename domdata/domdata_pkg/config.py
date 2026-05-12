from __future__ import annotations

import os
from dataclasses import dataclass


SECRET_KEYS = {"DOMDATA_MT5_PASSWORD"}


@dataclass(frozen=True)
class DomdataConfig:
    login: str | None
    server: str | None
    password: str | None
    terminal_path: str | None
    wineprefix: str | None
    wine_python: str | None


def read_config() -> DomdataConfig:
    return DomdataConfig(
        login=os.getenv("DOMDATA_MT5_LOGIN") or None,
        server=os.getenv("DOMDATA_MT5_SERVER") or None,
        password=os.getenv("DOMDATA_MT5_PASSWORD") or None,
        terminal_path=os.getenv("DOMDATA_MT5_PATH") or None,
        wineprefix=os.getenv("DOMDATA_WINEPREFIX") or None,
        wine_python=os.getenv("DOMDATA_WINE_PYTHON") or None,
    )


def mask_value(key: str, value: str | None) -> str:
    if not value:
        return "missing"
    if key in SECRET_KEYS:
        return "set"
    if "LOGIN" in key:
        return f"{value[:2]}***{value[-2:]}" if len(value) > 4 else "***"
    return value


def doctor_rows() -> list[tuple[str, str]]:
    cfg = read_config()
    return [
        ("DOMDATA_MT5_LOGIN", mask_value("DOMDATA_MT5_LOGIN", cfg.login)),
        ("DOMDATA_MT5_SERVER", mask_value("DOMDATA_MT5_SERVER", cfg.server)),
        ("DOMDATA_MT5_PASSWORD", mask_value("DOMDATA_MT5_PASSWORD", cfg.password)),
        ("DOMDATA_MT5_PATH", mask_value("DOMDATA_MT5_PATH", cfg.terminal_path)),
        ("DOMDATA_WINEPREFIX", mask_value("DOMDATA_WINEPREFIX", cfg.wineprefix)),
        ("DOMDATA_WINE_PYTHON", mask_value("DOMDATA_WINE_PYTHON", cfg.wine_python)),
    ]
