from __future__ import annotations

from datetime import datetime, timedelta, timezone
import csv
import logging
from pathlib import Path
from xml.etree import ElementTree as ET

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
DEFAULT_KVV_API_URL = "https://www.kvv.de/internet/service/ps/extapi/trias"
DEFAULT_REQUESTOR_REF = "FART"

TRIAS_NS = "http://www.vdv.de/trias"

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
        self._api_url = DEFAULT_KVV_API_URL
        self._requestor_ref = DEFAULT_REQUESTOR_REF
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
        xml_body = _build_request_xml(
            requestor_ref=self._requestor_ref,
            station_id=station_id,
            event_type=self._event_type,
            limit=self._limit,
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._api_url,
                data=xml_body,
                headers={"Content-Type": "application/xml; charset=utf-8"},
            ) as response:
                response_text = await response.text()

        if response.status != 200:
            raise RuntimeError(
                f"Request failed with status {response.status}: {response_text[:200]}"
            )

        root = ET.fromstring(response_text)
        results = _extract_stop_event_results(root)
        platforms = _map_results_to_platforms(results)

        return {
            "stationName": station_name,
            "cityName": city_name,
            "platforms": platforms,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }


def _build_request_xml(requestor_ref: str, station_id: str, event_type: str, limit: int) -> str:
    stop_event_type = "departure" if event_type == "dep" else "arrival"
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Trias version=\"1.1\"
  xmlns=\"http://www.vdv.de/trias\"
  xmlns:siri=\"http://www.siri.org.uk/siri\"
  xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
  <ServiceRequest>
    <siri:RequestTimeStamp>{_escape_xml(timestamp)}</siri:RequestTimeStamp>
    <siri:RequestorRef>{_escape_xml(requestor_ref)}</siri:RequestorRef>
    <RequestPayload>
      <StopEventRequest>
        <Location>
          <LocationRef>
            <StopPlaceRef>{_escape_xml(station_id)}</StopPlaceRef>
          </LocationRef>
          <DepArrTime>{_escape_xml(timestamp)}</DepArrTime>
        </Location>
        <Params>
          <NumberOfResults>{limit}</NumberOfResults>
          <StopEventType>{stop_event_type}</StopEventType>
          <IncludeRealtimeData>true</IncludeRealtimeData>
          <IncludeOperatingDays>false</IncludeOperatingDays>
          <IncludePreviousCalls>false</IncludePreviousCalls>
          <IncludeOnwardCalls>false</IncludeOnwardCalls>
        </Params>
      </StopEventRequest>
    </RequestPayload>
  </ServiceRequest>
</Trias>"""


def _extract_stop_event_results(root: ET.Element) -> list[ET.Element]:
    results = root.findall(f".//{{{TRIAS_NS}}}StopEventResult")
    return results if results else []


def _map_results_to_platforms(results: list[ET.Element]) -> list[dict[str, object]]:
    platforms: dict[str, dict[str, object]] = {}

    for result in results:
        stop_event = result.find(f"{{{TRIAS_NS}}}StopEvent")
        if stop_event is None:
            continue

        call_at_stop = stop_event.find(f"{{{TRIAS_NS}}}ThisCall/{{{TRIAS_NS}}}CallAtStop")
        if call_at_stop is None:
            continue

        service_departure = call_at_stop.find(f"{{{TRIAS_NS}}}ServiceDeparture")
        service_arrival = call_at_stop.find(f"{{{TRIAS_NS}}}ServiceArrival")

        if service_departure is None and service_arrival is None:
            continue

        event_node = service_departure or service_arrival
        planned_time = _text_of(event_node.find(f"{{{TRIAS_NS}}}TimetabledTime"))
        real_time = _text_of(event_node.find(f"{{{TRIAS_NS}}}EstimatedTime"))

        if not planned_time:
            continue

        service = stop_event.find(f"{{{TRIAS_NS}}}Service")
        line_name = _text_of(service.find(f"{{{TRIAS_NS}}}PublishedLineName"))
        if not line_name:
            line_name = _text_of(service.find(f"{{{TRIAS_NS}}}PublishedServiceName"))
        if not line_name:
            line_name = _text_of(service.find(f"{{{TRIAS_NS}}}LineRef")) or "—"

        platform_label = _text_of(call_at_stop.find(f"{{{TRIAS_NS}}}PlannedBay")) or ""
        platform_type = "rail"
        platform_name = platform_label

        if platform_label.startswith("Gleis"):
            platform_name = platform_label[len("Gleis") :].strip()
        elif platform_label.startswith("Bstg."):
            platform_type = "bus"
            platform_name = platform_label[len("Bstg.") :].strip()
        elif platform_label:
            platform_name = platform_label

        key = f"{platform_type}:{platform_name or 'unknown'}"
        if key not in platforms:
            platforms[key] = {
                "platform": {"type": platform_type, "name": platform_name or ""},
                "departures": [],
            }

        direction = _text_of(service.find(f"{{{TRIAS_NS}}}DestinationText")) or "—"
        departure = {
            "lineName": line_name,
            "direction": [direction] if direction != "—" else [],
            "plannedTime": planned_time,
            "realTime": real_time,
            "vehicleType": _text_of(service.find(f"{{{TRIAS_NS}}}Mode/{{{TRIAS_NS}}}PtMode")) or "",
        }
        platforms[key]["departures"].append(departure)

    output = []
    for platform_entry in platforms.values():
        platform_entry["departures"] = sorted(
            platform_entry["departures"],
            key=lambda item: item.get("plannedTime") or "",
        )
        output.append(platform_entry)

    output.sort(key=lambda item: (item["platform"]["type"], item["platform"]["name"]))
    return output


def _text_of(node: ET.Element | None) -> str | None:
    if node is None:
        return None

    text = (node.text or "").strip()
    if text:
        return text

    for child in node:
        child_text = _text_of(child)
        if child_text:
            return child_text

    return None


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


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
