import { PhBookOpenText, PhFolders, PhGearSix, PhHouse } from "@phosphor-icons/vue";

export const NAV = [
  { name: "home", to: "/", label: "nav.home", icon: PhHouse },
  { name: "library", to: "/library", label: "nav.library", icon: PhFolders },
  { name: "words", to: "/words", label: "nav.words", icon: PhBookOpenText },
  { name: "settings", to: "/settings", label: "nav.settings", icon: PhGearSix },
] as const;
