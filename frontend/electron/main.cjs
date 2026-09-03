const path = require('path')
const { app, BrowserWindow, ipcMain } = require('electron')

const MINI_MIN_WIDTH = 280
const MINI_MAX_WIDTH = 520
const MINI_MIN_HEIGHT = 130
const MINI_MAX_HEIGHT = 760

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function resizeMiniWindow(win, payload = {}) {
  if (!win || win.isDestroyed()) {
    return
  }

  const width = clamp(
    Math.ceil(payload.width || MINI_MIN_WIDTH),
    MINI_MIN_WIDTH,
    MINI_MAX_WIDTH
  )
  const height = clamp(
    Math.ceil(payload.height || MINI_MIN_HEIGHT),
    MINI_MIN_HEIGHT,
    MINI_MAX_HEIGHT
  )

  win.setContentSize(width, height)
}

function createWindow() {
  const win = new BrowserWindow({
    width: 300,
    height: 150,
    minWidth: MINI_MIN_WIDTH,
    minHeight: MINI_MIN_HEIGHT,
    maxWidth: MINI_MAX_WIDTH,
    maxHeight: MINI_MAX_HEIGHT,
    useContentSize: true,
    resizable: true,
    movable: true,
    maximizable: false,
    fullscreenable: false,
    minimizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    autoHideMenuBar: true,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs')
    }
  })

  win.loadURL('http://localhost:5173?mini=1')
}

ipcMain.on('mini-window:resize-to-content', (event, payload) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  resizeMiniWindow(win, payload)
})

app.whenReady().then(() => {
  createWindow()
})
