This is a custom component including card to display
Karlsruhe KVV depature times. Inspired by https://github.com/demartinomarco/F.A.R.T. hence the name.

## HACS install flow

1. In HACS, add this repository as a custom repository.
2. Install it via HACS.
3. Restart Home Assistant.
4. Open Home Assistant and go Settings -> Integrations
7. Click `Add Integration` and choose `FART`.
8. Select the station from the UI list.
9. Add the following to your Home Assistant `configuration.yaml` to make the custom card load automatically:

```yaml
lovelace:
  resources:
    - url: /local/fart-ha-card.js
      type: module
```

10. Restart Home Assistant again.
11. Open the dashboard editor and add the `FART` card.
