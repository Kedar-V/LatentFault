import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const { fontFamily: sans } = loadInter("normal", { weights: ["400", "600", "700", "800"], subsets: ["latin"] });
export const { fontFamily: mono } = loadMono("normal", { weights: ["500", "700"], subsets: ["latin"] });

export const C = {
  bg: "#07162B",
  navy: "#0B1F3A",
  panel: "#11294A",
  ink: "#E7EEF6",
  muted: "#93A6BF",
  coral: "#FF6B57",
  coralDeep: "#D2483C",
  teal: "#2BB3BF",
  green: "#2ECC71",
};
