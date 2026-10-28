/* ============================================================
   Logic only — all editorial content comes from js/content.js.
   ============================================================ */

(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- static text injection ---------- */

  /* solo mode: ?fig=1|2|3 shows a single stand-alone figure (for embeds) */
  const params = new URLSearchParams(location.search);
  /* pdf=1 freezes the page for a static snapshot (stills instead of videos) */
  const pdfMode = params.get("pdf") === "1";
  const solo = params.get("fig");
  if (["1", "2", "3"].includes(solo)) {
    document.body.classList.add("solo");
    document.querySelectorAll("section").forEach((s) => {
      if (s.id !== "figure-" + solo) s.style.display = "none";
    });
  }

  const fillParas = (el, paras) => {
    paras.forEach((t) => {
      const p = document.createElement("p");
      p.textContent = t;
      el.appendChild(p);
    });
  };

  $("pulseHeading").textContent = CONTENT.fig1.heading;
  fillParas($("pulseBody"), CONTENT.fig1.body);
  $("pulseMapTitle").textContent = CONTENT.fig1.mapTitle;
  $("pulseMapPeriod").textContent = CONTENT.fig1.mapTitlePeriod;
  $("pulseOverlay").textContent = CONTENT.fig1.mapOverlay;
  $("seasonLabel").textContent = CONTENT.fig1.wetSeasonLabel;

  $("fireHeading").textContent = CONTENT.fig2.heading;
  fillParas($("fireBody"), CONTENT.fig2.body);
  $("fireMapTitle").textContent = CONTENT.fig2.mapTitle;
  $("chartTitle").textContent = CONTENT.fig2.chart.title;
  $("chartUnit").textContent = CONTENT.fig2.chart.unit;

  $("listenHeading").textContent = CONTENT.fig3.heading;
  fillParas($("listenBody"), CONTENT.fig3.body);
  $("gbifTitle").textContent = CONTENT.fig3.gbifTitle;
  $("gbifCaption").textContent = CONTENT.fig3.gbifCaption;

  ["fig1", "fig2", "fig3"].forEach((k) => {
    $(k + "Sources").textContent = CONTENT[k].sources;
  });

  /* fig 1 cycle panel: lead, body and the stat grid (2 + 1 with divider) */
  $("pulseCycleLead").textContent = CONTENT.fig1.cycleNote.lead;
  $("pulseCycleNote").textContent = CONTENT.fig1.cycleNote.text;
  $("pulseGlobeCaption").textContent = CONTENT.fig1.globeCaption;

  {
    const grid = $("pulseStats");
    const colL = document.createElement("div");
    colL.className = "stat-col";
    const colR = document.createElement("div");
    colR.className = "stat-col right";
    CONTENT.fig1.stats.forEach((s, i) => {
      const d = document.createElement("div");
      d.className = "stat" + (i === 2 ? " tall" : "");
      d.innerHTML = `<span class="stat-num">${s.value}</span><span class="stat-label">${s.label}</span>`;
      (i === 2 ? colR : colL).appendChild(d);
    });
    grid.append(colL, colR);
  }

  /* legend */
  CONTENT.fig2.legend.forEach((it) => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML = `<span class="sw ${it.swatch}"></span>${it.label}`;
    $("fireLegend").appendChild(d);
  });

  /* GBIF small multiples, each with its species + records pill pair */
  CONTENT.fig3.gbifMaps.forEach((m) => {
    const f = document.createElement("figure");
    f.innerHTML = `<img src="${m.img}" alt="GBIF occurrence records: ${m.species}" loading="${pdfMode ? "eager" : "lazy"}">
      <div class="pill-row"><span class="pill pill-light">${m.species}</span><span class="pill pill-dark">${m.records}</span></div>`;
    $("gbifGrid").appendChild(f);
  });

  /* ---------- play / pause buttons ---------- */

  const ICON_PLAY = '<svg viewBox="0 0 16 16"><path d="M4 2.5v11l9-5.5z"/></svg>';
  const ICON_PAUSE = '<svg viewBox="0 0 16 16"><path d="M4 2.5h3v11H4zM9 2.5h3v11H9z"/></svg>';

  function bindPlayButton(btn, video) {
    const refresh = () => { btn.innerHTML = video.paused ? ICON_PLAY : ICON_PAUSE; };
    btn.addEventListener("click", () => { video.paused ? video.play() : video.pause(); });
    video.addEventListener("play", refresh);
    video.addEventListener("pause", refresh);
    refresh();
  }

  /* ============================================================
     Section 1 — monthly flood pulse
     The video holds 12 equal-length month segments, Jan..Dec.
     ============================================================ */

  const pv = $("pulseVideo");
  const monthRow = $("monthRow");
  const monthCells = [];
  let pulseDur = 14.2; // fallback until metadata loads

  CONTENT.fig1.months.forEach((m, i) => {
    const b = document.createElement("button");
    b.className = "month-cell";
    b.textContent = m;
    b.addEventListener("click", () => {
      pv.pause();
      pv.currentTime = (i + 0.5) * (pulseDur / 12);
    });
    monthRow.appendChild(b);
    monthCells.push(b);
  });

  /* rainy-season band segments under the dial */
  function drawSeasonBand() {
    const band = $("seasonBand");
    band.innerHTML = "";
    const w = 100 / 12;
    // merge consecutive wet months into runs for cleaner segments
    const wet = new Set(CONTENT.fig1.wetMonths);
    let run = null;
    for (let i = 0; i < 12; i++) {
      if (wet.has(i)) {
        if (run === null) run = i;
      }
      if ((!wet.has(i) || i === 11) && run !== null) {
        const end = wet.has(i) ? i : i - 1;
        const seg = document.createElement("span");
        seg.className = "seg";
        seg.style.left = run * w + "%";
        seg.style.width = (end - run + 1) * w + "%";
        band.appendChild(seg);
        run = null;
      }
    }
  }
  drawSeasonBand();

  /* callouts over the flood map */
  const calloutEls = CONTENT.fig1.callouts.map((c) => {
    const el = document.createElement("div");
    el.className = "callout";
    const dx = c.boxX - c.x, dy = c.boxY + 4 - c.y;
    const len = Math.sqrt(dx * dx + dy * dy); // in % units of width/height mix; cosmetic only
    el.innerHTML =
      `<span class="dot" style="left:${c.x}%;top:${c.y}%"></span>
       <span class="line" style="left:${c.x}%;top:${c.y}%;width:${len * 0.8}%;
             transform:rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)"></span>
       <div class="box" style="left:${c.boxX}%;top:${c.boxY}%"><b>${c.lead}.</b> ${c.text}</div>`;
    el.style.position = "absolute";
    el.style.inset = "0";
    $("pulseFrame").appendChild(el);
    return { el, months: c.months };
  });

  function updatePulseUI() {
    if (pdfMode) return;
    const m = Math.min(11, Math.floor(pv.currentTime / (pulseDur / 12)));
    monthCells.forEach((c, i) => c.classList.toggle("active", i === m));
    calloutEls.forEach((c) => c.el.classList.toggle("visible", c.months.includes(m)));
  }

  pv.addEventListener("loadedmetadata", () => { pulseDur = pv.duration; updatePulseUI(); });
  pv.addEventListener("timeupdate", updatePulseUI);
  if (!pdfMode) setInterval(updatePulseUI, 200); // timeupdate fires sparsely; keep dial snappy

  bindPlayButton($("pulsePlay"), pv);
  if (!reducedMotion && !pdfMode) {
    // autoplay the seasonal loop (muted); browsers may still block — button covers that
    pv.play().catch(() => {});
  }

  /* ============================================================
     Section 2 — 2020 fire detections over the ecoregion basemap
     Canvas animation fed by assets/fire_days.js (VIIRS, first
     detection day per cell); pacing matches the source video
     (10 days per second).
     ============================================================ */

  const slider = $("fireSlider");
  const chip = $("dateChip");
  const fireCanvas = $("fireCanvas");
  const fctx = fireCanvas.getContext("2d");
  const FD = window.FIRE_DAYS || { w: 660, h: 760, days: {} };
  const DAY_MAX = 366;            // 2020 is a leap year
  const DAYS_PER_SEC = 20;   // animation pace — adjust here
  const fireDays = {};
  Object.keys(FD.days).forEach((d) => {
    fireDays[d] = FD.days[d].split(",").map((s) => parseInt(s, 36));
  });
  const cellW = fireCanvas.width / FD.w;
  const cellH = fireCanvas.height / FD.h;
  let fireDay = 0;                // last day drawn on the canvas
  let scrubbing = false;
  let firePlaying = false;
  let fireRaf = null;
  let dayFloat = 0;
  let lastTs = null;

  /* AP month forms: abbreviate Aug.–Feb., spell out March–July */
  const MONTH_NAMES = ["Jan.", "Feb.", "March", "April", "May", "June",
                       "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];

  function dateFromDay(day) {
    const d = new Date(Date.UTC(2020, 0, Math.max(1, Math.min(DAY_MAX, day))));
    // U.S.-style date, per Mongabay convention
    return MONTH_NAMES[d.getUTCMonth()] + " " + d.getUTCDate() + ", 2020";
  }

  function drawFireRange(from, to) {
    fctx.fillStyle = "#a01313";   // fire red — adjust here
    for (let d = from; d <= to; d++) {
      const cells = fireDays[d];
      if (!cells) continue;
      for (let i = 0; i < cells.length; i++) {
        fctx.fillRect((cells[i] % FD.w) * cellW,
                      Math.floor(cells[i] / FD.w) * cellH, cellW, cellH);
      }
    }
  }

  function setFireDay(day) {
    day = Math.max(0, Math.min(DAY_MAX, Math.round(day)));
    if (day < fireDay) {
      fctx.clearRect(0, 0, fireCanvas.width, fireCanvas.height);
      fireDay = 0;
    }
    drawFireRange(fireDay + 1, day);
    fireDay = day;
    chip.textContent = dateFromDay(Math.max(1, day));
    if (!scrubbing) slider.value = Math.round((day / DAY_MAX) * 1000);
  }

  const fireBtn = $("firePlay");
  function refreshFireBtn() { fireBtn.innerHTML = firePlaying ? ICON_PAUSE : ICON_PLAY; }

  function fireTick(ts) {
    if (!firePlaying) return;
    if (lastTs !== null) {
      dayFloat += ((ts - lastTs) / 1000) * DAYS_PER_SEC;
      if (dayFloat >= DAY_MAX) {
        setFireDay(DAY_MAX);
        pauseFire();
        return;
      }
      if (Math.floor(dayFloat) > fireDay) setFireDay(Math.floor(dayFloat));
    }
    lastTs = ts;
    fireRaf = requestAnimationFrame(fireTick);
  }
  function playFire() {
    dayFloat = fireDay >= DAY_MAX ? 0 : fireDay;   // replay from January
    if (fireDay >= DAY_MAX) setFireDay(0);
    firePlaying = true;
    lastTs = null;
    refreshFireBtn();
    fireRaf = requestAnimationFrame(fireTick);
  }
  function pauseFire() {
    firePlaying = false;
    refreshFireBtn();
    if (fireRaf) cancelAnimationFrame(fireRaf);
  }
  fireBtn.addEventListener("click", () => (firePlaying ? pauseFire() : playFire()));

  slider.addEventListener("input", () => {
    scrubbing = true;
    pauseFire();
    dayFloat = (slider.value / 1000) * DAY_MAX;
    setFireDay(dayFloat);
  });
  slider.addEventListener("change", () => { scrubbing = false; });

  /* the figure loads complete: full-year picture (PDF freezes Sept. 17) */
  setFireDay(pdfMode ? 261 : DAY_MAX);
  refreshFireBtn();

  /* ============================================================
     PDF snapshot mode — freeze a telling frame of each animation
     ============================================================ */

  function swapVideoForStill(video, src) {
    const img = document.createElement("img");
    img.className = "still";
    img.src = src;
    img.alt = video.getAttribute("aria-label") || "";
    video.parentNode.insertBefore(img, video);
    video.remove();
  }

  if (pdfMode) {
    document.body.classList.add("pdf");
    monthCells.forEach((c, i) => c.classList.toggle("active", i === 6)); // July
    calloutEls.forEach((c) => c.el.classList.toggle("visible", c.months.includes(6)));
    swapVideoForStill(pv, "assets/pdf_flood_july.jpg");
    const ph = params.get("ph");
    if (ph) {
      const st = document.createElement("style");
      st.textContent = `@page { size: 1100px ${parseInt(ph, 10)}px; margin: 0; }`;
      document.head.appendChild(st);
    }
  }

  /* ============================================================
     Annual flooded-area bar chart (SVG, no libraries)
     Styling follows the v1 artboard: teal bars, flat bottoms,
     rounded tops, annotation leaders, no average line.
     ============================================================ */

  function drawChart() {
    const svg = $("floodChart");
    const cfg = CONTENT.fig2.chart;
    const W = 560, H = 450;
    const M = { top: 42, right: 8, bottom: 30, left: 36 };
    const iw = W - M.left - M.right, ih = H - M.top - M.bottom;
    const n = cfg.values.length;
    const maxV = 60000; // axis ceiling just above the 2011 peak — adjust here
    const gap = 4.6;
    const bw = (iw - gap * (n - 1)) / n;
    const y = (v) => M.top + ih * (1 - v / maxV);
    const FS = 20;      // label size in viewBox units (~1rem rendered) — adjust here
    const ns = "http://www.w3.org/2000/svg";
    const el = (tag, attrs, text) => {
      const e = document.createElementNS(ns, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      if (text != null) e.textContent = text;
      return e;
    };

    /* y grid: hairlines at 20/40/60 with labels, a firmer baseline at 0 */
    [0, 20000, 40000, 60000].forEach((v) => {
      svg.appendChild(el("line", {
        x1: M.left, x2: W - M.right, y1: y(v), y2: y(v),
        /* horizontal gridlines only — adjust here */
        stroke: "#788986", "stroke-width": v === 0 ? 1.2 : 0.6
      }));
      if (v > 0) svg.appendChild(el("text", {
        x: M.left - 8, y: y(v) + FS * 0.32, "text-anchor": "end",
        "font-size": FS, fill: "#738b87"
      }, String(v / 1000)));
    });

    /* bars: flat bottom on the baseline, rounded tops */
    const barPath = (x, yT, w, h, r) => {
      r = Math.min(r, w / 2, h);
      return `M${x},${yT + h} L${x},${yT + r} Q${x},${yT} ${x + r},${yT} ` +
             `L${x + w - r},${yT} Q${x + w},${yT} ${x + w},${yT + r} L${x + w},${yT + h} Z`;
    };
    cfg.years.forEach((yr, i) => {
      const v = cfg.values[i];
      const x = M.left + i * (bw + gap);
      svg.appendChild(el("path", {
        d: barPath(x, y(v), bw, M.top + ih - y(v), 2.6),
        /* bar colors — adjust here: flood teal, 2011 deep, 2020 fire red */
        fill: yr === 2020 ? "#a01313" : (cfg.annotations[yr] ? "#74aab1" : "#8fd0cd")
      }));
      /* x labels every 5 years + 2020, all muted (last one kept inside the viewBox) */
      if (yr % 5 === 0 || yr === 2020) {
        svg.appendChild(el("text", {
          x: Math.min(x + bw / 2, W - 26), y: H - 6, "text-anchor": "middle",
          "font-size": FS, fill: "#738b87"
        }, String(yr)));
      }
    });

    /* annotations with vertical leader lines */
    const barCx = (i) => M.left + i * (bw + gap) + bw / 2;

    const i2011 = cfg.years.indexOf(2011);
    svg.appendChild(el("text", {
      x: barCx(i2011), y: 18, "text-anchor": "middle",
      "font-size": FS, fill: "#74aab1"
    }, cfg.annotations[2011][0]));
    svg.appendChild(el("line", {
      x1: barCx(i2011), x2: barCx(i2011), y1: 26, y2: y(cfg.values[i2011]) - 5,
      stroke: "#74aab1", "stroke-width": 1.2
    }));

    const i2020 = cfg.years.indexOf(2020);
    cfg.annotations[2020].forEach((lineTxt, li) => {
      svg.appendChild(el("text", {
        x: W - M.right, y: M.top + 26 + li * (FS * 1.15), "text-anchor": "end",
        "font-size": FS, "font-weight": 500, fill: "#a01313"
      }, lineTxt));
    });
    svg.appendChild(el("line", {
      x1: barCx(i2020), x2: barCx(i2020),
      y1: M.top + 26 + cfg.annotations[2020].length * (FS * 1.15) + 2,
      y2: y(cfg.values[i2020]) - 5,
      stroke: "#a01313", "stroke-width": 1.2
    }));
  }
  drawChart();
})();
