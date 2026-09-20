import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"Human Relay · Capability infrastructure",description:"The human capability layer for autonomous agents. Closed alpha."};
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
