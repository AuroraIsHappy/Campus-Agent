// Optional Electron desktop shell for the Campus frontend.
// Not required for `npm run build` (that's tsc + vite build only).
// To use the desktop shell: `npm i -D electron concurrently wait-on && npm run electron:dev`
// (Electron is intentionally NOT a default dependency, to keep install lean.)
const { app, BrowserWindow } = require("electron");
const path = require("path");

const DEV_URL = process.env.VITE_DEV_URL || "http://localhost:5173";

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    title: "Campus · 你的专属秘书",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  const isDev = !app.isPackaged;
  if (isDev) {
    win.loadURL(DEV_URL);
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
