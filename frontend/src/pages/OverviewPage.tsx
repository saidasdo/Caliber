import { useState } from "react";
import { Navigate, Link, useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { Modal } from "../components/ui/Modal";
import { Headline } from "../components/overview/Headline";
import { NeedsAttention } from "../components/overview/NeedsAttention";
import { FollowUpHealth } from "../components/overview/FollowUpHealth";
import { ExecKpiTiles } from "../components/overview/ExecKpiTiles";
import { TopPlantsCard } from "../components/overview/TopPlantsCard";
import { LossByPlant } from "../components/overview/LossByPlant";
import { Heatmap } from "../components/overview/Heatmap";
import { FollowUpPipeline } from "../components/overview/FollowUpPipeline";
import { OverdueEscalations } from "../components/overview/OverdueEscalations";

// Executive Overview in three tiers, sized to one 1440 x 900 screen with no page scroll:
//   0. Headline: one generated sentence from the priority queue on the replay date.
//   1. Needs attention now (two thirds) and follow-up health (one third).
//   2. Four KPI tiles, one status line each.
//   3. Top plants by loss, and two buttons that open the heatmap and the follow-up pipeline.
// Detail lives in pop-ups. Money stays server-redacted, as before.
//
// Phase 10 section 2: Overview is Executive's landing page only. Plant manager is redirected to
// their plant page (an explicit "View all plants" link, ?all=1, opts back into this page with money
// redacted for every plant but their own); Engineer is redirected to the top alert's page.
export function OverviewPage() {
  const { overview, role, selectedPlant, topAlertTag } = useAppState();
  const [searchParams] = useSearchParams();
  const viewAll = searchParams.get("all") === "1";
  const [modal, setModal] = useState<"plants" | "heatmap" | "pipeline" | "escalations" | null>(null);
  useLogViewMoney("overview");

  if (!viewAll && role === "Plant manager" && selectedPlant) {
    return <Navigate to={`/plant/${selectedPlant}`} replace />;
  }
  if (!viewAll && role === "Engineer" && topAlertTag) {
    return <Navigate to={`/equipment/${topAlertTag}`} replace />;
  }

  if (overview.status === "loading") {
    return <div className="p-3 text-13 text-mute">Loading overview...</div>;
  }
  if (overview.status === "error") {
    return (
      <div className="border border-line bg-paper p-3 text-13 text-red">
        Could not load the overview: {overview.error}
        <div className="mt-1 text-12 text-mute">
          Is the API running? Start it with <code className="tabular">npm run api</code>.
        </div>
      </div>
    );
  }

  const { kpi_band, priority_queue, loss_by_plant, heatmap, follow_up_pipeline, follow_up_health } = overview.data;

  return (
    <div className="flex h-full flex-col gap-2 overflow-hidden pb-8">
      {role === "Plant manager" && viewAll && (
        <div className="flex items-center justify-between border border-line bg-canvas px-2 py-1 text-12 text-mute">
          Viewing all plants. Money is shown only for {selectedPlant}.
          <Link to={`/plant/${selectedPlant}`} className="text-blue">
            Back to {selectedPlant}
          </Link>
        </div>
      )}

      <Headline rows={priority_queue} />

      <div className="grid shrink-0 grid-cols-3 gap-1.5" style={{ height: 220 }}>
        <div className="col-span-2 min-h-0">
          <NeedsAttention rows={priority_queue} />
        </div>
        <div className="min-h-0">
          <FollowUpHealth
            rcaOverdue={follow_up_pipeline.rca_process_overdue}
            awaitingApproval={follow_up_health.awaiting_approval}
            openFollowUps={kpi_band.open_follow_ups}
            onReviewEscalations={() => setModal("escalations")}
          />
        </div>
      </div>

      <div className="shrink-0" style={{ height: 96 }}>
        <ExecKpiTiles
          kpi={kpi_band}
          production={kpi_band.production_vs_normal}
          energy={kpi_band.energy_proxy}
          emission={kpi_band.emission_kg}
        />
      </div>

      <div className="grid shrink-0 grid-cols-3 gap-1.5" style={{ height: 290 }}>
        <TopPlantsCard plants={loss_by_plant} onShowAll={() => setModal("plants")} />
        <Heatmap
          cells={heatmap}
          height={230}
          headerAction={<button type="button" onClick={() => setModal("heatmap")} className="border-l border-line px-1.5 py-0.5 text-12 text-blue">Open</button>}
        />
        <FollowUpPipeline
          hideOverdue
          data={follow_up_pipeline}
          headerAction={<button type="button" onClick={() => setModal("pipeline")} className="border-l border-line px-1.5 py-0.5 text-12 text-blue">Open</button>}
        />
      </div>

      {modal === "plants" && (
        <Modal title="Loss by plant, all plants" onClose={() => setModal(null)}>
          <LossByPlant plants={loss_by_plant} />
        </Modal>
      )}
      {modal === "heatmap" && (
        <Modal title="Plant by month" onClose={() => setModal(null)} wide>
          <div className="h-[520px]">
            <Heatmap cells={heatmap} />
          </div>
        </Modal>
      )}
      {modal === "pipeline" && (
        <Modal title="Follow-up pipeline" onClose={() => setModal(null)}>
          <FollowUpPipeline data={follow_up_pipeline} />
        </Modal>
      )}
      {modal === "escalations" && (
        <Modal title="Overdue escalations" onClose={() => setModal(null)}>
          <OverdueEscalations />
        </Modal>
      )}
    </div>
  );
}
