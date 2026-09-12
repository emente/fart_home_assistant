const SLATE_DARK = '#0f172a';

// Line colors ported from the original F.A.R.T. project
// (https://github.com/demartinomarco/F.A.R.T./blob/master/src/lib/styles/lines.ts)
const LINE_STYLES = {
  S1: { background: '#008256', text: '#fff' },
  S11: { background: '#008256', text: '#fff' },
  S12: { background: '#008256', text: '#fff' },

  S2: { background: '#aa70b8', text: SLATE_DARK },

  S3: { background: '#ffdc01', text: SLATE_DARK },

  S31: { background: '#007870', text: '#fff' },
  S32: { background: '#007870', text: '#fff' },
  S33: { background: '#824391', text: '#fff' },

  S4: { background: '#9f184c', text: '#fff' },

  S41: { background: '#bed730', text: SLATE_DARK },
  S42: { background: '#00728d', text: '#fff' },

  S5: { background: '#f59795', text: SLATE_DARK },
  S51: { background: '#f59795', text: SLATE_DARK },
  S52: { background: '#f59795', text: SLATE_DARK },

  S6: { background: '#01bdf2', text: SLATE_DARK },

  S7: { background: '#fff101', text: SLATE_DARK },
  S71: { background: '#fff101', text: SLATE_DARK },

  S8: { background: '#6e6928', text: '#fff' },
  S81: { background: '#6e6928', text: '#fff' },

  S9: { background: '#7fc241', text: SLATE_DARK },

  1: { background: '#d61a20', text: '#fff' },
  2: { background: '#0072bc', text: '#fff' },
  3: { background: '#937138', text: '#fff' },
  4: { background: '#fec210', text: SLATE_DARK },
  5: { background: '#15c0f2', text: SLATE_DARK },
  6: { background: '#80c342', text: SLATE_DARK },
  7: { background: '#58595b', text: '#fff' },
  8: { background: '#f7931d', text: SLATE_DARK },
  10: { background: '#a4d7bb', text: SLATE_DARK }
};

function getLineStyle(lineName, platformType) {
  const name = String(lineName || '');

  if (/^(ICE|IC|EC|ECE)/i.test(name)) {
    return { background: '#d61a20', text: '#fff' };
  }

  if (/^(NJ|EN)/i.test(name)) {
    return { background: '#001f52', text: '#fff' };
  }

  if (name.startsWith('TGV')) {
    return { background: '#224980', text: '#fff' };
  }

  if (/^(RE|RB|IRE|MEX)/i.test(name)) {
    return { background: '#ffd600', text: SLATE_DARK };
  }

  if (platformType === 'bus') {
    return { background: '#882287', text: '#fff' };
  }

  return LINE_STYLES[name] || { background: SLATE_DARK, text: '#fff' };
}

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

        const lineStyle = getLineStyle(nextDeparture.lineName, platformEntry.platform.type);

        return `
          <div class="platform-row">
            <div class="platform-name">${this.formatPlatformLabel(platformEntry.platform)}</div>
            <div class="platform-content">
              <div class="line-and-time">
                <span class="line-badge" style="background:${lineStyle.background}; color:${lineStyle.text};">${nextDeparture.lineName || '—'}</span>
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

            const lineStyle = getLineStyle(departure.lineName, platformEntry.platform.type);

            return `
              <div class="expanded-row">
                <div class="departure-main">
                  <div class="expanded-line-badge" style="background:${lineStyle.background}; color:${lineStyle.text};">${departure.lineName || '—'}</div>
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
          background: var(--ha-card-background, var(--card-background-color, #ffffff));
          border: 1px solid var(--divider-color, rgba(0,0,0,0.08));
          border-radius: 18px;
          box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
          padding: 10px 14px;
          cursor: pointer;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
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
          font-size: 1rem;
          font-weight: 700;
          line-height: 1.2;
        }

        .status {
          font-size: 0.75rem;
          color: var(--secondary-text-color, #6b7280);
          white-space: nowrap;
        }

        .body {
          display: flex;
          flex-direction: column;
        }

        .platform-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 5px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }

        .platform-row:last-child {
          border-bottom: none;
        }

        .platform-name {
          flex: 0 0 auto;
          font-size: 0.78rem;
          font-weight: 700;
          text-transform: uppercase;
          color: var(--secondary-text-color, #6b7280);
        }

        .platform-content {
          flex: 1 1 auto;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          min-width: 0;
          line-height: 1.2;
        }

        .line-and-time {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }

        .line-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 24px;
          height: 20px;
          padding: 0 6px;
          border-radius: 5px;
          font-size: 0.78rem;
          font-weight: 800;
          line-height: 1;
          box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
        }

        .time {
          font-size: 0.85rem;
          font-weight: 700;
          color: var(--primary-color, #0f766e);
        }

        .meta {
          flex: 0 0 auto;
          font-size: 0.68rem;
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
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 50%;
          background: transparent;
          cursor: pointer;
          color: var(--secondary-text-color, #6b7280);
          transition: background-color 0.15s ease-in-out;
        }

        .close-button:hover,
        .close-button:focus-visible {
          background: rgba(128, 128, 128, 0.16);
        }

        .close-button svg {
          display: block;
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
          background: var(--secondary-background-color, rgba(148, 163, 184, 0.04));
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
            <button class="close-button" type="button" aria-label="Close">
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path fill="currentColor" d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"></path>
              </svg>
            </button>
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
