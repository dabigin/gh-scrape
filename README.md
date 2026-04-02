# Galaxy Harvester Scraper GUI

A user-friendly web interface for scraping schematic resource requirements from Galaxy Harvester (galaxyharvester.net).

## Features

- ✅ **Multiple Schematics** - Add as many schematic URLs as you need
- ✅ **Quantity Control** - Specify how many of each item you want to craft
- ✅ **Resource Breakdown** - See all materials needed for each schematic
- ✅ **Subcomponent Expansion** - Automatically shows materials for components
- ✅ **Grand Total** - Combined resource count for all schematics
- ✅ **Download Results** - Save breakdown as a text file (.txt)
- ✅ **Easy to Use** - Clean, intuitive web interface

## Quick Start with VS Code

### Step 1: Clone the Repository

1. Open **Visual Studio Code**
2. Press **Ctrl + Shift + `** or go to **View** → **Terminal** to open the integrated terminal
3. Choose a location where you want to save the project, for example:
   ```bash
   cd Desktop
   ```
   or
   ```bash
   cd Documents
   ```
4. Clone the repository by typing:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Galaxy-Harvester-Scraper.git
   ```
   Replace `YOUR_USERNAME` with the actual GitHub username/repo owner
5. Navigate into the project folder:
   ```bash
   cd Galaxy-Harvester-Scraper
   ```

### Step 2: Open the Project in VS Code

1. In the terminal (from Step 1), type:
   ```bash
   code .
   ```
   This opens the current folder in VS Code
   
   **Alternative:** In VS Code, go to **File** → **Open Folder** and select the cloned `Galaxy-Harvester-Scraper` folder

### Step 3: Open the Integrated Terminal

1. In VS Code, press **Ctrl + `** (backtick/grave accent) to open the integrated terminal
   - **Alternative:** Go to **View** → **Terminal**
2. The terminal will open at the bottom of VS Code (you should already be in the project folder)

### Step 4: Check Python Installation

In the terminal, type:
```bash
python --version
```

- If you see a version number (3.6 or higher), Python is installed ✅
- If you see an error, download Python from https://www.python.org/downloads/ (check "Add to PATH" during installation)

### Step 5: Install Dependencies

In the VS Code terminal, type:
```bash
pip install -r requirements.txt
```

This will install:
- **Flask** - Web framework for the interface
- **requests** - For fetching Galaxy Harvester pages  
- **beautifulsoup4** - For parsing HTML

Wait for it to complete (you'll see "Successfully installed..." messages).

### Step 6: Run the Application

In the same terminal, type:
```bash
python gh_scraper_gui_fixed.py
```

You should see:
```
 * Running on http://localhost:8000
 * Press Ctrl+C to stop the server.
```

Your web browser will automatically open with the scraper interface.

**To stop the server:** Press **Ctrl+C** in the terminal



## How to Use

### Adding Schematics

1. In the web interface that opened, you'll see input fields for schematic URLs
2. Paste a Galaxy Harvester schematic URL, for example:
   ```
   https://www.galaxyharvester.net/schematics.py/food_drink_vasarian_brandy
   ```
3. Set the **Quantity** - how many of this item you want to craft
4. Click **"+ Add more links"** to add additional schematics

### Scraping Resources

1. After entering your URLs and quantities, click **"Scrape Schematics"**
2. The interface will fetch all the information and display:
   - A detailed breakdown for each schematic
   - All subcomponents and their materials
   - A grand total of all resources needed
   - A list of unique resources required

### Downloading Results

1. After scraping, scroll to the results section
2. Click **"📥 Download as TXT"** to save the breakdown to your computer
3. The file will be named `scraped_resources.txt`

## Requirements Explained

The `requirements.txt` file contains these Python packages:

| Package | Purpose |
|---------|---------|
| `flask` | Web framework that powers the GUI interface |
| `requests` | Fetches pages from Galaxy Harvester website |
| `beautifulsoup4` | Parses HTML to extract resource data |

## Example URLs

Here are some example Galaxy Harvester schematic URLs you can use:

- `https://www.galaxyharvester.net/schematics.py/chemistry_medpack_enhance_poison_c`
- `https://www.galaxyharvester.net/schematics.py/food_drink_vasarian_brandy`
- `https://www.galaxyharvester.net/schematics.py/chemistry_component_infection_amplifier_advanced`

## Troubleshooting

### Issue: "python is not recognized" error
**Solution:**
- Python is not installed or not in your system PATH
- Download from https://www.python.org/downloads/
- **Important:** During installation, check the box "Add Python to PATH"
- Restart VS Code after installing Python

### Issue: "No module named 'flask'" or similar error
**Solution:**
- The requirements weren't installed properly
- In VS Code terminal, run: `pip install -r requirements.txt`
- Make sure the install completes with "Successfully installed..." messages

### Issue: Browser doesn't open automatically
**Solution:**
- The server is running, but your browser didn't launch automatically
- Manually open your browser and go to: `http://localhost:8000`

### Issue: Can't stop the server with Ctrl+C
**Solution:**
- Try pressing Ctrl+C again
- Or close the terminal in VS Code and open a new one

### Issue: "Address already in use" error
**Solution:**
- Another process is using port 8000
- In VS Code terminal, press Ctrl+C to stop the current server
- Wait a few seconds and try running the script again

## File Structure

```
Galaxy Harvester Scraping/
├── gh_scraper_gui_fixed.py      # Main application (what you run)
├── requirements.txt              # Python dependencies (installed with pip)
├── README.md                      # This file
└── Procfile                       # For Render deployment (optional)
```

## Restarting the Application

If you need to restart the scraper:

1. In VS Code terminal, press **Ctrl+C** to stop the server
2. Type the same command again:
   ```bash
   python gh_scraper_gui_fixed.py
   ```
3. The web interface will open again

## Notes

- The scraper respects Galaxy Harvester's server and includes appropriate delays
- All requests are read-only (no data is modified on Galaxy Harvester)
- Results are processed locally on your machine
- Internet connection is required to fetch data from Galaxy Harvester

## License

This tool is for personal use with Galaxy Harvester data scraped from publicly available pages.

