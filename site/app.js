const COLORS = ["#ff6600", "#2563eb", "#0f8a4a", "#9333ea", "#c2362b", "#0891b2", "#ca8a04", "#db2777", "#4b5563", "#65a30d"];
const DEFAULT_TECH = ["Python", "TypeScript", "React", "Go", "Rust", "LLMs / GenAI"];
const MIN_SALARY_N = 15;

const data = await (await fetch("data/summary.json")).json();
const months = data.months.filter((m) => !m.in_progress);
const pending = data.months.find((m) => m.in_progress);
const labels = months.map((m) => m.month);

// ---------- helpers ----------
const monthName = (ym, style = "long") => {
  const [y, m] = ym.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleString("en-US", { month: style, year: "numeric", timeZone: "UTC" });
};
const pct = (v, digits = 0) => `${(v * 100).toFixed(digits)}%`;
const money = (v) => `$${Math.round(v / 1000)}k`;
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
const rolling = (xs, n) =>
  xs.map((_, i) => mean(xs.slice(Math.max(0, i - n + 1), i + 1).filter((v) => v != null)));

// Series are computed over the full history, then sliced to the selected range,
// so rolling averages at the start of a range are not truncated.
const series = {
  posts: months.map((m) => m.posts),
  posts12: rolling(months.map((m) => m.posts), 12),
  remote: rolling(months.map((m) => m.arrangement.remote), 3),
  hybrid: rolling(months.map((m) => m.arrangement.hybrid), 3),
  onsite: rolling(months.map((m) => m.arrangement.onsite), 3),
  unspecified: rolling(months.map((m) => m.arrangement.unspecified), 3),
  salaryListed: rolling(months.map((m) => m.salary_listed), 3),
  salaryMedian: rolling(months.map((m) => (m.salary_n >= MIN_SALARY_N ? m.salary_median : null)), 3).map((v, i) =>
    months[i].salary_n >= MIN_SALARY_N ? v : null),
  tech: Object.fromEntries(data.techs.map((t) => [t, rolling(months.map((m) => m.tech[t]), 3)])),
};

// ---------- header + KPIs ----------
const totalPosts = data.months.reduce((n, m) => n + m.posts, 0);
document.getElementById("meta").textContent =
  `Updated ${new Date(data.generated_at).toLocaleDateString("en-US", { dateStyle: "medium" })} · ` +
  `${data.months.length} monthly threads · ${totalPosts.toLocaleString()} job posts parsed` +
  (pending ? ` · ${monthName(pending.month)} in progress (${pending.posts} posts so far)` : "");

const now = months.at(-1);
const before = months.at(-13);
const kpis = [
  { label: "Job posts", value: now.posts.toLocaleString(), delta: now.posts / before.posts - 1, unit: "%" },
  { label: "Remote-only share", value: pct(now.arrangement.remote), delta: now.arrangement.remote - before.arrangement.remote, unit: "pts" },
  { label: "USD salary listed", value: pct(now.salary_listed), delta: now.salary_listed - before.salary_listed, unit: "pts" },
  {
    label: "Median listed salary",
    value: now.salary_n >= MIN_SALARY_N ? money(now.salary_median) : "n/a",
    delta: now.salary_n >= MIN_SALARY_N && before.salary_n >= MIN_SALARY_N ? now.salary_median / before.salary_median - 1 : null,
    unit: "%",
  },
];
document.getElementById("kpis").innerHTML = kpis
  .map(({ label, value, delta, unit }) => {
    const shown = delta == null ? "" : `${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta * 100).toFixed(unit === "%" ? 0 : 1)}${unit === "%" ? "%" : " pts"}`;
    return `<div class="kpi"><div class="label">${label}</div>
      <div class="value">${value}</div>
      <div class="delta ${delta >= 0 ? "up" : "down"}">${shown} <span>vs last year</span></div></div>`;
  })
  .join("");
document.getElementById("kpi-month").textContent = `${monthName(now.month)} at a glance`;

// ---------- charts ----------
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.color = "#5d6572";
Chart.defaults.animation.duration = 250;
Chart.defaults.plugins.legend.position = "bottom";
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.legend.labels.boxHeight = 10;
Chart.defaults.elements.point.radius = 0;
Chart.defaults.elements.point.hoverRadius = 4;
Chart.defaults.elements.line.borderWidth = 2;
Chart.defaults.elements.line.tension = 0.25;
Chart.defaults.interaction = { mode: "index", intersect: false };

let range = "all";
let start = 0;

// Half-width charts label every other year so ticks do not collide.
const xAxis = (narrow = false) => ({
  grid: { display: false },
  ticks: {
    autoSkip: false,
    maxRotation: 0,
    callback(i) {
      const ym = labels[start + i];
      if (range === "24") return i % (narrow ? 6 : 3) === 0 ? monthName(ym, "short") : "";
      const yearStep = narrow && range === "all" ? 2 : 1;
      return ym.endsWith("-01") && Number(ym.slice(0, 4)) % yearStep === 0 ? ym.slice(0, 4) : "";
    },
  },
});
const pctAxis = (extra = {}) => ({ beginAtZero: true, grid: { color: "#eef0f3" }, ticks: { callback: (v) => pct(v) }, ...extra });
const tooltipTitle = (items) => monthName(labels[start + items[0].dataIndex]);
const pctLabel = (c) => `${c.dataset.label}: ${c.raw == null ? "n/a" : pct(c.raw, 1)}`;

const charts = {};
const slice = (xs) => xs.slice(start);

function make(id, config) {
  config.options.plugins = { ...config.options.plugins, tooltip: { callbacks: { title: tooltipTitle, ...config.options.tooltipCallbacks } } };
  delete config.options.tooltipCallbacks;
  charts[id] = new Chart(document.getElementById(id), config);
}

