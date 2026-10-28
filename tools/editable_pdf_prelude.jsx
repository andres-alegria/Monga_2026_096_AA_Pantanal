/* ============================================================
   Editable-PDF prelude — ExtendScript (ES3) helpers executed in
   Illustrator before the draw calls that tools/editable_pdf_extract.js
   generates in the browser. Builds each figure as a NEW document
   (never touches other open documents), saves an Illustrator-
   editable PDF into pdf/ and a QA PNG, then closes.
   Concatenate:  prelude + fig parts + postlude  ->  build.jsx
   Run: osascript -e 'with timeout of 600 seconds' \
     -e 'tell application "Adobe Illustrator" to do javascript (read POSIX file "BUILD_JSX" as «class utf8»)' \
     -e 'end timeout'
   ============================================================ */

var BASE = "/Users/andres/Documents/GitHub/Monga_2026_096_AA_Pantanal/";
var OUT = BASE + "pdf/";
var QA = OUT; /* runner may override with a scratch folder */
var LOG = [];
var FONTS = {
  ps300: ["PublicSans-Light", "PublicSans-Regular"],
  ps400: ["PublicSans-Regular"],
  ps500: ["PublicSans-Medium", "PublicSans-Regular"],
  ps600: ["PublicSans-SemiBold", "PublicSans-Bold", "PublicSans-Regular"],
  rowan400: ["Rowan-Regular"],
  rowan500: ["Rowan-Medium", "Rowan-Regular"]
};

var _prevUI = app.userInteractionLevel;
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

var doc = null, aL = 0, aT = 0;

function C(hex) {
  var c = new RGBColor();
  c.red = parseInt(hex.substring(0, 2), 16);
  c.green = parseInt(hex.substring(2, 4), 16);
  c.blue = parseInt(hex.substring(4, 6), 16);
  return c;
}

var _fc = {};
function F(key) {
  if (_fc[key]) return _fc[key];
  var list = FONTS[key], i;
  for (i = 0; i < list.length; i++) {
    try { _fc[key] = app.textFonts.getByName(list[i]); return _fc[key]; } catch (e) {}
  }
  LOG.push("font missing: " + key);
  _fc[key] = app.textFonts[0];
  return _fc[key];
}

function X(x) { return aL + x; }
function Y(y) { return aT - y; }

/* new document, artboard = figure bounds (1 css px = 1 pt) */
function D(w, h) {
  doc = app.documents.add(DocumentColorSpace.RGB, w, h);
  var ab = doc.artboards[0].artboardRect;
  aL = ab[0]; aT = ab[1];
}

/* rectangle; fill/stroke are hex or "", op = opacity percent */
function R(x, y, w, h, fill, stroke, sw, rx, op) {
  var p;
  if (rx > 0) {
    var r = Math.min(rx, w / 2, h / 2);
    p = doc.pathItems.roundedRectangle(Y(y), X(x), w, h, r, r);
  } else {
    p = doc.pathItems.rectangle(Y(y), X(x), w, h);
  }
  if (fill) { p.filled = true; p.fillColor = C(fill); } else { p.filled = false; }
  if (stroke) { p.stroked = true; p.strokeColor = C(stroke); p.strokeWidth = sw; } else { p.stroked = false; }
  if (op < 100) p.opacity = op;
  return p;
}

/* rectangle with only the top-left corner rounded (the date chip) */
function RT(x, y, w, h, r, fill) {
  var k = r * 0.5523;
  var p = doc.pathItems.add();
  p.setEntirePath([
    [X(x + r), Y(y)], [X(x + w), Y(y)], [X(x + w), Y(y + h)],
    [X(x), Y(y + h)], [X(x), Y(y + r)]
  ]);
  p.closed = true;
  p.pathPoints[4].rightDirection = [X(x), Y(y + r - k)];
  p.pathPoints[0].leftDirection = [X(x + r - k), Y(y)];
  p.filled = true; p.fillColor = C(fill); p.stroked = false;
  return p;
}

function L(x1, y1, x2, y2, stroke, sw, dash, op) {
  var p = doc.pathItems.add();
  p.setEntirePath([[X(x1), Y(y1)], [X(x2), Y(y2)]]);
  p.filled = false; p.stroked = true;
  p.strokeColor = C(stroke); p.strokeWidth = sw;
  if (dash && dash.length) p.strokeDashes = dash;
  if (op < 100) p.opacity = op;
  return p;
}

