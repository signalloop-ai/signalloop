import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignalLoop MVP",
  description: "Candidate assessment workspace and employer review portal for SignalLoop MVP",
};

const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const body = <body>{children}</body>;

  return (
    <html lang="en" suppressHydrationWarning>
      {clerkPublishableKey ? (
        <ClerkProvider publishableKey={clerkPublishableKey}>{body}</ClerkProvider>
      ) : (
        body
      )}
    </html>
  );
}
