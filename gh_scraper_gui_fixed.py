#!/usr/bin/env python3
import threading
import time
import re
import http.server
import webbrowser
import json
import urllib.parse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://galaxyharvester.net/schematics.py/"
DELAY = 0.5

session = requests.Session()
session.headers.update({"User-Agent": "GH-Schematic-Scraper/GUI-FIX"})
_cache = {}

def slug_from_url(url):
    if "/schematics.py/" in url:
        return url.split("/schematics.py/")[-1].strip("/")
    return url.strip("/")

def fetch_schematic(slug, emit):
    if slug in _cache:
        return _cache[slug]

    url = BASE_URL + slug
    emit(f"Fetching: {url}")

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        emit(f"ERROR: {e}")
        return {"name": slug, "resources": [], "subcomponents": []}

    time.sleep(DELAY)
    soup = BeautifulSoup(resp.text, "html.parser")

    name = soup.find("h2").get_text(strip=True) if soup.find("h2") else slug

    resources = []
    subcomponents = []

    # Find ingredients section
    ingredients_elem = soup.find(lambda tag: tag.name in ['h3', 'h4', 'h2'] and 'Ingredients' in tag.get_text())
    if ingredients_elem:
        current = ingredients_elem.find_next_sibling()
        if current and current.name == 'table':
            # parse table
            for tr in current.find_all("tr"):
                if "This schematic is an ingredient" in tr.get_text():
                    break
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                qty_text = tds[0].get_text(strip=True)
                if not qty_text.isdigit():
                    continue
                qty = int(qty_text)
                # find all a in tds[2]
                links = tds[2].find_all('a', href=True)
                for link in links:
                    name_text = link.get_text(strip=True)
                    href = link["href"]
                    if "/resourceType.py/" in href:
                        resources.append((qty, name_text))
                    elif href and not href.startswith('http'):  # relative links for schematics
                        if not any(s[0] == qty for s in subcomponents):  # add only the first subcomponent for this qty
                            sub_slug = slug_from_url(href)
                            subcomponents.append((qty, name_text, sub_slug))
        elif current and current.name in ['p', 'div']:
            p = current
            for a in p.find_all('a', href=True):
                text_before = ''
                for prev in a.previous_siblings:
                    if isinstance(prev, str):
                        text_before = prev + text_before
                    elif prev.name in ['a', 'img']:
                        break
                text_before = text_before.strip()
                match = re.search(r'(\d+)\s*$', text_before)
                if match:
                    qty = int(match.group(1))
                    name_text = a.get_text(strip=True)
                    href = a['href']
                    if "/resourceType.py/" in href:
                        resources.append((qty, name_text))
                    elif "/schematics.py/" in href:
                        sub_slug = slug_from_url(href)
                        subcomponents.append((qty, name_text, sub_slug))
    else:
        # fallback to old table parsing if no ingredients section
        table = soup.find("table")
        if table:
            for tr in table.find_all("tr"):
                if "This schematic is an ingredient" in tr.get_text():
                    break
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                qty_text = tds[0].get_text(strip=True)
                if not qty_text.isdigit():
                    continue
                qty = int(qty_text)
                link = tds[2].find("a")
                if not link:
                    continue
                name_text = link.get_text(strip=True)
                href = link["href"]
                if "/resourceType.py/" in href:
                    resources.append((qty, name_text))
                elif "/schematics.py/" in href:
                    sub_slug = slug_from_url(href)
                    subcomponents.append((qty, name_text, sub_slug))

    result = {"name": name, "resources": resources, "subcomponents": subcomponents}
    _cache[slug] = result
    return result


def expand_schematic(slug, emit, multiplier=1, depth=0):
    schem = fetch_schematic(slug, emit)

    total_resources = defaultdict(int)
    lines = []

    indent = "  " * depth
    lines.append(f"{indent}{multiplier}x {schem['name']}")

    for qty, res in schem["resources"]:
        total_resources[res] += qty * multiplier
        lines.append(f"{indent}  - {qty * multiplier} {res}")

    for qty, name, sub_slug in schem["subcomponents"]:
        sub_total, sub_lines = expand_schematic(sub_slug, emit, qty * multiplier, depth + 1)
        lines.extend(sub_lines)
        for k, v in sub_total.items():
            total_resources[k] += v

    return total_resources, lines


def build_notecard(schematics, emit):
    lines = []
    grand_totals = defaultdict(int)

    for slug, multiplier in schematics:
        emit(f"Processing: {slug} (x{multiplier})")
        totals, tree_lines = expand_schematic(slug, emit, multiplier)

        lines.extend(tree_lines)
        lines.append("\nTOTAL RESOURCES:")
        for res, qty in sorted(totals.items()):
            lines.append(f"{qty} {res}")
            grand_totals[res] += qty

        lines.append("\n" + "-" * 40)

    lines.append("\nGRAND TOTAL:")
    for res, qty in sorted(grand_totals.items()):
        lines.append(f"{qty} {res}")

    lines.append("\nRESOURCES NEEDED:")
    resources_needed = sorted(set(grand_totals.keys()))
    for res in resources_needed:
        lines.append(res)

    return "\n".join(lines)


