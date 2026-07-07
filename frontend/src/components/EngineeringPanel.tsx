import { Layers } from 'lucide-react';

export function EngineeringPanel() {
  return (
    <section className="panel engineering">
      <div className="panelHeader">
        <Layers size={18} />
        <h2>Engineering View</h2>
      </div>
      <div className="calloutGrid">
        <article>
          <h3>v3 Pipeline</h3>
          <p>Topic, Director, Agent Speechers, Voice, Image, Editor split the podcast workflow into inspectable stages.</p>
        </article>
        <article>
          <h3>Fixture / Mock</h3>
          <p>Demo runs stay offline, repeatable, and fast while preserving the same artifact shape used by the real path.</p>
        </article>
        <article>
          <h3>Stage Runner</h3>
          <p>Voice, image, and editor can be rerun from existing session artifacts without restarting the whole pipeline.</p>
        </article>
        <article>
          <h3>Manifest</h3>
          <p>Every run records stage status, config, and artifact locations for reporting and verification.</p>
        </article>
      </div>
    </section>
  );
}
