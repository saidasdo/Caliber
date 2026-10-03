import { useState } from "react";
import { Navigate, Link, useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { Modal } from "../components/ui/Modal";
import { KpiBand } from "../components/overview/KpiBand";
import { PriorityQueue } from "../components/overview/PriorityQueue";
import { LossByPlant } from "../components/overview/LossByPlant";
import { LossByPlantChart } from "../components/overview/LossByPlantChart";
import { Heatmap } from "../components/overview/Heatmap";
import { FollowUpPipeline } from "../components/overview/FollowUpPipeline";
import { TopAlertsBusiness } from "../components/overview/TopAlertsBusiness";
import { OverdueEscalations } from "../components/overview/OverdueEscalations";

const PANEL_HEIGHT = 420;

// A dashboard named "Overview" should read in 5 to 10 seconds, not require scrolling to find
// out what's happening: the whole page is sized to fit one screen (KPI band + a fixed-height
// row of panels), lists that used to run 12+ rows deep are now charts, and anything that's
// genuinely a longer read (the full loss-by-plant numbers, the business-language alert list,
// overdue escalations) opens in a pop-up instead of pushing the page taller.
//
// Phase 10 section 2: Overview is Executive's landing page only. Plant manager is redirected
// to their plant page (an explicit "View all plants" link, ?all=1, opts back into this page
// with money redacted for every plant but their own); Engineer is redirected to the top
// alert's equipment page instead of ever seeing this page at all.
export function OverviewPage() {
  const { overview, role, selectedPlant, topAlertTag } = useAppState();
  const [searchParams] = useSearchParams();
  const viewAll = searchParams.get("all") === "1";
  const [modal, setModal] = useState<"loss" | "alerts" | "escalations" | null>(null);
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

  const { kpi_band, priority_queue, loss_by_plant, heatmap, follow_up_pipeline } = overview.data;

  return (
    <div className="flex h-full flex-col gap-1.5 overflow-hidden">
      {role === "Plant manager" && viewAll && (
        <div className="flex items-center justify-between border border-line bg-canvas px-2 py-1 text-12 text-mute">
          Viewing all plants. Money is shown only for {selectedPlant}.
          <Link to={`/plant/${selectedPlant}`} className="text-blue">
            Back to {selectedPlant}
          </Link>
        </div>
      )}

      <KpiBand data={kpi_band} />

      <div className="grid grid-cols-12 gap-1.5" style={{ height: PANEL_HEIGHT }}>
        <div className="col-span-3 min-h-0">
          <PriorityQueue
            rows={priority_queue}
            headerAction={
              role === "Executive" && (
                <button type="button" onClick={() => setModal("alerts")} className="normal-case text-blue">
                  Business view
                </button>
              )
            }
          />
        </div>
        <div className="col-span-4 flex min-h-0 flex-col border border-line bg-paper">
          <button
            type="button"
            onClick={() => setModal("loss")}
            className="border-b border-line px-2 py-1.5 text-left text-12 font-semibold uppercase tracking-wide text-mute hover:bg-canvas"
          >
            Loss by plant
          </button>
          <div className="min-h-0 flex-1 p-1">
            <LossByPlantChart plants={loss_by_plant} />
          </div>
        </div>
        <div className="col-span-3 min-h-0">
          <Heatmap cells={heatmap} />
        </div>
        <div className="col-span-2 min-h-0">
          <FollowUpPipeline
            data={follow_up_pipeline}
            headerAction={
              role === "Executive" && (
                <button type="button" onClick={() => setModal("escalations")} className="normal-case text-blue">
                  Escalations
                </button>
              )
            }
          />
        </div>
      </div>

      {modal === "loss" && (
        <Modal title="Loss by plant" onClose={() => setModal(null)}>
          <LossByPlant plants={loss_by_plant} />
        </Modal>
      )}
      {modal === "alerts" && (
        <Modal title="Top alerts" onClose={() => setModal(null)}>
          <TopAlertsBusiness rows={priority_queue} />
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
