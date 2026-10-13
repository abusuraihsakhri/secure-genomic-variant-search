"use strict";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_RECORDS = 100000;
const DISPLAY_LIMIT = 250;
const COLUMNS = ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"];
const DEMO_VCF = [
  "##fileformat=VCFv4.2",
  "##source=synthetic-example",
  "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
  "chr1\t10177\trs367896724\tA\tAC\t50\tPASS\tGENE=DEMO1",
  "chr1\t10352\trs555500075\tT\tTA\t99\tPASS\tGENE=DEMO1",
  "chr7\t140453136\t.\tA\tT\t65\tPASS\tGENE=DEMO2",
  "chr17\t43044295\t.\tG\tA\t48\tq10\tGENE=DEMO3"
].join("\n");

function parseVcf(text) {
  if (typeof text !== "string") throw new TypeError("Expected text VCF input");
  if (text.length > MAX_FILE_BYTES) throw new Error("VCF exceeds the 10 MiB limit");
  const records = [];
  let hasHeader = false;
  for (const [index, raw] of text.replace(/\r\n?/g, "\n").split("\n").entries()) {
    const line = raw.trim();
    if (!line || line.startsWith("##")) continue;
    if (line.startsWith("#CHROM")) {
      const fields = line.split("\t");
      if (hasHeader || COLUMNS.some((name, i) => fields[i] !== (i === 0 ? "#CHROM" : name))) {
        throw new Error("Invalid or duplicate #CHROM header");
      }
      hasHeader = true;
      continue;
    }
    if (line.startsWith("#")) continue;
    if (!hasHeader) throw new Error("Missing #CHROM header before data records");
    const cells = line.split("\t");
    const position = Number(cells[1]);
    if (cells.length < 8 || !Number.isSafeInteger(position) || position < 1 ||
        !cells[0] || !cells[3] || !cells[4]) {
      throw new Error("Malformed VCF record at line " + (index + 1));
    }
    const record = Object.fromEntries(COLUMNS.map((key, i) => [key, cells[i]]));
    record.POS = position;
    records.push(record);
    if (records.length > MAX_RECORDS) throw new Error("VCF exceeds the 100,000 record limit");
  }
  if (!hasHeader) throw new Error("Expected a tab-separated VCF with a #CHROM header");
  return records;
}

function normalizeChromosome(value) {
  return String(value || "").trim().replace(/^chr/i, "").toUpperCase();
}

function searchVariants(records, filters = {}) {
  const chrom = normalizeChromosome(filters.chromosome);
  const start = filters.start === "" || filters.start == null ? null : Number(filters.start);
  const end = filters.end === "" || filters.end == null ? null : Number(filters.end);
  const text = String(filters.text || "").toLowerCase().trim();
  for (const bound of [start, end]) {
    if (bound !== null && (!Number.isSafeInteger(bound) || bound < 1)) {
      throw new Error("Coordinates must be positive whole numbers");
    }
  }
  if (start !== null && end !== null && end < start) {
    throw new Error("End coordinate must not precede start coordinate");
  }
  return records.filter(row =>
    (!chrom || normalizeChromosome(row.CHROM) === chrom) &&
    (start === null || row.POS >= start) &&
    (end === null || row.POS <= end) &&
    (!text || [row.ID, row.REF, row.ALT, row.INFO].some(v => String(v).toLowerCase().includes(text)))
  );
}

function csvEncode(records) {
  function safeCell(value) {
    let v = String(value ?? "");
    // Prevent spreadsheet formula injection when CSV is opened in Excel/Sheets.
    if (/^[=+\-@\t\r\n]/.test(v)) v = "'" + v;
    return '"' + v.replace(/"/g, '""') + '"';
  }
  const lines = [COLUMNS.map(safeCell).join(",")];
  for (const record of records) lines.push(COLUMNS.map(key => safeCell(record[key])).join(","));
  return lines.join("\r\n") + "\r\n";
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseVcf, searchVariants, csvEncode, normalizeChromosome, DEMO_VCF };
}

if (typeof document !== "undefined") {
  const fileInput = document.getElementById("vcf-file");
  const searchForm = document.getElementById("search-form");
  const status = document.getElementById("status");
  const summary = document.getElementById("summary");
  const tbody = document.getElementById("results-body");
  const exportButton = document.getElementById("export-button");
  const fields = ["chromosome", "start", "end", "text"];
  let records = [];
  let results = [];

  function announce(message, error = false) {
    status.textContent = message;
    status.dataset.error = error ? "true" : "false";
  }

  function draw() {
    tbody.replaceChildren();
    for (const record of results.slice(0, DISPLAY_LIMIT)) {
      const tr = document.createElement("tr");
      for (const key of COLUMNS) {
        const td = document.createElement("td");
        td.textContent = String(record[key]);
        tr.append(td);
      }
      tbody.append(tr);
    }
    summary.textContent = records.length
      ? results.length + " matching of " + records.length + " loaded variants" +
        (results.length > DISPLAY_LIMIT ? "; showing the first " + DISPLAY_LIMIT : "")
      : "No VCF records loaded";
    exportButton.disabled = results.length === 0;
  }

  function applyFilters() {
    try {
      const filters = Object.fromEntries(fields.map(id => [id, document.getElementById(id).value]));
      results = searchVariants(records, filters);
      draw();
      announce(records.length ? "Search complete (local browser processing)." : "Load a VCF to begin.");
    } catch (error) {
      results = [];
      draw();
      announce(error.message, true);
    }
  }

  function loadText(text, filename) {
    records = parseVcf(text);
    document.getElementById("source-name").textContent = filename;
    applyFilters();
  }

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    records = [];
    results = [];
    draw();
    document.getElementById("source-name").textContent = "None";
    if (file.size > MAX_FILE_BYTES) {
      announce("File exceeds the 10 MiB limit; use a smaller plain-text VCF.", true);
      return;
    }
    try {
      loadText(await file.text(), file.name);
    } catch (error) {
      records = [];
      results = [];
      draw();
      announce(error.message, true);
    }
  });

  document.getElementById("demo-button").addEventListener("click", () => {
    fileInput.value = "";
    searchForm.reset();
    loadText(DEMO_VCF, "Synthetic VCF example");
  });

  searchForm.addEventListener("submit", event => {
    event.preventDefault();
    applyFilters();
  });

  document.getElementById("clear-button").addEventListener("click", () => {
    searchForm.reset();
    applyFilters();
  });

  exportButton.addEventListener("click", () => {
    if (!results.length) return;
    const blob = new Blob([csvEncode(results)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "vcf-search-results.csv";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  draw();
}
