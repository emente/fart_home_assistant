from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import csv
import logging
from pathlib import Path

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

CONF_STATION_ID = "station_id"
CONF_STATION_SELECTOR = "station_selector"
CONF_EVENT_TYPE = "event_type"
CONF_LIMIT = "limit"

DEFAULT_EVENT_TYPE = "dep"
DEFAULT_LIMIT = 10
KVV_DM_API_URL = "https://www.kvv.de/tunnelEfaDirect.php"

# KVV/EFA mode-of-transport codes that represent rail-like services; anything
# else (bus codes) is treated as "bus". Used only as a fallback for entries
# that don't carry an explicit pointType.
RAIL_MOT_TYPES = {"0", "1", "2", "3", "4", "13", "14", "15", "16", "17", "18"}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_STATION_ID): str,
        vol.Optional(CONF_STATION_SELECTOR): str,
        vol.Optional(CONF_NAME, default="FART"): str,
        vol.Optional(CONF_EVENT_TYPE, default=DEFAULT_EVENT_TYPE): vol.In(["dep", "arr"]),
        vol.Optional(CONF_LIMIT, default=DEFAULT_LIMIT): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    }
)

SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            FartDeparturesSensor(
                station_id=config_entry.data.get(CONF_STATION_ID),
                station_selector=None,
                name=config_entry.title,
                event_type=DEFAULT_EVENT_TYPE,
                limit=DEFAULT_LIMIT,
            )
        ]
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if CONF_STATION_ID not in config and CONF_STATION_SELECTOR not in config:
        raise ValueError("Either station_id or station_selector must be configured")

    async_add_entities(
        [
            FartDeparturesSensor(
                station_id=config.get(CONF_STATION_ID),
                station_selector=config.get(CONF_STATION_SELECTOR),
                name=config[CONF_NAME],
                event_type=config[CONF_EVENT_TYPE],
                limit=config[CONF_LIMIT],
            )
        ]
    )


