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
    # Handle relative hrefs like "food_drink_alcohol" or href attributes
    return url.replace(".py/", "").replace(".py", "").strip("/")

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
            # parse table - look at all rows and extract links
            for tr in current.find_all("tr"):
                if "This schematic is an ingredient" in tr.get_text():
                    break
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                qty_text = tds[0].get_text(strip=True)
                if not qty_text.isdigit():
                    continue
                qty = int(qty_text)
                
                # Find all links in this row
                links = tr.find_all('a', href=True)
                for link in links:
                    name_text = link.get_text(strip=True).strip()
                    if not name_text:
                        continue
                    href = link.get("href", "")
                    
                    if "/resourceType.py/" in href:
                        resources.append((qty, name_text))
                    elif "schematics.py" in href or (href and "/" not in href and not href.startswith("http")):
                        # Handle both absolute and relative schema links
                        if href.startswith("/"):
                            sub_slug = slug_from_url(href)
                        else:
                            # Convert relative href to slug
                            sub_slug = href.replace(".py/", "").replace(".py", "").strip("/")
                        subcomponents.append((qty, name_text, sub_slug))
        elif current and current.name in ['p', 'div']:
            # Parse text with inline links (like "2 Alcohol" with images between qty and link)
            container_text = current.get_text(separator=" ", strip=True)
            
            # Find all potential quantity+resource/schematic patterns
            links = current.find_all('a', href=True)
            for link in links:
                name_text = link.get_text(strip=True).strip()
                if not name_text:
                    continue
                    
                href = link.get("href", "")
                
                # Try to find quantity before the link
                qty = 1
                # Search backwards from the link for text containing a number
                prev_text = []
                for prev in link.previous_siblings:
                    if isinstance(prev, str):
                        prev_text.insert(0, prev.strip())
                    elif hasattr(prev, 'get_text'):
                        prev_text.insert(0, prev.get_text(strip=True))
                        if prev.name in ['img', 'a'] and prev_text[0]:
                            break
                
                combined = " ".join(prev_text).strip()
                match = re.search(r'(\d+)\s*$', combined)
                if match:
                    qty = int(match.group(1))
                
                if "/resourceType.py/" in href:
                    resources.append((qty, name_text))
                elif "schematics.py" in href or (href and "/" not in href and not href.startswith("http")):
                    if href.startswith("/"):
                        sub_slug = slug_from_url(href)
                    else:
                        sub_slug = href.replace(".py/", "").replace(".py", "").strip("/")
                    subcomponents.append((qty, name_text, sub_slug))
    
    # Fallback: check for table if no ingredients section found
    if not resources and not subcomponents:
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
                
                links = tr.find_all('a', href=True)
                for link in links:
                    name_text = link.get_text(strip=True)
                    href = link.get("href", "")
                    if "/resourceType.py/" in href:
                        resources.append((qty, name_text))
                    elif "schematics.py" in href or (href and "/" not in href and not href.startswith("http")):
                        if href.startswith("/"):
                            sub_slug = slug_from_url(href)
                        else:
                            sub_slug = href.replace(".py/", "").replace(".py", "").strip("/")
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

  .url-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
  .url-num  { font-size: 12px; color: #64748b; width: 26px; text-align: right;
              flex-shrink: 0; font-weight: 500; }
  .url-row input { background: #0f1117; border: 1px solid #2d3148;
                   border-radius: 8px; padding: 10px 12px; color: #e2e8f0;
                   font-size: 13px; outline: none; transition: all 0.15s; }
  .url-row input:first-of-type { flex: 1; }
  .url-row input:focus { border-color: #4f8ef7; box-shadow: 0 0 0 2px rgba(79, 142, 247, 0.1); }
  .url-row input::placeholder { color: #475569; }

  .qty-input { width: 80px !important; }

  .btn-row { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .btn { background: #2d7d46; border: 1px solid #1a5a36; border-radius: 8px;
         color: #fff; padding: 10px 18px; font-size: 13px; font-weight: 500;
         cursor: pointer; transition: all 0.15s; }
  .btn:hover { background: #246038; box-shadow: 0 2px 8px rgba(45, 125, 70, 0.3); }
  .btn:active { transform: scale(0.98); }

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

  .discord-card { display: none; }
  .discord-options { display: flex; gap: 14px; margin-bottom: 16px; }
  .discord-option { display: flex; align-items: center; gap: 6px; }
  .discord-option input[type="radio"] { cursor: pointer; }
  .discord-option label { cursor: pointer; font-size: 13px; color: #94a3b8; }
  .discord-sections { display: flex; flex-direction: column; gap: 12px; }
  .discord-section { background: #0f1117; border-radius: 8px; padding: 12px;
                    font-family: "Consolas", "Courier New", monospace;
                    font-size: 11px; color: #cbd5e1; overflow-x: auto;
                    max-height: 200px; min-height: 80px; white-space: pre-wrap;
                    word-wrap: break-word; line-height: 1.4; position: relative; }
  .discord-section-header { font-size: 10px; color: #64748b; margin-bottom: 8px;
                            font-weight: 600; }
  .discord-copy-btn { position: absolute; top: 8px; right: 8px; padding: 4px 8px;
                     background: #1a5fa8; border: none; border-radius: 4px;
                     color: white; font-size: 10px; cursor: pointer;
                     transition: background 0.15s; }
  .discord-copy-btn:hover { background: #154d8a; }

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
    <div class="btn-row">
      <button class="btn" type="button" onclick="addRow()">+ Add</button>
      <button class="btn" type="button" onclick="removeLast()">✕ Remove</button>
    </div>
    <h2>Schematic URLs & Quantities</h2>
    <div id="url-list">
      <div class="url-row">
        <span class="url-num">1.</span>
        <input type="text" placeholder="https://galaxyharvester.net/schematics.py/..." />
        <input type="number" class="qty-input" min="1" value="1" />
      </div>
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

  <div class="card discord-card" id="discord-card">
    <h2>Discord Export</h2>
    <div class="discord-options">
      <div class="discord-option">
        <input type="radio" id="discord-no-nitro" name="discord-format" value="2000" onchange="updateDiscordFormat()" checked />
        <label for="discord-no-nitro">Without Nitro (2,000 char limit)</label>
      </div>
      <div class="discord-option">
        <input type="radio" id="discord-nitro" name="discord-format" value="4000" onchange="updateDiscordFormat()" />
        <label for="discord-nitro">With Nitro (4,000 char limit)</label>
      </div>
    </div>
    <div class="discord-sections" id="discord-sections"></div>
  </div>

</main>

<script>
let resultText = "";
let pollTimer  = null;
let logOffset  = 0;

function addRow(val) {
  if (val===undefined) val='';
  console.log('addRow called');
  const list = document.getElementById("url-list");
  console.log('list element:', list);
  const idx  = list.children.length + 1;
  const div  = document.createElement("div");
  div.className = "url-row";
  var html = '<span class="url-num">' + idx + '.</span>' +
    '<input type="text" placeholder="https://galaxyharvester.net/schematics.py/..." value="' + val + '" />' +
    '<input type="number" class="qty-input" min="1" value="1" />';
  div.innerHTML = html;
  list.appendChild(div);
  renumber();
  console.log('row added, now', list.children.length, 'rows');
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
  console.log('startScrape called');
  const schematics = getUrls();
  console.log('schematics:', schematics);
  if (!schematics.length) { alert("Please enter at least one schematic URL."); return; }

  document.getElementById("scrape-btn").disabled = true;
  document.getElementById("scrape-btn").innerHTML = '<span class="spinner"></span> Scraping...';
  document.getElementById("log-card").style.display   = "block";
  document.getElementById("result-card").style.display = "none";
  document.getElementById("discord-card").style.display = "none";
  document.getElementById("download-btn").style.display = "none";
  document.getElementById("log-box").innerHTML = "";
  logOffset = 0;

  console.log('sending fetch to /scrape');
  fetch("/scrape", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({schematics})
  }).then(r => {
    console.log('fetch response received:', r);
    pollTimer = setInterval(pollLog, 800);
  }).catch(e => {
    console.error('fetch error:', e);
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
          document.getElementById("discord-card").style.display = "block";
          updateDiscordFormat();
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

function formatForDiscord(text, charLimit) {
  const lines = text.split('\\n');
  const sections = [];
  let currentSection = '';
  const codeBlockPrefix = '```\\n';
  const codeBlockSuffix = '\\n```';

  lines.forEach(line => {
    const testLength = currentSection + line + '\\n';
    const totalLength = testLength.length + codeBlockPrefix.length + codeBlockSuffix.length;

    if (totalLength > charLimit && currentSection) {
      sections.push(currentSection.trim());
      currentSection = line + '\\n';
    } else {
      currentSection += line + '\\n';
    }
  });

  if (currentSection) {
    sections.push(currentSection.trim());
  }

  return sections;
}

function updateDiscordFormat() {
  const charLimit = document.querySelector('input[name="discord-format"]:checked').value;
  const sections = formatForDiscord(resultText, parseInt(charLimit));
  const container = document.getElementById('discord-sections');
  container.innerHTML = '';

  sections.forEach((section, idx) => {
    const div = document.createElement('div');
    div.className = 'discord-section';
    
    const header = document.createElement('div');
    header.className = 'discord-section-header';
    header.textContent = 'Message ' + (idx + 1) + ' of ' + sections.length + ' (' + section.length + ' chars)';
    
    const content = document.createElement('div');
    content.textContent = section;
    content.style.paddingTop = '28px';
    
    const btn = document.createElement('button');
    btn.className = 'discord-copy-btn';
    btn.textContent = '📋 Copy';
    btn.onclick = () => {
      const textToCopy = '```\\n' + section + '\\n```';
      navigator.clipboard.writeText(textToCopy).then(() => {
        const original = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => { btn.textContent = original; }, 1500);
      });
    };
    
    div.appendChild(header);
    div.appendChild(content);
    div.appendChild(btn);
    container.appendChild(div);
  });
}

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
