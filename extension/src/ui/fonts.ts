// Bundled fonts (no CDN): IBM Plex Sans Arabic for text, Reem Kufi for the wordmark and headings.
import "@fontsource/ibm-plex-sans-arabic/arabic-400.css";
import "@fontsource/ibm-plex-sans-arabic/latin-400.css";
import "@fontsource/ibm-plex-sans-arabic/arabic-500.css";
import "@fontsource/ibm-plex-sans-arabic/latin-500.css";
import "@fontsource/ibm-plex-sans-arabic/arabic-600.css";
import "@fontsource/ibm-plex-sans-arabic/latin-600.css";
import "@fontsource/ibm-plex-sans-arabic/arabic-700.css";
import "@fontsource/ibm-plex-sans-arabic/latin-700.css";
import "@fontsource/reem-kufi/arabic-600.css";
import "@fontsource/reem-kufi/latin-600.css";
import "./tokens.css";

// The subtitle fonts the user can choose, for the preview in the options page and the popup.
import { extraFontFaces } from "@/shared/fonts";

const style = document.createElement("style");
style.textContent = extraFontFaces((f) => `/fonts/${f}`);
document.head.appendChild(style);
