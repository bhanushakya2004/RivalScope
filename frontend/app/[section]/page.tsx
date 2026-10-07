import { RivalScopeApp } from "../../components/rivalscope-app";

export default async function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  return <RivalScopeApp section={section} />;
}
