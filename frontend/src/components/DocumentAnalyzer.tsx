import { FileCheck2, Files, Play } from "lucide-react";
import { useState } from "react";

type Props = {
  disabled: boolean;
  onAnalyze: (criteriaFile: File, files: File[]) => void;
};

export function DocumentAnalyzer({ disabled, onAnalyze }: Props) {
  const [criteriaFile, setCriteriaFile] = useState<File | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const canAnalyze = Boolean(criteriaFile && files.length);

  return (
    <section className="panel document-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Entrees du systeme</p>
          <h2>Classement par fiche de test</h2>
        </div>
      </div>

      <label className="file-input-card">
        <span>
          <FileCheck2 size={19} />
          Fiche de test / criteres
        </span>
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          disabled={disabled}
          onChange={(event) => setCriteriaFile(event.target.files?.[0] ?? null)}
        />
        <small>{criteriaFile ? criteriaFile.name : "PDF contenant les criteres du poste"}</small>
      </label>

      <label className="file-input-card">
        <span>
          <Files size={19} />
          CV candidats
        </span>
        <input
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          disabled={disabled}
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
        />
        <small>
          {files.length
            ? files.map((file) => file.name).join(", ")
            : "Un ou plusieurs CV PDF a classer"}
        </small>
      </label>

      <button
        className="primary-button full-width"
        type="button"
        disabled={disabled || !canAnalyze}
        onClick={() => criteriaFile && onAnalyze(criteriaFile, files)}
      >
        <Play size={17} />
        Analyser et classer
      </button>
    </section>
  );
}