function CI(cx, cy, r, fill, stroke, sw) {
  var p = doc.pathItems.ellipse(Y(cy - r), X(cx - r), 2 * r, 2 * r);
  if (fill) { p.filled = true; p.fillColor = C(fill); } else { p.filled = false; }
  if (stroke) { p.stroked = true; p.strokeColor = C(stroke); p.strokeWidth = sw; } else { p.stroked = false; }
  return p;
}

/* place + embed a raster, clipped to a rounded rect when rx > 0 */
function IM(rel, x, y, w, h, rx) {
  var g = doc.groupItems.add();
  var pi = doc.placedItems.add();
  pi.file = new File(BASE + rel);
  pi.width = w; pi.height = h;
  pi.position = [X(x), Y(y)];
  pi.move(g, ElementPlacement.PLACEATBEGINNING);
  try { pi.embed(); } catch (e) { LOG.push("embed failed: " + rel); }
  if (rx > 0) {
    var r = doc.pathItems.roundedRectangle(Y(y), X(x), w, h, rx, rx);
    r.filled = false; r.stroked = false;
    r.move(g, ElementPlacement.PLACEATBEGINNING);
    r.clipping = true;
    g.clipped = true;
  }
}

/* vector SVG import (locator globe, logomark) */
function SV(rel, x, y, w, h) {
  var g = null;
  try { g = doc.groupItems.createFromFile(new File(BASE + rel)); }
  catch (e) { LOG.push("svg import failed: " + rel + " (" + e + ")"); return; }
  g.width = w; g.height = h;
  g.position = [X(x), Y(y)];
}

function _style(ca, run) {
  ca.textFont = F(run[1]);
  ca.size = run[2];
  ca.fillColor = C(run[3]);
  if (run[4]) ca.tracking = run[4];
}

/* runs: [[text, fontKey, sizePt, hex, tracking], ...]; bi = base run index */
function _fill(tf, lead, align, bi, runs) {
  var s = "", i, j;
  for (i = 0; i < runs.length; i++) s += runs[i][0];
  tf.contents = s;
  var tr = tf.textRange;
  tr.paragraphAttributes.justification =
    align === "C" ? Justification.CENTER : (align === "R" ? Justification.RIGHT : Justification.LEFT);
  try { tr.paragraphAttributes.hyphenation = false; } catch (e) {}
  var ca = tr.characterAttributes;
  ca.autoLeading = false;
  ca.leading = lead;
  _style(ca, runs[bi]);
  var pos = 0;
  for (i = 0; i < runs.length; i++) {
    var t = runs[i][0];
    if (i !== bi) {
      for (j = 0; j < t.length; j++) {
        _style(tf.characters[pos + j].characterAttributes, runs[i]);
      }
    }
    pos += t.length;
  }
}

/* area type */
function AR(x, y, w, h, lead, align, bi, runs) {
  var rp = doc.pathItems.rectangle(Y(y), X(x), w, h);
  var tf = doc.textFrames.areaText(rp);
  _fill(tf, lead, align, bi, runs);
  return tf;
}

/* point type; y is the baseline, align anchors the point L/C/R */
function P(x, y, align, bi, runs) {
  var tf = doc.textFrames.pointText([X(x), Y(y)]);
  _fill(tf, runs[bi][2] * 1.2, align, bi, runs);
  return tf;
}

/* save Illustrator-editable PDF + QA PNG, close without touching anything else */
function FIN(name) {
  var pdf = new PDFSaveOptions();
  pdf.compatibility = PDFCompatibility.ACROBAT7;
  pdf.preserveEditability = true;
  pdf.viewAfterSaving = false;
  doc.saveAs(new File(OUT + name + ".pdf"), pdf);
  var png = new ExportOptionsPNG24();
  png.artBoardClipping = true;
  png.antiAliasing = true;
  doc.exportFile(new File(QA + name + ".png"), ExportType.PNG24, png);
  try { doc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) { LOG.push("close failed: " + name); }
  doc = null;
}
