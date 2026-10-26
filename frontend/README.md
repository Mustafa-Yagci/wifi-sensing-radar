# WiFi Sensing Radar — Frontend Interface

Modern, real-time web dashboard for environmental Wi-Fi sensing and RF perturbation monitoring. Built with React 19 and Vite.

---

## 🎯 Architecture & Design

The frontend provides real-time telemetry visualization driven by high-frequency Wi-Fi signal measurements:

- **Live Signal Monitor (`monitor.html` / `index.html`):**
  - **Dynamic Radar Field:** High-performance HTML5 Canvas renderer showing real-time environmental perturbations, baseline variance, and receiver status.
  - **Spectral & Fresnel Panels:** Real-time metrics for TX-RX distance estimation (Log-Distance Path Loss), Fresnel zone perturbation percentage, and spectral frequency analysis (dominant Hz, entropy).
  - **Audio Alerts & Controls:** Synthesized Web Audio API alarms on threshold-exceeding environmental motion, with baseline re-calibration controls.
- **WebSocket Streaming (`useRadarWebSocket.js`):**
  - Auto-reconnecting binary/JSON WebSocket stream (`/ws`).
  - Graceful polling fallback (`/api/poll`) with exponential backoff on disconnects.
  - Sub-150ms latency between driver reads and canvas redraws.
- **Components:**
  - `App.jsx`: Main telemetry orchestration, audio synthesis, and status cards.
  - `components/CsiWaterfall.jsx`: Subcarrier amplitude matrix visualizer for CSI hardware.
  - `components/EnvironmentPanels.jsx`: Spectral statistics, multi-link metrics, and event log journal.

---

## 🚀 Development & Build

### Prerequisites
- Node.js 18+ (tested with Node 20 / 22)
- npm 9+

### Scripts

```bash
# Install dependencies
npm install

# Start development server (with HMR)
npm run dev

# Run test suite
npm test

# Run ESLint validation
npm run lint

# Build production bundle (outputs to dist/)
npm run build
```

Production builds are output directly to `dist/` and served statically by the FastAPI/Starlette backend (`server.py`).
