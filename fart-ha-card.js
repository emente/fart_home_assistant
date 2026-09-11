class FartHaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._expanded = false;
  }

  setConfig(config) {
    this._config = {
      entity: config.entity || '',
      title: config.title || 'FART',
      station_name: config.station_name || '',
      limit: Number.isInteger(config.limit) ? config.limit : 10,
      refresh_seconds: Number.isInteger(config.refresh_seconds) ? config.refresh_seconds : 15
    };
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  getEntityState() {
    if (!this._hass || !this._config.entity) {
      return null;
    }

    return this._hass.states[this._config.entity] || null;
  }

  getData() {
    const state = this.getEntityState();
    if (!state) {
      return null;
    }

    const attributes = state.attributes || {};
    const platforms = Array.isArray(attributes.platforms) ? attributes.platforms : [];

    return {
      stationName: attributes.station_name || attributes.stationName || state.name || 'FART',
      cityName: attributes.city_name || attributes.cityName || '',
      platforms,
      fetchedAt: attributes.fetched_at || attributes.fetchedAt || state.last_updated,
      unavailable: state.state === 'unavailable'
    };
  }

  formatTime(dateString) {
    if (!dateString) {
      return '--:--';
    }

    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
      return '--:--';
    }

    return new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  formatPlatformLabel(platform) {
    if (!platform || !platform.name) {
      return 'Platform';
    }

    if (platform.type === 'rail') {
      return `Gleis ${platform.name}`;
    }

    if (platform.type === 'bus') {
      return `Bstg. ${platform.name}`;
    }

    return platform.name;
  }

  buildCompactRows(data) {
    if (!data || !Array.isArray(data.platforms) || data.platforms.length === 0) {
      return '<div class="empty-message">No platform data available.</div>';
    }

    return data.platforms
      .map((platformEntry) => {
        const departures = Array.isArray(platformEntry.departures) ? platformEntry.departures : [];
        const nextDeparture = departures[0];

        if (!nextDeparture) {
          return `
            <div class="platform-row empty">
              <div class="platform-name">${this.formatPlatformLabel(platformEntry.platform)}</div>
              <div class="platform-meta">No departures</div>
            </div>
          `;
        }

        const realTime = nextDeparture.realTime || nextDeparture.plannedTime;
        const delayMin = nextDeparture.realTime
          ? Math.max(
              0,
              Math.round(
                (new Date(nextDeparture.realTime).getTime() - new Date(nextDeparture.plannedTime).getTime()) / 60000
              )
            )
          : 0;

        return `
          <div class="platform-row">
            <div class="platform-name">${this.formatPlatformLabel(platformEntry.platform)}</div>
            <div class="platform-content">
              <div class="line-and-time">
                <span class="line">${nextDeparture.lineName || '—'}</span>
                <span class="time">${this.formatTime(realTime)}</span>
              </div>
              <div class="meta">${delayMin > 0 ? `+${delayMin} min` : 'on time'}</div>
            </div>
          </div>
        `;
      })
      .join('');
  }

  buildExpandedRows(data) {
    if (!data || !Array.isArray(data.platforms) || data.platforms.length === 0) {
      return '<div class="expanded-empty">No departures available.</div>';
    }

    const limit = Math.max(1, this._config.limit || 10);

    const columns = data.platforms
      .map((platformEntry) => {
        const departures = Array.isArray(platformEntry.departures) ? platformEntry.departures : [];
        const rows = departures
          .slice(0, limit)
          .map((departure) => {
            const realTime = departure.realTime || departure.plannedTime;
            const delayMin = departure.realTime
              ? Math.max(
                  0,
                  Math.round(
                    (new Date(departure.realTime).getTime() - new Date(departure.plannedTime).getTime()) / 60000
                  )
                )
              : 0;

            const direction = Array.isArray(departure.direction) && departure.direction.length
              ? departure.direction.join(', ')
              : '—';

            return `
              <div class="expanded-row">
                <div class="departure-main">
                  <div class="expanded-line-badge">${departure.lineName || '—'}</div>
                  <div class="expanded-direction">${direction}</div>
                </div>
                <div class="expanded-meta">
                  <span class="expanded-time">${this.formatTime(realTime)}</span>
                  <span class="expanded-delay">${delayMin > 0 ? `+${delayMin} min` : 'on time'}</span>
                </div>
              </div>
            `;
          })
          .join('');

        return `
          <div class="expanded-platform">
            <div class="expanded-header">${this.formatPlatformLabel(platformEntry.platform)}</div>
            <div class="expanded-list">${rows || '<div class="expanded-empty">No departures</div>'}</div>
          </div>
        `;
      })
      .join('');

    return `<div class="expanded-grid">${columns}</div>`;
  }

  render() {
    const data = this.getData();
    const title = this._config.title || this._config.station_name || data?.stationName || 'Departures';
    const subtitle = this._config.station_name || data?.stationName || 'Unknown stop';
    const rows = this.buildCompactRows(data);
    const expandedRows = this.buildExpandedRows(data);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--ha-card-header-font-family, sans-serif);
          color: var(--primary-text-color, #1d1d1f);
        }

        * { box-sizing: border-box; }

        .card {
          background: var(--ha-card-background, #ffffff);
          border: 1px solid var(--divider-color, rgba(0,0,0,0.08));
          border-radius: 18px;
          box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
          padding: 16px;
          cursor: pointer;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }

        .title-wrap {
          display: flex;
          flex-direction: column;
        }

        .eyebrow {
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--secondary-text-color, #6b7280);
        }

        h2 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 700;
        }

        .status {
          font-size: 0.75rem;
          color: var(--secondary-text-color, #6b7280);
          white-space: nowrap;
        }

        .body {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .platform-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }

        .platform-row:last-child {
          border-bottom: none;
        }

        .platform-name {
          font-size: 0.78rem;
          font-weight: 700;
          text-transform: uppercase;
          color: var(--secondary-text-color, #6b7280);
        }

        .platform-content {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          text-align: right;
        }

        .line-and-time {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .line {
          font-size: 1.05rem;
          font-weight: 800;
          color: var(--primary-text-color, #111827);
        }

        .time {
          font-size: 0.92rem;
          font-weight: 700;
          color: var(--primary-color, #0f766e);
        }

        .meta {
          font-size: 0.72rem;
          color: var(--secondary-text-color, #6b7280);
        }

        .loader, .error, .empty-message {
          padding: 12px 0;
          font-size: 0.85rem;
          color: var(--secondary-text-color, #6b7280);
        }

        .error {
          color: var(--error-color, #b91c1c);
        }

        .modal-backdrop {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(15, 23, 42, 0.6);
          padding: 24px;
          z-index: 9999;
        }

        .modal-backdrop.open {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .modal {
          width: min(900px, 100%);
          max-height: 80vh;
          overflow: auto;
          background: var(--card-background-color, #ffffff);
          border-radius: 20px;
          padding: 20px;
          box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        .modal-header h3 {
          margin: 0;
          font-size: 1.1rem;
        }

        .close-button {
          border: none;
          background: transparent;
          font-size: 0.9rem;
          cursor: pointer;
          color: var(--secondary-text-color, #6b7280);
        }

        .expanded-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 20px;
          align-items: start;
        }

        .expanded-platform {
          border: 1px solid var(--divider-color, rgba(0,0,0,0.08));
          border-radius: 12px;
          padding: 12px;
          background: rgba(148, 163, 184, 0.04);
        }

        .expanded-header {
          font-size: 0.78rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--secondary-text-color, #6b7280);
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.08));
          padding-bottom: 8px;
          margin-bottom: 8px;
        }

        .expanded-list {
          display: flex;
          flex-direction: column;
        }

        .expanded-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 8px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }

        .expanded-row:last-child {
          border-bottom: none;
        }

        .departure-main {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
        }

        .expanded-line-badge {
          width: 34px;
          height: 24px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 800;
          color: #fff;
          background: var(--primary-color, #0f766e);
          box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
        }

        .expanded-direction {
          font-size: 0.8rem;
          color: var(--secondary-text-color, #6b7280);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .expanded-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          font-size: 0.8rem;
          min-width: 78px;
        }

        .expanded-time {
          font-weight: 700;
          color: var(--primary-color, #0f766e);
        }

        .expanded-delay {
          color: var(--secondary-text-color, #6b7280);
        }

        .expanded-empty {
          font-size: 0.8rem;
          color: var(--secondary-text-color, #6b7280);
        }

        @media (max-width: 600px) {
          .header {
            align-items: flex-start;
            flex-direction: column;
          }

          .platform-row {
            align-items: flex-start;
            flex-direction: column;
          }

          .platform-content {
            align-items: flex-start;
            text-align: left;
          }

          .expanded-row {
            grid-template-columns: 1fr;
          }

          .expanded-meta {
            align-items: flex-start;
          }
        }
      </style>

      <div class="card" tabindex="0" role="button" aria-label="Open departure schedule">
        <div class="header">
          <div class="title-wrap">
            <div class="eyebrow">FART</div>
            <h2>${title}</h2>
          </div>
          <div class="status">${subtitle}</div>
        </div>

        <div class="body">
          ${!this._hass || !this._config.entity
            ? '<div class="error">Set the card entity configuration.</div>'
            : data && data.unavailable
              ? '<div class="error">Entity unavailable.</div>'
              : rows}
        </div>
      </div>

      <div class="modal-backdrop ${this._expanded ? 'open' : ''}">
        <div class="modal" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h3>${title} • ${subtitle}</h3>
            <button class="close-button" type="button">Close</button>
          </div>
          <div>${expandedRows}</div>
        </div>
      </div>
    `;

    const card = this.shadowRoot.querySelector('.card');
    if (card) {
      card.onclick = () => {
        if (data && Array.isArray(data.platforms) && data.platforms.length > 0) {
          this._expanded = true;
          this.render();
        }
      };

      card.onkeydown = (event) => {
        if ((event.key === 'Enter' || event.key === ' ') && data && Array.isArray(data.platforms) && data.platforms.length > 0) {
          event.preventDefault();
          this._expanded = true;
          this.render();
        }
      };
    }

    const closeButton = this.shadowRoot.querySelector('.close-button');
    if (closeButton) {
      closeButton.onclick = (event) => {
        event.stopPropagation();
        this._expanded = false;
        this.render();
      };
    }

    const backdrop = this.shadowRoot.querySelector('.modal-backdrop');
    if (backdrop) {
      backdrop.onclick = (event) => {
        if (event.target === backdrop) {
          this._expanded = false;
          this.render();
        }
      };
    }
  }
}

if (!customElements.get('fart-ha-card')) {
  customElements.define('fart-ha-card', FartHaCard);
}
