import "./globals.css";

export const metadata = {
  title: "Whop Toolkit",
  description: "Extract clips and analyze transcripts from any video URL",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-ink text-mist">{children}</body>
    </html>
  );
}
