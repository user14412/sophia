import { FileUp, Upload } from 'lucide-react';
import { useState } from 'react';

interface UploadPanelProps {
  sessionId: string;
  loading: boolean;
  onUploadSource: (file: File) => Promise<void>;
  onUploadStageInput: (stage: string, file: File) => Promise<void>;
}

const STAGE_INPUTS = [
  { value: 'topic', label: 'topic.json' },
  { value: 'director', label: 'director.json' },
  { value: 'agent_speechers', label: 'script_items.json' },
  { value: 'voice', label: 'voice.json' },
  { value: 'image', label: 'images.json' },
  { value: 'editor', label: 'video.json' }
];

export function UploadPanel({ sessionId, loading, onUploadSource, onUploadStageInput }: UploadPanelProps) {
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [stageFile, setStageFile] = useState<File | null>(null);
  const [stage, setStage] = useState('agent_speechers');

  return (
    <section className="panel">
      <div className="panelHeader">
        <FileUp size={16} />
        <h2>Uploads</h2>
      </div>

      <div className="uploadBlock">
        <div>
          <strong>Start from source</strong>
          <p>Upload a .txt, .md, or .json file for this session.</p>
        </div>
        <input
          type="file"
          accept=".txt,.md,.json"
          onChange={(event) => setSourceFile(event.target.files?.[0] ?? null)}
        />
        <button disabled={loading || !sessionId.trim() || !sourceFile} onClick={() => sourceFile && onUploadSource(sourceFile)}>
          <Upload size={15} />
          <span>Upload Source</span>
        </button>
      </div>

      <div className="uploadBlock">
        <div>
          <strong>Import stage input</strong>
          <p>Upload a JSON file so one stage can be debugged directly.</p>
        </div>
        <select value={stage} onChange={(event) => setStage(event.target.value)}>
          {STAGE_INPUTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
        <input type="file" accept=".json" onChange={(event) => setStageFile(event.target.files?.[0] ?? null)} />
        <button
          disabled={loading || !sessionId.trim() || !stageFile}
          onClick={() => stageFile && onUploadStageInput(stage, stageFile)}
        >
          <Upload size={15} />
          <span>Import Input</span>
        </button>
      </div>
    </section>
  );
}
