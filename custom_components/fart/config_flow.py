from __future__ import annotations

import csv
from pathlib import Path

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN

CONF_STATION_ID = "station_id"


class FartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
            await self.async_set_unique_id(f"fart_{station_id}")
            self._abort_if_unique_id_configured()

            title = _station_label(station_id)
            return self.async_create_entry(
                title=title,
                data={
                    CONF_STATION_ID: station_id,
                },
            )

        station_options = _load_station_options()
        if not station_options:
            return self.async_abort(reason="no_stations")

        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_ID): vol.In(station_options),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


def _load_station_options() -> dict[str, str]:
    csv_path = Path(__file__).with_name("stops.csv")
    options: dict[str, str] = {}

    if not csv_path.exists():
        return options

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            gid = (row.get("gid") or "").strip()
            place_name = (row.get("place_name") or "").strip()
            stop_name = (row.get("stop_name") or "").strip()
            if not gid or not place_name or not stop_name:
                continue

            label = f"{stop_name} ({place_name})"
            options[gid] = label

    return options


def _station_label(station_id: str) -> str:
    options = _load_station_options()
    return options.get(station_id, station_id)
