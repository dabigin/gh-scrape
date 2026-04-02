const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  scrapeSchematics: async (urls) => {
    try {
      return await ipcRenderer.invoke('scrape-schematics', urls);
    } catch (error) {
      console.error('IPC Error:', error);
      throw error;
    }
  },
  onScrapeProgress: (callback) => {
    return ipcRenderer.on('scrape-progress', (event, data) => callback(data));
  }
});

// Log that preload has been loaded
window.addEventListener('DOMContentLoaded', () => {
  console.log('API exposed:', window.api ? 'SUCCESS' : 'FAILED');
});
