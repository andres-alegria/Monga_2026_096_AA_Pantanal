/* ============================================================
   Editable-PDF extractor — run in the browser on a figure page
   opened as  ?fig=N&pdf=1  (stills frozen, desktop layout).
   window.__extract() returns ExtendScript draw calls that are
   executed after tools/editable_pdf_prelude.jsx in Illustrator:
   - paragraphs/captions/notes -> area type frames
   - small labels (dial, chips, chart) -> point type
   - videos (as stills) and GBIF jpgs -> placed + embedded images
   - locator globe / logomark SVGs -> vector imports
   ============================================================ */

window.__extract = async function () {
  await document.fonts.ready;
  const params = new URLSearchParams(location.search);
  const fig = params.get("fig");
  const sec = document.getElementById("figure-" + fig);
  const base = sec.getBoundingClientRect();
  const out = [];
  const n2 = (v) => Math.round(v * 100) / 100;

  /* ---- helpers ---- */
  const hexOf = (c) => {
    const m = c.match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?\)/);
    if (!m) return null;
    const h = [1, 2, 3].map((i) => Math.round(+m[i]).toString(16).padStart(2, "0")).join("");
    let a = 100;
    if (m[4] !== undefined) a = m[4].endsWith("%") ? Math.round(parseFloat(m[4])) : Math.round(parseFloat(m[4]) * 100);
    return { h, a };
  };
  const esc = (s) => s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');

  const mctx = document.createElement("canvas").getContext("2d");
  const metrics = (cs) => {
    mctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const m = mctx.measureText("Hgj²");
    return { a: m.fontBoundingBoxAscent, d: m.fontBoundingBoxDescent };
  };

  /* webfonts load 300-600 only, so a computed 700 renders as SemiBold */
  const fontKey = (cs) => {
    const w = parseInt(cs.fontWeight) || 400;
    if (/rowan/i.test(cs.fontFamily)) return w >= 500 ? "rowan500" : "rowan400";
    if (w <= 300) return "ps300";
    if (w < 500) return "ps400";
    if (w < 600) return "ps500";
    return "ps600";
  };

  const mkRun = (text, el) => {
    const cs = getComputedStyle(el);
    const size = parseFloat(cs.fontSize);
    const ls = parseFloat(cs.letterSpacing);
    return { t: text, f: fontKey(cs), s: n2(size), c: hexOf(cs.color).h,
             tr: isNaN(ls) ? 0 : Math.round((ls / size) * 1000) };
  };

  const runsOf = (el) => {
    const runs = [];
    (function walk(node, styleEl) {
      node.childNodes.forEach((c) => {
        if (c.nodeType === 3) {
          const t = c.textContent.replace(/\s+/g, " ");
          if (t.trim()) runs.push(mkRun(t, styleEl));
        } else if (c.nodeType === 1) {
          const tg = c.tagName.toLowerCase();
          if (tg === "img" || tg === "svg" || c.classList.contains("sw")) return;
          walk(c, c);
        }
      });
    })(el, el);
    if (runs.length) {
      runs[0].t = runs[0].t.replace(/^ /, "");
      runs[runs.length - 1].t = runs[runs.length - 1].t.replace(/ $/, "");
    }
    return runs;
  };
  const runJs = (runs) =>
    "[" + runs.map((r) => `["${esc(r.t)}","${r.f}",${r.s},"${r.c}",${r.tr}]`).join(",") + "]";
  const baseIdx = (runs) => {
    let bi = 0;
    runs.forEach((r, i) => { if (r.t.length > runs[bi].t.length) bi = i; });
    return bi;
  };

  /* ---- emitters ---- */
  const emitArea = (el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const padL = parseFloat(cs.paddingLeft), padR = parseFloat(cs.paddingRight);
    const padT = parseFloat(cs.paddingTop), padB = parseFloat(cs.paddingBottom);
    const w = el.clientWidth - padL - padR;
    const lead = parseFloat(cs.lineHeight);
    const m = metrics(cs);
    const half = Math.max(0, (lead - (m.a + m.d)) / 2);
    const x = r.left - base.left + el.clientLeft + padL;
    const y = r.top - base.top + el.clientTop + padT + half;
    const h = el.clientHeight - padT - padB + lead; /* one spare line against reflow */
    const runs = runsOf(el);
    if (!runs.length) return;
    const align = cs.textAlign === "center" ? "C" : cs.textAlign === "right" ? "R" : "L";
    out.push(`AR(${n2(x)},${n2(y)},${n2(w + 2)},${n2(h)},${n2(lead)},"${align}",${baseIdx(runs)},${runJs(runs)});`);
  };

  const emitPoint = (target, styleEl, anchor) => {
    const range = document.createRange();
    if (target.nodeType === 3) range.selectNode(target); else range.selectNodeContents(target);
    const rects = [...range.getClientRects()].filter((q) => q.width > 0 && q.height > 0);
    if (!rects.length) return;
    const cs = getComputedStyle(styleEl);
    const m = metrics(cs);
    const r = rects[0];
    const baseline = r.top - base.top + (r.height - (m.a + m.d)) / 2 + m.a;
    const left = Math.min(...rects.map((q) => q.left));
    const right = Math.max(...rects.map((q) => q.right));
    const x = anchor === "C" ? (left + right) / 2 - base.left
            : anchor === "R" ? right - base.left : left - base.left;
    const runs = target.nodeType === 3
      ? [mkRun(target.textContent.replace(/\s+/g, " ").trim(), styleEl)]
      : runsOf(styleEl);
    if (!runs.length) return;
    out.push(`P(${n2(x)},${n2(baseline)},"${anchor}",${baseIdx(runs)},${runJs(runs)});`);
  };

  const emitBox = (el) => {
    const cs = getComputedStyle(el);
    const bg = hexOf(cs.backgroundColor);
    const bw = parseFloat(cs.borderTopWidth) || 0;
    const bc = bw ? hexOf(cs.borderTopColor) : null;
    const hasBg = bg && bg.a > 0;
    if (!hasBg && !bc) return;
    const r = el.getBoundingClientRect();
    const rad = Math.min(parseFloat(cs.borderTopLeftRadius) || 0, r.height / 2, r.width / 2);
    out.push(`R(${n2(r.left - base.left)},${n2(r.top - base.top)},${n2(r.width)},${n2(r.height)},"${hasBg ? bg.h : ""}","${bc ? bc.h : ""}",${bw ? n2(bw) : 0},${n2(rad)},${hasBg ? bg.a : 100});`);
  };

  const emitChart = (svg) => {
    const sr = svg.getBoundingClientRect();
    const s = sr.width / 560; /* viewBox 0 0 560 300 */
    const ox = sr.left - base.left, oy = sr.top - base.top;
    [...svg.children].forEach((e) => {
      const tag = e.tagName.toLowerCase();
      const g = (a) => parseFloat(e.getAttribute(a));
      if (tag === "line") {
        const dash = (e.getAttribute("stroke-dasharray") || "").split(/[\s,]+/)
          .filter(Boolean).map((v) => n2(v * s));
        const sw = g("stroke-width");
        out.push(`L(${n2(ox + g("x1") * s)},${n2(oy + g("y1") * s)},${n2(ox + g("x2") * s)},${n2(oy + g("y2") * s)},"${e.getAttribute("stroke").slice(1)}",${n2(isNaN(sw) ? s : sw * s)},[${dash}],100);`);
      } else if (tag === "rect") {
        out.push(`R(${n2(ox + g("x") * s)},${n2(oy + g("y") * s)},${n2(g("width") * s)},${n2(g("height") * s)},"${e.getAttribute("fill").slice(1)}","",0,${n2((g("rx") || 0) * s)},100);`);
      } else if (tag === "text") {
        const anchor = { end: "R", middle: "C" }[e.getAttribute("text-anchor")] || "L";
        const w = +(e.getAttribute("font-weight") || 400);
        const run = { t: e.textContent, f: w >= 600 ? "ps600" : "ps400",
                      s: n2(g("font-size") * s), c: e.getAttribute("fill").slice(1), tr: 0 };
        out.push(`P(${n2(ox + g("x") * s)},${n2(oy + g("y") * s)},"${anchor}",0,${runJs([run])});`);
      }
    });
  };

  const emitCallout = (co) => {
    const frame = co.parentElement;
    const fr = frame.getBoundingClientRect();
    co.querySelectorAll(".dot").forEach((d) => {
      const r = d.getBoundingClientRect();
      const cs = getComputedStyle(d);
      const bw = parseFloat(cs.borderTopWidth);
      out.push(`CI(${n2(r.left + r.width / 2 - base.left)},${n2(r.top + r.height / 2 - base.top)},${n2((r.width - bw) / 2)},"${hexOf(cs.backgroundColor).h}","${hexOf(cs.borderTopColor).h}",${n2(bw)});`);
    });
    co.querySelectorAll(".line").forEach((ln) => {
      const cs = getComputedStyle(ln);
      const x0 = fr.left + (parseFloat(ln.style.left) / 100) * fr.width - base.left;
      const y0 = fr.top + (parseFloat(ln.style.top) / 100) * fr.height - base.top;
      const len = parseFloat(cs.width);
      const tm = new DOMMatrix(cs.transform);
      const ang = Math.atan2(tm.b, tm.a);
      out.push(`L(${n2(x0)},${n2(y0)},${n2(x0 + len * Math.cos(ang))},${n2(y0 + len * Math.sin(ang))},"${hexOf(cs.backgroundColor).h}",${n2(parseFloat(cs.height))},[],100);`);
    });
    co.querySelectorAll(".box").forEach((bx) => { emitBox(bx); emitArea(bx); });
  };

  /* ---- walk the figure in DOM (= paint) order ---- */
  const consumed = new Set();
  const consume = (el) => el.querySelectorAll("*").forEach((d) => consumed.add(d));
  const names = { 1: "FloodPulse", 2: "FloodFire2020", 3: "Bioacoustics" };

  out.push(`D(${n2(base.width)},${n2(base.height)});`);

  sec.querySelectorAll("*").forEach((el) => {
    if (consumed.has(el)) return;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity === 0) {
      consume(el); return;
    }
    const cl = el.classList;
    const tag = el.tagName.toLowerCase();

    if (cl.contains("playbtn") || tag === "input") { consume(el); return; }
    if (cl.contains("callout")) { emitCallout(el); consume(el); return; }

    if (tag === "img") {
      const r = el.getBoundingClientRect();
      const src = el.getAttribute("src");
      if (src.endsWith(".svg")) {
        out.push(`SV("${src}",${n2(r.left - base.left)},${n2(r.top - base.top)},${n2(r.width)},${n2(r.height)});`);
      } else {
        const rad = parseFloat(cs.borderRadius) ||
                    parseFloat(getComputedStyle(el.parentElement).borderRadius) || 0;
        out.push(`IM("${src}",${n2(r.left - base.left)},${n2(r.top - base.top)},${n2(r.width)},${n2(r.height)},${n2(rad)});`);
      }
      return;
    }
    if (cl.contains("date-chip")) {
      const r = el.getBoundingClientRect();
      out.push(`RT(${n2(r.left - base.left)},${n2(r.top - base.top)},${n2(r.width)},${n2(r.height)},8,"${hexOf(cs.backgroundColor).h}");`);
      emitPoint(el, el, "C");
      consume(el); return;
    }
    if (cl.contains("month-cell")) {
      if (cl.contains("active")) emitBox(el);
      emitPoint(el, el, "C");
      consume(el); return;
    }
    if (cl.contains("seg")) { emitBox(el); return; }
    if (cl.contains("season-label")) { emitPoint(el, el, "L"); consume(el); return; }
    if (cl.contains("item") && el.parentElement.classList.contains("legend")) {
      el.querySelectorAll(".sw").forEach(emitBox);
      const tn = [...el.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim());
      if (tn) emitPoint(tn, el, "L");
      consume(el); return;
    }
    if (cl.contains("chip")) { emitBox(el); emitPoint(el, el, "L"); consume(el); return; }
    if (cl.contains("taxon") || cl.contains("count")) { emitPoint(el, el, "L"); consume(el); return; }
    if (tag === "svg") { emitChart(el); consume(el); return; }
    if (cl.contains("chart-block")) { emitBox(el); return; } /* then descend */
    if (tag === "li") {
      const r = el.getBoundingClientRect();
      const m = metrics(cs);
      const lead = parseFloat(cs.lineHeight);
      const bl = r.top - base.top + (lead - (m.a + m.d)) / 2 + m.a;
      const mk = hexOf(getComputedStyle(el, "::marker").color) || { h: "92a3a0" };
      out.push(`P(${n2(r.left - base.left - 7)},${n2(bl)},"R",0,[["•","ps400",${n2(parseFloat(cs.fontSize))},"${mk.h}",0]]);`);
      emitArea(el);
      consume(el); return;
    }
    if (tag === "h2" || tag === "p" || tag === "figcaption") { emitArea(el); consume(el); return; }
  });

  out.push(`FIN("2026_096_Fig${fig}_${names[fig]}_va");`);
  return out.join("\n");
};
