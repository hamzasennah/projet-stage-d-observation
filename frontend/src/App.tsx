import { useEffect, useState } from "react";
import { Play, RefreshCcw } from "lucide-react";
import { analyzeDocuments, analyzeSeed, getDefaultCriteria, getSeedResumes } from "./api";
import { CriteriaEditor } from "./components/CriteriaEditor";
import { DocumentAnalyzer } from "./components/DocumentAnalyzer";
import { RankingTable } from "./components/RankingTable";
import { ResumeLibrary } from "./components/ResumeLibrary";
import type { CriteriaSheet, CandidateRanking, ResumeSeed } from "./types";

function App() {
  const [criteria, setCriteria] = useState<CriteriaSheet | null>(null);
  const [resumes, setResumes] = useState<ResumeSeed[]>([]);
  const [ranking, setRanking] = useState<CandidateRanking[]>([]);
  const [status, setStatus] = useState("Initialisation");
  const [busy, setBusy] = useState(false);

  async function loadInitialData() {
    setBusy(true);
    try {
      const [sheet, seedResumes] = await Promise.all([getDefaultCriteria(), getSeedResumes()]);
      setCriteria(sheet);
      setResumes(seedResumes);
      setStatus("Pret");
    } catch (error) {
      setStatus(messageFromError(error));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadInitialData();
  }, []);

  async function runSeedAnalysis() {
    if (!criteria) return;
    setBusy(true);
    try {
      const response = await analyzeSeed(criteria);
      setRanking(response.ranking);
      setStatus(`Analyse ${response.analysis_id ?? ""} terminee`);
    } catch (error) {
      setStatus(messageFromError(error));
    } finally {
      setBusy(false);
    }
  }

  async function runDocumentAnalysis(criteriaFile: File, files: File[]) {
    setBusy(true);
    try {
      const response = await analyzeDocuments(criteriaFile, files);
      setRanking(response.ranking);
      setStatus(`Classement ${response.analysis_id ?? ""} termine`);
    } catch (error) {
      setStatus(messageFromError(error));
    } finally {
      setBusy(false);
    }
  }

  if (!criteria) {
    return <main className="loading-shell">{status}</main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Resume Ranking RAG</p>
          <h1>Importer une fiche de test et classer les CV</h1>
        </div>
        <div className="topbar-actions">
          <span className={busy ? "status busy" : "status"}>{status}</span>
          <button className="secondary-button" type="button" onClick={loadInitialData} disabled={busy}>
            <RefreshCcw size={17} />
            Sync
          </button>
        </div>
      </header>

      <div className="document-grid">
        <DocumentAnalyzer disabled={busy} onAnalyze={runDocumentAnalysis} />
        <RankingTable ranking={ranking} />
      </div>

      <details className="advanced-section">
        <summary>Mode test avec base provisoire</summary>
        <div className="workspace-grid advanced-grid">
          <CriteriaEditor sheet={criteria} onChange={setCriteria} onReset={loadInitialData} />
          <div className="side-stack">
            <ResumeLibrary resumes={resumes} />
            <section className="panel">
              <div className="panel-header compact">
                <div>
                  <p className="eyebrow">Scenario seed</p>
                  <h2>{criteria.job_title}</h2>
                </div>
                <button
                  className="primary-button"
                  type="button"
                  onClick={runSeedAnalysis}
                  disabled={busy}
                >
                  <Play size={17} />
                  Classer la base
                </button>
              </div>
            </section>
          </div>
        </div>
      </details>
    </main>
  );
}

function messageFromError(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Erreur inattendue";
}

export default App;
