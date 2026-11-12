import { ShipAtmosphere } from "@/components/ShipAtmosphere";
import { ShipNav } from "@/components/ShipNav";
import { PwaRegister } from "@/components/PwaRegister";

export default function ShipLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="ahoy-trail-root relative min-h-screen pb-10">
      <PwaRegister />
      <ShipAtmosphere />
      <div className="relative z-10">
        <ShipNav />
        {children}
      </div>
    </div>
  );
}
