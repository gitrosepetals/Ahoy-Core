import { ShipNav } from "@/components/ShipNav";

export default function ShipLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen pb-24">
      {children}
      <ShipNav />
    </div>
  );
}
