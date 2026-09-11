from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

CARD_URL_PATH = f"/{DOMAIN}_files/fart-ha-card.js"
CARD_FILE_PATH = Path(__file__).with_name("www") / "fart-ha-card.js"
MANIFEST_PATH = Path(__file__).with_name("manifest.json")


def _card_version() -> str:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(CARD_FILE_PATH), True)]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={_card_version()}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
