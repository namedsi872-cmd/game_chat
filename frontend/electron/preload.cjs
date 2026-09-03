const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronMiniWindow', {
  resizeToContent(payload) {
    ipcRenderer.send('mini-window:resize-to-content', payload)
  }
})
