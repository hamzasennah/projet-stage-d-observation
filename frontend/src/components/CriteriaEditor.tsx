import { Plus, RotateCcw, Trash2 } from "lucide-react";
import type { CriteriaSheet, Criterion } from "../types";

type Props = {
  sheet: CriteriaSheet;
  onChange: (sheet: CriteriaSheet) => void;
  onReset: () => void;
};

const emptyCriterion: Criterion = {
  label: "Nouveau critere",
  weight: 0,
  description: "",
  keywords: [],
  minimum_evidence: 1,
};

export function CriteriaEditor({ sheet, onChange, onReset }: Props) {
  const weightTotal = sheet.criteria.reduce((total, item) => total + Number(item.weight), 0);

  function updateCriterion(index: number, patch: Partial<Criterion>) {
    const criteria = sheet.criteria.map((criterion, currentIndex) =>
      currentIndex === index ? { ...criterion, ...patch } : criterion,
    );
    onChange({ ...sheet, criteria });
  }

  function removeCriterion(index: number) {
    onChange({
      ...sheet,
      criteria: sheet.criteria.filter((_, currentIndex) => currentIndex !== index),
    });
  }

  return (
    <section className="panel criteria-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Fiche de test</p>
          <h2>{sheet.title}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onReset} title="Recharger">
          <RotateCcw size={18} />
        </button>
      </div>

      <label>
        Poste
        <input
          value={sheet.job_title}
          onChange={(event) => onChange({ ...sheet, job_title: event.target.value })}
        />
      </label>

      <label>
        Description
        <textarea
          value={sheet.job_description}
          onChange={(event) => onChange({ ...sheet, job_description: event.target.value })}
          rows={5}
        />
      </label>

      <div className="skill-grid">
        <label>
          Obligatoires
          <textarea
            value={sheet.required_skills.join(", ")}
            onChange={(event) =>
              onChange({ ...sheet, required_skills: splitList(event.target.value) })
            }
            rows={3}
          />
        </label>
        <label>
          Souhaitees
          <textarea
            value={sheet.preferred_skills.join(", ")}
            onChange={(event) =>
              onChange({ ...sheet, preferred_skills: splitList(event.target.value) })
            }
            rows={3}
          />
        </label>
      </div>

      <div className="criteria-toolbar">
        <span className={Math.abs(weightTotal - 100) < 0.01 ? "status-ok" : "status-warn"}>
          Poids total: {weightTotal}
        </span>
        <button
          className="secondary-button"
          type="button"
          onClick={() => onChange({ ...sheet, criteria: [...sheet.criteria, emptyCriterion] })}
        >
          <Plus size={17} />
          Ajouter
        </button>
      </div>

      <div className="criteria-list">
        {sheet.criteria.map((criterion, index) => (
          <div className="criterion-row" key={`${criterion.label}-${index}`}>
            <div className="criterion-main">
              <input
                value={criterion.label}
                onChange={(event) => updateCriterion(index, { label: event.target.value })}
              />
              <textarea
                value={criterion.keywords.join(", ")}
                onChange={(event) =>
                  updateCriterion(index, { keywords: splitList(event.target.value) })
                }
                rows={2}
              />
            </div>
            <div className="criterion-actions">
              <input
                className="weight-input"
                type="number"
                min="0"
                max="100"
                value={criterion.weight}
                onChange={(event) => updateCriterion(index, { weight: Number(event.target.value) })}
              />
              <button
                className="icon-button danger"
                type="button"
                onClick={() => removeCriterion(index)}
                title="Supprimer"
              >
                <Trash2 size={17} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

