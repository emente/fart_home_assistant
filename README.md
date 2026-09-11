This is a custom component including card to display
Karlsruhe KVV depature times. Inspired by https://github.com/demartinomarco/F.A.R.T. hence the name.

## HACS install flow

1. In HACS, add this repository as a custom repository (category: Integration).
2. Install it via HACS.
3. Restart Home Assistant.
4. Go to Settings -> Devices & services.
5. Click `Add Integration` and choose `FART`.
6. Select the station from the list.
7. A notification appears with the exact card YAML (including the station's entity ID) and a link to your dashboards — open a dashboard, click **+ Add Card** -> **Manual**, and paste it in.

The `fart-ha-card.js` resource is registered automatically by the integration (via `add_extra_js_url`) — there's no need to add it manually under Settings -> Dashboards -> Resources.
