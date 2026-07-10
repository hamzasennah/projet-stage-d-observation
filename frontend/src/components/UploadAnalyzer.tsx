import { UploadCloud } from "lucide-react";

type Props = {
  disabled: boolean;
  onAnalyze: (files: File[]) => void;
};

export function UploadAnalyzer({ disabled, onAnalyze }: Props) {
  return (
    <section className="panel upload-panel">
      <div className="panel-header compact">
        <div className="title-with-icon">
          <UploadCloud size={18} />
          <h2>Upload CV</h2>
        </div>
      </div>
      <input
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md"
        disabled={disabled}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length) {
            onAnalyze(files);
          }
        }}
      />
    </section>
  );
}

