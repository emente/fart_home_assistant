This is a custom component including card to display
Karlsruhe KVV depature times. Inspired by https://github.com/demartinomarco/F.A.R.T. hence the name.

## HACS install flow

1. In HACS, add this repository as a custom repository (category: Integration).
2. Install it via HACS.
3. Restart Home Assistant.
4. Go to Settings -> Devices & services.
5. Click `Add Integration` and choose `FART`.
6. Select the station from the list.
7. A notification appears with setup steps: adding `/fart_files/fart-ha-card.js` as a dashboard resource (one-time, only needed once even with multiple stations) and the exact card YAML (including the station's entity ID) to paste into a dashboard.

The resource only needs adding once:

1. Settings -> Dashboards -> the ⋮ menu (top right) -> Resources.
2. Add Resource -> URL `/fart_files/fart-ha-card.js` -> Resource type `JavaScript Module` -> Create.

(If `Resources` isn't in that menu, enable `Advanced Mode` in your user profile.)
