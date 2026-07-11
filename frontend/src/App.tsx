import { useState } from "react";
import { RefreshCcw } from "lucide-react";
import { analyzeDocuments } from "./api";
import { DocumentAnalyzer } from "./components/DocumentAnalyzer";
import { RankingTable } from "./components/RankingTable";
import type { CandidateRanking } from "./types";

function App() {
  const [ranking, setRanking] = useState<CandidateRanking[]>([]);
  const [status, setStatus] = useState("Pret");
  const [busy, setBusy] = useState(false);

  function resetAnalysis() {
    setRanking([]);
    setStatus("Pret");
  }

  async function runDocumentAnalysis(criteriaFile: File, files: File[]) {
    setBusy(true);
    try {
      const response = await analyzeDocuments(criteriaFile, files);
      setRanking(response.ranking);
      setStatus("Classement termine");
    } catch (error) {
      setStatus(messageFromError(error));
    } finally {
      setBusy(false);
    }
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
          <button className="secondary-button" type="button" onClick={resetAnalysis} disabled={busy}>
            <RefreshCcw size={17} />
            Reinitialiser
          </button>
        </div>
      </header>

      <div className="document-grid">
        <DocumentAnalyzer disabled={busy} onAnalyze={runDocumentAnalysis} />
        <RankingTable ranking={ranking} />
      </div>
    </main>
  );
}

function messageFromError(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Erreur inattendue";
}

export default App;
