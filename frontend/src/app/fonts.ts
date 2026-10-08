import { Golos_Text, Unbounded } from "next/font/google";

// Unbounded — широкие формы для заголовков и цен; Golos Text — текст. Оба с кириллицей.
export const unbounded = Unbounded({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "600", "700"],
  variable: "--font-unbounded",
});

export const golos = Golos_Text({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600"],
  variable: "--font-golos",
});

export const fontClasses = `${unbounded.variable} ${golos.variable}`;
