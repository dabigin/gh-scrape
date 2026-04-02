# Galaxy Harvester Scraper - Electron Desktop App

A desktop application for scraping schematic resources from the Star Wars Galaxies Galaxy Harvester website.

## Features

- ✅ Add multiple schematic URLs to scrape at once
- ✅ Set custom quantities for each schematic
- ✅ View detailed resource breakdowns
- ✅ Grand total of all resources needed
- ✅ Download results as TXT file
- ✅ Copy results to clipboard

## Installation

### Prerequisites

- Node.js 14+ and npm

### Setup

1. Navigate to the project directory:
```bash
cd "d:\SWGNB Resources\Galaxy Harvester Scraping"
```

2. Install dependencies:
```bash
npm install
```

## Running the App

### Development Mode
```bash
npm start
```

This will launch the Electron app with the DevTools open.

### Building for Distribution

#### Windows
```bash
npm run build-win
```

#### macOS
```bash
npm run build-mac
```

#### Linux
```bash
npm run build-linux
```

The built installers will be available in the `dist/` directory.

## Downloads

### Pre-built Installers

After running `npm run build-win`, you can find the compiled executables in the `dist/` folder:

- **[Galaxy Harvester Scraper Setup 1.0.0.exe](dist/Galaxy%20Harvester%20Scraper%20Setup%201.0.0.exe)** - Full installer (recommended for distribution)
- **[Galaxy Harvester Scraper 1.0.0.exe](dist/Galaxy%20Harvester%20Scraper%201.0.0.exe)** - Portable version (no installation required)

**Direct Path:** `D:\SWGNB Resources\Galaxy Harvester Scraping\dist\`

## Usage

1. Launch the app
2. Enter schematic URLs (full URLs or just the slug)
3. Set the quantity for each schematic (how many you want to craft)
4. Click "Scrape Schematics"
5. View results and download or copy to clipboard

## Project Structure

```
├── main.js              # Electron main process
├── preload.js          # IPC communication bridge
├── package.json        # Node.js dependencies
├── src/
│   ├── index.html      # UI layout
│   ├── renderer.js     # Frontend logic
│   ├── scraper.js      # Scraping logic
└── README.md           # This file
```

## Technologies

- **Electron** - Desktop application framework
- **Node.js** - JavaScript runtime
- **Cheerio** - HTML parsing
- **Axios** - HTTP requests

## Notes

- The app respects rate limits when scraping (500ms delay between requests)
- Results are cached to avoid redundant requests
- All scraping is done locally without sending data to external servers (except to galaxyharvester.net for data)

## License

MIT
