import { Outlet } from "react-router-dom";
import { IconRail } from "./IconRail";
import { AssetTree } from "./AssetTree";
import { Breadcrumb } from "./Breadcrumb";
import { PageTabs } from "./PageTabs";
import { ReplayClock } from "./ReplayClock";
import { RoleSwitch } from "./RoleSwitch";

export function AppShell() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas">
      <IconRail />
      <AssetTree />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-paper px-3 py-2">
          <Breadcrumb />
          <ReplayClock />
        </header>
        <PageTabs />
        <main className="flex-1 overflow-y-auto p-2 pb-8">
          <Outlet />
        </main>
      </div>
      <RoleSwitch />
    </div>
  );
}
