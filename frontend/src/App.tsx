import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";
import { OverviewPage } from "./pages/OverviewPage";
import { PlantPage } from "./pages/PlantPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { DiagnosisPage } from "./pages/DiagnosisPage";
import { ActionsPage } from "./pages/ActionsPage";
import { BacktestPage } from "./pages/BacktestPage";
import { DataPage } from "./pages/DataPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="plant/:plantCode" element={<PlantPage />} />
          <Route path="equipment/:tag" element={<EquipmentPage />} />
          <Route path="diagnosis" element={<DiagnosisPage />} />
          <Route path="actions" element={<ActionsPage />} />
          <Route path="backtest" element={<BacktestPage />} />
          <Route path="data" element={<DataPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
