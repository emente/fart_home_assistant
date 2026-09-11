from __future__ import annotations

import csv
from pathlib import Path

import voluptuous as vol

from homeassistant.components.select import PLATFORM_SCHEMA, SelectEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

CONF_CSV_PATH = "csv_path"
DEFAULT_CSV_PATH = str(Path(__file__).with_name("stops.csv"))

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default="FART Station"): str,
        vol.Optional(CONF_CSV_PATH, default=DEFAULT_CSV_PATH): str,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    async_add_entities(
        [
            FartStationSelect(
                name=config[CONF_NAME],
                csv_path=config[CONF_CSV_PATH],
            )
        ]
    )


class FartStationSelect(SelectEntity):
    def __init__(self, name: str, csv_path: str) -> None:
        self._attr_name = name
        self._attr_unique_id = "fart_station_selector"
        self._csv_path = csv_path
        self._attr_options = self._load_options()
        self._attr_current_option = self._attr_options[0] if self._attr_options else None

    def _load_options(self) -> list[str]:
        options: list[str] = []
        csv_path = Path(self._csv_path)

        if not csv_path.exists():
            return options

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                place_name = (row.get("place_name") or "").strip()
                stop_name = (row.get("stop_name") or "").strip()
                if place_name and stop_name:
                    options.append(f"{stop_name} ({place_name})")

        return options

    @property
    def options(self) -> list[str]:
        return self._attr_options

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
