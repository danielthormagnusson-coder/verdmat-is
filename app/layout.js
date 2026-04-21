import { Inter, Fraunces } from "next/font/google";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata = {
  title: "verdmat.is — Íslenskt fasteignaverðmat",
  description:
    "AI-studdur verðmatsvettvangur fyrir íslenskan fasteignamarkað. Verðmat byggt á 226.000 þinglýstum kaupsamningum og state-of-the-art LightGBM-módelum.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="is" className={`${inter.variable} ${fraunces.variable}`}>
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body>
        <Nav />
        {children}
        <Footer />
      </body>
    </html>
  );
}
