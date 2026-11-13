/** The extension manifest. scripts/build.mjs writes it to dist/manifest.json. */
export function manifest(version: string) {
  return {
    manifest_version: 3,
    name: "__MSG_extName__",
    short_name: "__MSG_extShortName__",
    description: "__MSG_extDescription__",
    version,
    default_locale: "en",
    minimum_chrome_version: "116",
    homepage_url: "https://github.com/MohamedElnagar94/tarjuman",
    icons: {
      "16": "icons/icon-16.png",
      "32": "icons/icon-32.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png",
    },
    permissions: ["storage", "activeTab", "scripting", "offscreen", "tabCapture"],
    host_permissions: ["http://127.0.0.1/*", "http://localhost/*"],
    optional_host_permissions: ["<all_urls>"],
    background: { service_worker: "background.js", type: "module" },
    action: {
      default_popup: "popup.html",
      default_title: "__MSG_extShortName__",
      default_icon: {
        "16": "icons/icon-16.png",
        "32": "icons/icon-32.png",
        "48": "icons/icon-48.png",
      },
    },
    options_ui: { page: "options.html", open_in_tab: true },
    commands: {
      "toggle-translation": {
        suggested_key: { default: "Alt+Shift+A" },
        description: "__MSG_cmdToggle__",
      },
    },
    content_scripts: [
      {
        matches: ["*://*.youtube.com/*"],
        js: ["content.js"],
        run_at: "document_idle",
        all_frames: false,
      },
    ],
    // The overlay's subtitle font. Pages can load these files but nothing else of the extension.
    // use_dynamic_url: the files answer only at a per-session address (the one chrome.runtime.getURL
    // gives the content script), so a site can't detect the extension by fetching them at its fixed ID.
    web_accessible_resources: [{ resources: ["fonts/*.woff2"], matches: ["<all_urls>"], use_dynamic_url: true }],
  };
}
