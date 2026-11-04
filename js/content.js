/* ============================================================
   CONTENT & DATA — everything editorial lives here.
   Copy follows Andrés's Illustrator redesign (2026_096_AA_
   Pantanal_v1.ai, 28 Oct). All text and numbers derive from the
   reporter's source folder (Sugai/UFMS presentation + animations,
   Pereira et al. 2022, Stevaux et al. 2020, Bergier & Assine 2016,
   Damasceno-Junior & Pott 2021).
   Edit copy here; no editorial text is hardcoded in main.js.
   ============================================================ */

const CONTENT = {
  /* ---------- Figure 1 — The dry and wet season dynamics in the Pantanal ---------- */
  fig1: {
    heading: "Dry and wet season dynamics in the Pantanal",
    body: [
      "Rains peak in January and create initial flooding. Due to bottlenecks in the Paraguay River, the flood doesn't extend further south until months later, deep into the dry season."
    ],
    globeCaption: "The Pantanal lies at the heart of South America, where Brazil, Bolivia and Paraguay meet.",
    mapTitle: "Average share of each month spent underwater",
    mapTitlePeriod: "Period 1999–2019",
    /* white annotation over the map's top-left corner */
    mapOverlay: "Blue–white shading marks areas covered by water in a given month.",
    playLabel: "Play the year",
    pauseLabel: "Pause",
    // wet season band on the month dial (hydrological: Oct–May rains)
    wetMonths: [9, 10, 11, 0, 1, 2, 3, 4], // Oct..May as 0-indexed months
    wetSeasonLabel: "Rainy season (Oct–May)",
    months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    // callouts appear only during the listed months (0-indexed)
    callouts: [
      {
        months: [11, 0, 1, 2],
        x: 27, y: 24,            // anchor point, % of map area
        boxX: 48, boxY: 10,      // text box position, % of map area
        lead: "Summer rains",
        text: "The northern river fans flood first, while the rains are still falling."
      },
      {
        months: [4, 5, 6, 7],
        x: 36, y: 66,
        boxX: 55, boxY: 58,
        lead: "",
        text: "The wetland is so flat that the flood takes months to reach further south, arriving around the mid-year dry season."
      }
    ],
    stats: [
      { value: "39%", label: "of the wetland never flooded between 2000 and 2020" },
      { value: "3.4%", label: "is permanently underwater" },
      { value: "~60%", label: "of the year-to-year variation in flooding is explained by rainfall alone" }
    ],
    cycleNote: {
      lead: "Part of a longer cycle:",
      text: "A century of river-level records show alternating wet and dry phases: The driest span ran 1963–73 and the 2020 drought."
    },
    sources: "Sources: J.L.M. Moreira Sugai (UFMS); Pereira et al. (2022); Stevaux et al. (2020); Bergier & Assine (2016); Damasceno-Junior & Pott (2021)."
  },

  /* ---------- Figure 2 — In 2020 the water stayed away, and fire moved in ---------- */
  fig2: {
    heading: "In 2020, the water stayed away, and fire moved in",
    body: [
      "Less rain meant a lesser flood — and more wildfire. In 2020, floods shrank by 83% below the 2000–2020 average while fire spread deep into areas that normally sit underwater."
    ],
    mapTitle: "Fire detections through 2020",
    legend: [
      { swatch: "flood", label: "Pantanal ecoregion" },
      { swatch: "fire", label: "Fire detections" }
    ],
    chart: {
      title: "Annual flooded area in the Pantanal",
      unit: "Thousand km²",
      // Pereira et al. 2022, Fig. 3 (km²)
      years: [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
              2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020],
      values: [46008, 30879, 44312, 38688, 33330, 26922, 49631, 45715, 51218, 26074, 31065,
               57969, 18168, 28318, 52500, 43256, 42908, 27304, 44952, 26632, 10668],
      // annotation lines per highlighted year (arrays break lines)
      annotations: {
        2011: ["Biggest flood"],
        2020: ["The year", "of the fires"]
      }
    },
    sources: "Sources: NASA FIRMS VIIRS (2020); Copernicus Sentinel-2 (June 2020); WWF Terrestrial Ecoregions (2001); Pereira et al. (2022); J.L.M. Moreira Sugai (UFMS)."
  },

  /* ---------- Figure 3 — Why scientists are wiring the wetland for sound ---------- */
  fig3: {
    heading: "Why scientists are wiring the wetland for sound",
    body: [
      "Two centuries of wildlife records are distributed mostly along road networks, and don't accurately capture the rest of the biome."
    ],
    gbifMaps: [
      { img: "assets/gbif_amphibia_s2.svg", species: "79 amphibians", records: "5,930 records" },
      { img: "assets/gbif_mammalia_s2.svg", species: "153 mammals", records: "87,745 records" },
      { img: "assets/gbif_aves_s2.svg", species: "855 birds", records: "1,805,377 records" }
    ],
    gbifCaption: "Occurrence records (orange dots) from the Global Biodiversity Information Facility (GBIF); species and record counts cover the Pantanal ecoregion (teal area). Records cluster along roads, rivers and towns, leaving large sampling gaps in the seasonally flooded interior.",
    sources: "Sources: GBIF occurrence data (Oct. 2026); WWF Terrestrial Ecoregions (2001); Copernicus Sentinel-2 (June 2020); J.L.M. Moreira Sugai (UFMS)."
  }
};
