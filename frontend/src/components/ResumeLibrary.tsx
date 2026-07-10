import { Database } from "lucide-react";
import type { ResumeSeed } from "../types";

type Props = {
  resumes: ResumeSeed[];
};

export function ResumeLibrary({ resumes }: Props) {
  return (
    <section className="panel">
      <div className="panel-header compact">
        <div className="title-with-icon">
          <Database size={18} />
          <h2>Base provisoire</h2>
        </div>
        <span className="count">{resumes.length} CV</span>
      </div>
      <div className="resume-list">
        {resumes.map((resume) => (
          <article className="resume-item" key={resume.id}>
            <strong>{resume.title}</strong>
            <span>{resume.focus}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

