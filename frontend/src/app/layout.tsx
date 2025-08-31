import type { Metadata } from "next"
import "./globals.css"
import { Navbar } from "@/components/navbar"

// External styles to mirror Flask templates
const EXTERNAL_STYLES = (
  <>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" />
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.10.5/font/bootstrap-icons.min.css" rel="stylesheet" />
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  {/* Local copy of the backend styles for visual parity */}
  <link rel="stylesheet" href="/style.css" />
  </>
)

export const metadata: Metadata = {
  title: {
    default: "HomeGrubHub - Smart Meal Planning & Recipe Organization App",
    template: "%s - HomeGrubHub"
  },
  description: "Plan meals, track nutrition, and organize recipes with HomeGrubHub.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        {EXTERNAL_STYLES}
      </head>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Navbar />
        {children}

        {/* Load bootstrap JS at end of body for interactive components (optional) */}
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
      </body>
    </html>
  )
}
