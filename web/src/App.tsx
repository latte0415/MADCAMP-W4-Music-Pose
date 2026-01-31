import { useCallback, useState } from "react";
import { AudioUploader } from "./components/AudioUploader";
import { JsonUploader } from "./components/JsonUploader";
import { WaveformWithOverlay } from "./components/WaveformWithOverlay";
import { Tab04EnergyView } from "./components/Tab04EnergyView";
import { Tab05ClarityView } from "./components/Tab05ClarityView";
import { LayerFilterPanel } from "./components/LayerFilterPanel";
import type { EventPoint } from "./types/event";
import type { EnergyJsonData } from "./types/energyEvent";
import type { ClarityJsonData } from "./types/clarityEvent";
import "./App.css";

type TabId = "01" | "03" | "04" | "05";

const TABS: { id: TabId; label: string; samplePath: string }[] = [
  { id: "01", label: "01 Explore", samplePath: "/onset_beats.json" },
  { id: "03", label: "03 Visualize", samplePath: "/onset_events.json" },
  { id: "04", label: "04 Energy", samplePath: "/onset_events_energy.json" },
  { id: "05", label: "05 Clarity", samplePath: "/onset_events_clarity.json" },
];

function getUniqueLayers(events: EventPoint[]): string[] {
  const set = new Set(events.map((e) => e.layer));
  return Array.from(set);
}

function App() {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("01");
  type TabEvents = Partial<Record<TabId, Array<EventPoint>>>;
  type TabLayers = Partial<Record<TabId, Set<string>>>;
  const [tabEvents, setTabEvents] = useState<TabEvents>({});
  const [tabVisibleLayers, setTabVisibleLayers] = useState<TabLayers>({});
  const [tabEnergyData, setTabEnergyData] = useState<Partial<Record<TabId, EnergyJsonData | null>>>({});
  const [tabClarityData, setTabClarityData] = useState<Partial<Record<TabId, ClarityJsonData | null>>>({});

  const handleJsonLoaded = useCallback(
    (newEvents: EventPoint[]) => {
      setTabEvents((prev) => ({ ...prev, [activeTab]: newEvents }));
      setTabVisibleLayers((prev) => ({
        ...prev,
        [activeTab]: new Set(getUniqueLayers(newEvents)),
      }));
    },
    [activeTab]
  );

  const handleEnergyLoaded = useCallback(
    (data: EnergyJsonData | null) => {
      setTabEnergyData((prev) => ({ ...prev, [activeTab]: data }));
    },
    [activeTab]
  );

  const handleClarityLoaded = useCallback(
    (data: ClarityJsonData | null) => {
      setTabClarityData((prev) => ({ ...prev, [activeTab]: data }));
    },
    [activeTab]
  );

  const toggleLayer = useCallback(
    (layer: string) => {
      setTabVisibleLayers((prev) => {
        const current = prev[activeTab] ?? new Set<string>();
        const next = new Set(current);
        if (next.has(layer)) next.delete(layer);
        else next.add(layer);
        return { ...prev, [activeTab]: next };
      });
    },
    [activeTab]
  );

  return (
    <div className="app">
      <h1>측정 가능한 뷰 — MVP</h1>

      <section className="upload-section">
        <AudioUploader onAudioLoaded={setAudioUrl} />
      </section>

      <section className="tabs-section">
        <div className="tabs-header">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {TABS.map((tab) =>
          activeTab === tab.id ? (
            <div key={tab.id} className="tab-panel active">
              <div className="tab-upload">
                <JsonUploader
                  onJsonLoaded={handleJsonLoaded}
                  onEnergyLoaded={tab.id === "04" ? handleEnergyLoaded : undefined}
                  onClarityLoaded={tab.id === "05" ? handleClarityLoaded : undefined}
                  samplePath={tab.samplePath}
                  sampleLabel={`${tab.label} 샘플 로드`}
                />
              </div>

              <section className="controls-section">
                {tab.id === "04" ? (
                  <Tab04EnergyView
                    audioUrl={audioUrl}
                    energyData={tabEnergyData["04"] ?? null}
                  />
                ) : tab.id === "05" ? (
                  <Tab05ClarityView
                    audioUrl={audioUrl}
                    clarityData={tabClarityData["05"] ?? null}
                  />
                ) : (
                  <>
                    <WaveformWithOverlay
                      audioUrl={audioUrl}
                      events={tabEvents[tab.id] ?? []}
                      visibleLayers={tabVisibleLayers[tab.id] ?? new Set()}
                    />
                    <div className="filter-section">
                      {(tabEvents[tab.id] ?? []).length > 0 && (
                        <p className="events-count">
                          포인트 {(tabEvents[tab.id] ?? []).length}개 로드됨
                        </p>
                      )}
                      <LayerFilterPanel
                        layers={getUniqueLayers(tabEvents[tab.id] ?? [])}
                        visibleLayers={tabVisibleLayers[tab.id] ?? new Set()}
                        onToggle={toggleLayer}
                      />
                    </div>
                  </>
                )}
              </section>
            </div>
          ) : null
        )}
      </section>
    </div>
  );
}

export default App;