class FartDeparturesSensor(SensorEntity):
    _attr_should_poll = True

    def __init__(
        self,
        station_id: str | None,
        station_selector: str | None,
        name: str,
        event_type: str,
        limit: int,
    ) -> None:
        self._station_id = station_id
        self._station_selector = station_selector
        self._event_type = event_type
        self._limit = limit
        self._attr_unique_id = f"fart_{station_id or station_selector or 'unconfigured'}_{event_type}"
        self._attr_name = name
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self) -> None:
        try:
            station_id, station_name, city_name = self._resolve_station_details()
            data = await self._fetch_departures(station_id=station_id, station_name=station_name, city_name=city_name)
            self._attr_native_value = data["fetchedAt"]
            self._attr_extra_state_attributes = {
                "station_id": station_id,
                "station_name": station_name,
                "city_name": city_name,
                "event_type": self._event_type,
                "platforms": data["platforms"],
                "fetched_at": data["fetchedAt"],
            }
            self._attr_available = True
        except Exception as err:
            _LOGGER.warning("Failed to fetch FART departures: %s", err)
            self._attr_available = False
            self._attr_extra_state_attributes = {"error": str(err)}

    def _resolve_station_details(self) -> tuple[str, str, str]:
        if self._station_id:
            station_id = self._station_id
            station_name = self._station_id
            city_name = self._station_id
            metadata = _station_metadata_by_gid().get(station_id)
            if metadata:
                station_name = metadata["stop_name"]
                city_name = metadata["place_name"]
            return station_id, station_name, city_name

        if not self._station_selector:
            raise RuntimeError("No station_id or station_selector configured")

        selector_state = self.hass.states.get(self._station_selector)
        if selector_state is None:
            raise RuntimeError(f"Station selector entity not found: {self._station_selector}")

        selected_label = selector_state.state
        if not selected_label or selected_label in {"unknown", "unavailable", "None"}:
            raise RuntimeError(f"Station selector {self._station_selector} has no valid selection")

        metadata = _station_metadata_by_label().get(selected_label)
        if metadata is None:
            raise RuntimeError(
                f"Selected station label '{selected_label}' was not found in the local stop list"
            )

        return metadata["gid"], metadata["stop_name"], metadata["place_name"]

    async def _fetch_departures(
        self,
        station_id: str,
        station_name: str,
        city_name: str,
    ) -> dict[str, object]:
        params = {
            "action": "XSLT_DM_REQUEST",
            "outputFormat": "JSON",
            "type_dm": "stop",
            "name_dm": station_id,
            "mode": "direct",
            "useRealtime": "1",
            "limit": str(self._limit),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(KVV_DM_API_URL, params=params) as response:
                if response.status != 200:
                    body_text = await response.text()
                    raise RuntimeError(
                        f"Request failed with status {response.status}: {body_text[:200]}"
                    )
                payload = await response.json(content_type=None)

        departures = payload.get("departureList") or []
        platforms = _map_departures_to_platforms(departures)

        return {
            "stationName": station_name,
            "cityName": city_name,
            "platforms": platforms,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }


def _map_departures_to_platforms(departures: list[dict[str, object]]) -> list[dict[str, object]]:
    platforms: dict[str, dict[str, object]] = {}

    for entry in departures:
        planned_time = _format_datetime(entry.get("dateTime"))
        if not planned_time:
            continue
        real_time = _format_datetime(entry.get("realDateTime")) or planned_time

        serving_line = entry.get("servingLine") or {}
        platform_name = str(entry.get("platformName") or entry.get("platform") or "").strip()
        if platform_name.startswith("Gleis"):
            platform_name = platform_name[len("Gleis") :].strip()
        elif platform_name.startswith("Bstg."):
            platform_name = platform_name[len("Bstg.") :].strip()
        platform_type = (
            "rail"
            if entry.get("pointType") == "Gleis" or serving_line.get("motType") in RAIL_MOT_TYPES
            else "bus"
        )

        key = f"{platform_type}:{platform_name or 'unknown'}"
        if key not in platforms:
            platforms[key] = {
                "platform": {"type": platform_type, "name": platform_name},
                "departures": [],
            }

        direction = serving_line.get("direction") or "—"
        platforms[key]["departures"].append(
            {
                "lineName": serving_line.get("number") or serving_line.get("symbol") or "—",
                "direction": [direction] if direction != "—" else [],
                "plannedTime": planned_time,
                "realTime": real_time,
                "vehicleType": serving_line.get("name") or "",
            }
        )

    output = []
    for platform_entry in platforms.values():
        platform_entry["departures"] = sorted(
            platform_entry["departures"],
            key=lambda item: item.get("plannedTime") or "",
        )
        output.append(platform_entry)

    output.sort(key=lambda item: (item["platform"]["type"], item["platform"]["name"]))
    return output


def _format_datetime(parts: dict[str, str] | None) -> str | None:
    if not parts:
        return None

    try:
        return (
            f"{int(parts['year']):04d}-{int(parts['month']):02d}-{int(parts['day']):02d}"
            f"T{int(parts['hour']):02d}:{int(parts['minute']):02d}:00"
        )
    except (KeyError, ValueError):
        return None


@lru_cache(maxsize=1)
def _station_metadata_by_label() -> dict[str, dict[str, str]]:
    csv_path = Path(__file__).with_name("stops.csv")
    lookup: dict[str, dict[str, str]] = {}

    if not csv_path.exists():
        return lookup

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            gid = (row.get("gid") or "").strip()
            place_name = (row.get("place_name") or "").strip()
            stop_name = (row.get("stop_name") or "").strip()
            if not gid or not place_name or not stop_name:
                continue

            label = f"{stop_name} ({place_name})"
            lookup[label] = {
                "gid": gid,
                "place_name": place_name,
                "stop_name": stop_name,
            }

    return lookup


def _station_metadata_by_gid() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for label, metadata in _station_metadata_by_label().items():
        lookup[metadata["gid"]] = metadata
    return lookup
