import { AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import type { CandidateRanking } from "../types";

type Props = {
  ranking: CandidateRanking[];
};

export function RankingTable({ ranking }: Props) {
  return (
    <section className="panel results-panel">
      <div className="panel-header compact">
        <div className="title-with-icon">
          <FileText size={18} />
          <h2>Classement</h2>
        </div>
        <span className="count">{ranking.length} resultats</span>
      </div>

      <div className="ranking-table">
        <div className="ranking-head">
          <span>Rang</span>
          <span>CV</span>
          <span>Score</span>
          <span>Signaux</span>
        </div>
        {ranking.map((candidate, index) => (
          <details className="ranking-row" key={candidate.candidate_id} open={index === 0}>
            <summary>
              <span className="rank">{index + 1}</span>
              <span>
                <strong>{candidate.resume_title}</strong>
                <small>{candidate.candidate_name}</small>
              </span>
              <span className="score-cell">
                <b>{Math.round(candidate.match_score)}</b>
                <span className="score-bar">
                  <i style={{ width: `${candidate.match_score}%` }} />
                </span>
              </span>
              <span className="signal-icons">
                <CheckCircle2 size={18} />
                <AlertTriangle size={18} />
              </span>
            </summary>

            <div className="ranking-details">
              <p>{candidate.summary}</p>
              <div className="detail-grid">
                <div>
                  <h3>Points forts</h3>
                  <ul>
                    {candidate.pros.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3>Points faibles</h3>
                  <ul>
                    {candidate.cons.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <h3>Detail des criteres</h3>
              <div className="criteria-breakdown">
                {candidate.criteria_breakdown.map((criterion) => (
                  <div className="breakdown-row" key={criterion.label}>
                    <span>{criterion.label}</span>
                    <b>
                      {criterion.score}/{criterion.weight}
                    </b>
                    <small>{criterion.matched_keywords.join(", ") || "Aucune preuve"}</small>
                  </div>
                ))}
              </div>

              <h3>Preuves</h3>
              <div className="evidence-list">
                {candidate.evidence.map((evidence) => (
                  <blockquote key={`${candidate.candidate_id}-${evidence.source}`}>
                    {evidence.text}
                  </blockquote>
                ))}
              </div>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