scrape_state = {
    "running": False,
    "log": [],
    "result": None,
    "done": False,
}


def run_scrape(schematics):
    scrape_state.update({"running": True, "log": [], "result": None, "done": False})

    def emit(msg):
        scrape_state["log"].append(msg)

    result = build_notecard(schematics, emit)

    scrape_state["result"] = result
    scrape_state["done"] = True
    scrape_state["running"] = False


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GH Schematic Scraper</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0f1117; color: #e2e8f0; min-height: 100vh; }

  header { background: #1a1d27; border-bottom: 1px solid #2d3148;
           padding: 18px 28px; display: flex; align-items: center; gap: 14px; }
  header h1 { font-size: 18px; font-weight: 600; color: #f1f5f9; }
  header p  { font-size: 13px; color: #94a3b8; margin-top: 2px; }
  .logo { width: 38px; height: 38px; background: #2d7d46; border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          font-size: 20px; flex-shrink: 0; }

  main { max-width: 800px; margin: 0 auto; padding: 28px 20px; }

  .card { background: #1a1d27; border: 1px solid #2d3148;
          border-radius: 12px; padding: 20px 22px; margin-bottom: 18px; }
  .card h2 { font-size: 13px; font-weight: 500; color: #94a3b8;
             text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 14px; }

  .url-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
  .url-num  { font-size: 12px; color: #64748b; width: 22px; text-align: right;
              flex-shrink: 0; }
  .url-row input { flex: 1; background: #0f1117; border: 1px solid #2d3148;
                   border-radius: 8px; padding: 9px 12px; color: #e2e8f0;
                   font-size: 13px; outline: none; transition: border 0.15s; }
  .url-row input:focus { border-color: #4f8ef7; }
  .url-row input::placeholder { color: #475569; }

  .qty-input { width: 70px !important; }

  .btn-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .btn { background: #252836; border: 1px solid #2d3148; border-radius: 8px;
         color: #cbd5e1; padding: 7px 14px; font-size: 13px; cursor: pointer;
         transition: background 0.15s; }
  .btn:hover { background: #2d3148; }

  .count-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
  .count-row label { font-size: 13px; color: #94a3b8; }
  .count-row input[type=number] { width: 64px; background: #0f1117;
    border: 1px solid #2d3148; border-radius: 8px; padding: 7px 10px;
    color: #e2e8f0; font-size: 13px; outline: none; }

  #scrape-btn { width: 100%; padding: 13px; background: #2d7d46;
                border: none; border-radius: 10px; color: white;
                font-size: 15px; font-weight: 600; cursor: pointer;
                transition: background 0.15s; margin-bottom: 18px; }
  #scrape-btn:hover:not(:disabled) { background: #246038; }
  #scrape-btn:disabled { background: #1a4028; color: #4a7a5a; cursor: not-allowed; }

  #log-card { display: none; }
  #log-box { background: #0f1117; border-radius: 8px; padding: 14px;
             font-family: "Consolas", "Courier New", monospace; font-size: 12px;
             color: #94a3b8; min-height: 120px; max-height: 240px;
             overflow-y: auto; white-space: pre-wrap; line-height: 1.6; }

  #result-card { display: none; }
  #result-box  { background: #0f1117; border-radius: 8px; padding: 14px;
                 font-family: "Consolas", "Courier New", monospace; font-size: 12px;
                 color: #cbd5e1; max-height: 340px; overflow-y: auto;
                 white-space: pre; line-height: 1.65; min-height: 200px; }

  #download-btn { display: none; width: 100%; padding: 12px; background: #1a5fa8;
                  border: none; border-radius: 10px; color: white;
                  font-size: 14px; font-weight: 600; cursor: pointer;
                  transition: background 0.15s; margin-top: 14px; }
  #download-btn:hover { background: #154d8a; }

  .spinner { display: inline-block; width: 14px; height: 14px;
             border: 2px solid #4a7a5a; border-top-color: white;
             border-radius: 50%; animation: spin 0.7s linear infinite;
             vertical-align: middle; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <div class="logo">&#x1F52D;</div>
  <div>
    <h1>GH Schematic Scraper</h1>
    <p>Galaxy Harvester &mdash; resource notecard generator</p>
  </div>
</header>

<main>

  <div class="card">
    <h2>Schematic URLs & Quantities</h2>
    <div id="url-list"></div>
    <div class="btn-row">
      <button class="btn" onclick="addRow()">+ Add row</button>
      <button class="btn" onclick="removeLast()">✕ Remove last</button>
    </div>
  </div>

  <button id="scrape-btn" onclick="startScrape()">▶️  Scrape Schematics</button>

  <div class="card" id="log-card">
    <h2>Progress</h2>
    <div id="log-box"></div>
  </div>

  <div class="card" id="result-card">
    <h2>Notecard Preview</h2>
    <div id="result-box"></div>
    <button id="download-btn" onclick="downloadResult()">💾  Download Notecard (.txt)</button>
  </div>

</main>

<script>
let resultText = "";
let pollTimer  = null;
let logOffset  = 0;

function addRow(val='') {
  const list = document.getElementById("url-list");
  const idx  = list.children.length + 1;
  const div  = document.createElement("div");
  div.className = "url-row";
  div.innerHTML = `<span class="url-num">${idx}.</span>
    <input type="text" placeholder="https://galaxyharvester.net/schematics.py/..." value="${val}" />
    <input type="number" class="qty-input" min="1" value="1" />`;
  list.appendChild(div);
  renumber();
}

function removeLast() {
  const list = document.getElementById("url-list");
  if (list.children.length > 1) list.removeChild(list.lastChild);
  renumber();
}

function renumber() {
  const rows = document.querySelectorAll(".url-row");
  rows.forEach((r, i) => { r.querySelector(".url-num").textContent = (i+1)+"."; });
}

function getUrls() {
  const rows = document.querySelectorAll(".url-row");
  const result = [];
  rows.forEach(row => {
    const inputs = row.querySelectorAll("input");
    const url = inputs[0].value.trim();
    const qty = Math.max(1, parseInt(inputs[1].value) || 1);
    if (url) result.push({url: url, qty: qty});
  });
  return result;
}

function startScrape() {
  const schematics = getUrls();
  if (!schematics.length) { alert("Please enter at least one schematic URL."); return; }

  document.getElementById("scrape-btn").disabled = true;
  document.getElementById("scrape-btn").innerHTML = '<span class="spinner"></span> Scraping...';
  document.getElementById("log-card").style.display   = "block";
  document.getElementById("result-card").style.display = "none";
  document.getElementById("download-btn").style.display = "none";
  document.getElementById("log-box").innerHTML = "";
  logOffset = 0;

  fetch("/scrape", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({schematics})
  }).then(() => {
    pollTimer = setInterval(pollLog, 800);
  }).catch(e => {
    appendLog("Error starting scrape: " + e, "warn");
    resetBtn();
  });
}

function pollLog() {
  fetch("/status?offset=" + logOffset)
    .then(r => r.json())
    .then(data => {
      (data.new_lines || []).forEach(line => {
        logOffset++;
        let cls = "";
        if (line.startsWith("✓"))          cls = "";
        else if (line.includes("ERROR")) cls = "log-warn";
        else if (line.startsWith("Fetching")) cls = "";
        appendLog(line, cls);
      });
      if (data.done) {
        clearInterval(pollTimer);
        resetBtn();
        if (data.result) {
          resultText = data.result;
          document.getElementById("result-box").textContent = resultText;
          document.getElementById("result-card").style.display = "block";
          document.getElementById("download-btn").style.display = "block";
        }
      }
    });
}

function appendLog(msg, cls) {
  const box  = document.getElementById("log-box");
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = msg + "\\n";
  box.appendChild(span);
  box.scrollTop = box.scrollHeight;
}

function resetBtn() {
  const btn = document.getElementById("scrape-btn");
  btn.disabled = false;
  btn.innerHTML = "▶️  Scrape Schematics";
}

function downloadResult() {
  const blob = new Blob([resultText], {type: "text/plain"});
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = "schematic_notecard.txt";
  a.click();
}

addRow();
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        if self.path.startswith("/status"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            offset = int(qs.get("offset", ["0"])[0])
            new = scrape_state["log"][offset:]

            payload = json.dumps({
                "new_lines": new,
                "done": scrape_state["done"],
                "result": scrape_state["result"]
            })
            self._send(200, "application/json", payload.encode())
        else:
            self._send(200, "text/html", HTML.encode())

    def do_POST(self):
        if self.path == "/scrape":
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
                schematics = []
                for item in data.get("schematics", []):
                    slug = slug_from_url(item.get("url", ""))
                    qty = int(item.get("qty", 1))
                    if slug:
                        schematics.append((slug, qty))

                if schematics:
                    threading.Thread(target=run_scrape, args=(schematics,), daemon=True).start()
                    self._send(200, "application/json", b'{"ok":true}')
                else:
                    self._send(400, "application/json", json.dumps({"error": "No valid schematics provided"}).encode())
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def find_port():
    import socket
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


if __name__ == "__main__":
    port = find_port()
    url = f"http://localhost:{port}"
    print("Open:", url)
    print("Press Ctrl+C to stop the server.")
    webbrowser.open(url)

    server = http.server.HTTPServer(("", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        print("Server stopped.")