make("posts", {
  type: "bar",
  data: { labels: slice(labels), datasets: [] },
  options: { maintainAspectRatio: false, scales: { x: xAxis(), y: { beginAtZero: true, grid: { color: "#eef0f3" } } } },
});
make("arrangement", {
  type: "line",
  data: { labels: slice(labels), datasets: [] },
  options: {
    maintainAspectRatio: false,
    scales: { x: xAxis(), y: pctAxis({ stacked: true, max: 1 }) },
    tooltipCallbacks: { label: pctLabel },
  },
});
make("salary", {
  type: "line",
  data: { labels: slice(labels), datasets: [] },
  options: {
    maintainAspectRatio: false,
    scales: {
      x: xAxis(),
      y: pctAxis(),
      y2: { position: "right", grid: { display: false }, ticks: { callback: (v) => money(v) } },
    },
    tooltipCallbacks: {
      label: (c) => (c.dataset.yAxisID === "y2" ? `${c.dataset.label}: ${c.raw == null ? "n/a" : money(c.raw)}` : pctLabel(c)),
    },
  },
});
make("tech", {
  type: "line",
  data: { labels: slice(labels), datasets: [] },
  options: { maintainAspectRatio: false, scales: { x: xAxis(), y: pctAxis() }, tooltipCallbacks: { label: pctLabel } },
});

const selected = new Set(DEFAULT_TECH);
const colorOf = (t) => COLORS[[...selected].indexOf(t) % COLORS.length];

function render() {
  start = range === "all" ? 0 : range === "24" ? Math.max(0, months.length - 24) : labels.findIndex((m) => m >= "2020-01");
  for (const c of Object.values(charts)) {
    c.data.labels = slice(labels);
    c.options.scales.x = xAxis(c.canvas.closest(".grid") != null);
  }

  charts.posts.data.datasets = [
    { type: "line", label: "12-month average", data: slice(series.posts12), borderColor: "#16191f" },
    { type: "bar", label: "Job posts", data: slice(series.posts), backgroundColor: "rgba(255,102,0,.45)", borderRadius: 2 },
  ];

  const area = (label, key, color, fill) => ({ label, data: slice(series[key]), borderColor: color, backgroundColor: color + "cc", fill, borderWidth: 1 });
  charts.arrangement.data.datasets = [
    area("Remote only", "remote", "#ff6600", "origin"),
    area("Hybrid / mixed", "hybrid", "#2563eb", "-1"),
    area("On-site only", "onsite", "#0f8a4a", "-1"),
    area("Not stated", "unspecified", "#c9ced6", "-1"),
  ];

  charts.salary.data.datasets = [
    { label: "Posts listing a USD salary", data: slice(series.salaryListed), borderColor: "#ff6600", yAxisID: "y" },
    { label: "Median listed salary", data: slice(series.salaryMedian), borderColor: "#2563eb", yAxisID: "y2", spanGaps: false },
  ];

  charts.tech.data.datasets = [...selected].map((t) => ({ label: t, data: slice(series.tech[t]), borderColor: colorOf(t), backgroundColor: colorOf(t) }));

  for (const c of Object.values(charts)) c.update();
  renderChips();
}

function renderChips() {
  const el = document.getElementById("chips");
  el.innerHTML = data.techs
    .map((t) => {
      const on = selected.has(t);
      return `<button class="chip${on ? " on" : ""}" data-tech="${t}" style="${on ? `color:${colorOf(t)}` : ""}"><i style="${on ? `background:${colorOf(t)}` : ""}"></i>${t}</button>`;
    })
    .join("");
}

document.getElementById("chips").addEventListener("click", (e) => {
  const t = e.target.closest(".chip")?.dataset.tech;
  if (!t) return;
  selected.has(t) ? selected.delete(t) : selected.add(t);
  render();
});
document.querySelector(".range").addEventListener("click", (e) => {
  const r = e.target.closest("button")?.dataset.range;
  if (!r) return;
  range = r;
  document.querySelectorAll(".range button").forEach((b) => b.classList.toggle("on", b.dataset.range === r));
  render();
});

// ---------- movers table ----------
const last12 = months.slice(-12);
const prior12 = months.slice(-24, -12);
const movers = data.techs
  .map((t) => {
    const nowShare = mean(last12.map((m) => m.tech[t]));
    const prevShare = mean(prior12.map((m) => m.tech[t]));
    return { t, nowShare, prevShare, delta: nowShare - prevShare };
  })
  .sort((a, b) => b.delta - a.delta);
const shown = [...movers.slice(0, 6), ...movers.slice(-6)];
const maxDelta = Math.max(...shown.map((m) => Math.abs(m.delta)));
document.getElementById("movers-sub").textContent =
  `Share of posts mentioning each technology, ${monthName(last12[0].month, "short")}–${monthName(last12.at(-1).month, "short")} vs. the 12 months before. Six biggest gains and drops.`;
document.querySelector("#movers tbody").innerHTML = shown
  .map(({ t, nowShare, prevShare, delta }) => {
    const dir = delta >= 0 ? "up" : "down";
    const w = Math.max(2, Math.round((Math.abs(delta) / maxDelta) * 160));
    return `<tr><td>${t}</td><td class="num">${pct(prevShare, 1)}</td><td class="num">${pct(nowShare, 1)}</td>
      <td><div class="bar ${dir}"><i style="width:${w}px"></i>${delta >= 0 ? "+" : "−"}${Math.abs(delta * 100).toFixed(1)} pts</div></td></tr>`;
  })
  .join("");

render();
