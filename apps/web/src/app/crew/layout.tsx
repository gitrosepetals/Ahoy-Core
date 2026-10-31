import { CrewAtmosphere } from "@/components/CrewAtmosphere";

export default function CrewLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="ahoy-crew-root relative min-h-screen">
      <CrewAtmosphere />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
