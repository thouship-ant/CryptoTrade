import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from './providers'
import { AlertProvider } from '@/components/AlertProvider'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ConnectivityGate } from '@/components/ConnectivityGate'


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "ANT Crypto Robo Trade",
  description: "Automated Binance crypto trading bot - ANT Crypto Robo Trade",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/assets/images/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/assets/images/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/assets/images/icons/apple-touch-icon.png",
  },
};

export const viewport = {
  themeColor: "#F5B400",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      // The pre-hydration script below (and ThemeProvider after mount) toggles a
      // "dark" class on this element from localStorage, which the server can't know
      // during SSR - that's an intentional, expected mismatch on first render (the
      // standard fix for this exact dark-mode-FOUC pattern), not a real bug.
      suppressHydrationWarning
    >
      <head>
        <meta name="color-scheme" content="light dark" />
        <script dangerouslySetInnerHTML={{__html:'window.addEventListener("error",function(e){if(e.error instanceof DOMException&&e.error.name==="DataCloneError"&&e.message&&e.message.includes("PerformanceServerTiming")){e.stopImmediatePropagation();e.preventDefault()}},true);'}} />
        {/* Applies the saved light/dark mode before first paint, so the page never
            flashes the default theme before React hydrates and ThemeProvider takes over. */}
        <script dangerouslySetInnerHTML={{__html:'(function(){try{var t=localStorage.getItem("ant_theme_mode");if(t!=="light"&&t!=="dark"){t="dark";}if(t==="dark"){document.documentElement.classList.add("dark");}}catch(e){}})();'}} />
        <link rel="shortcut icon" href="/assets/images/favicon.ico" />
      </head>
      <body>
        <AlertProvider>
          <ThemeProvider>
            <Providers>
              <ConnectivityGate>{children}</ConnectivityGate>
            </Providers>
          </ThemeProvider>
        </AlertProvider>
      </body>
    </html>
  );
}
