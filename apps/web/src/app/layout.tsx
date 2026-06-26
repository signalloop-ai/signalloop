import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignalLoop MVP",
  description: "Candidate assessment workspace and employer review portal for SignalLoop MVP",
};

const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

// Clerk sign-in modal + UserButton popover. We keep Clerk's default (readable)
// surface and only tint the primary action to our blue — forcing a dark
// `colorBackground` here made the modal text and the "Continue with Google"
// button invisible (Clerk's `dark` base theme did not apply in this version).
const clerkAppearance = {
  variables: {
    colorPrimary: "#3b82f6",
    borderRadius: "8px",
  },
} as const;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const body = <body>{children}</body>;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      {clerkPublishableKey ? (
        <ClerkProvider publishableKey={clerkPublishableKey} appearance={clerkAppearance}>
          {body}
        </ClerkProvider>
      ) : (
        body
      )}
    </html>
  );
}
