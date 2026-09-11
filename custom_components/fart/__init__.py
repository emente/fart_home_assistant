from __future__ import annotations

from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

PLATFORMS = ["sensor"]
CONF_STATION_ID = "station_id"

CARD_URL_PATH = f"/{DOMAIN}_files/fart-ha-card.js"
CARD_FILE_PATH = Path(__file__).with_name("www") / "fart-ha-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(CARD_FILE_PATH), False)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    registry = er.async_get(hass)
    unique_id = f"fart_{entry.data.get(CONF_STATION_ID)}_dep"
    is_new_entry = registry.async_get_entity_id("sensor", DOMAIN, unique_id) is None

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if is_new_entry:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id:
            persistent_notification.async_create(
                hass,
                title=f"FART: {entry.title} added",
                message=(
                    "**One-time setup:** go to Settings -> Dashboards -> "
                    "the ⋮ menu -> Resources -> Add Resource, and add "
                    f"`{CARD_URL_PATH}` as a **JavaScript Module** "
                    "(skip this if you've already added it for another station).\n\n"
                    "Then add the departures card to a dashboard: edit a dashboard, "
                    "click **+ Add Card**, choose **Manual**, and paste:\n\n"
                    "```yaml\n"
                    "type: custom:fart-ha-card\n"
                    f"entity: {entity_id}\n"
                    f"title: {entry.title}\n"
                    "```\n\n"
                    "[Open dashboards](/config/lovelace/dashboards)"
                ),
                notification_id=f"{DOMAIN}_setup_{entry.entry_id}",
            )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
