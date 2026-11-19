import { useState } from "react";
import { isValid } from "../activityList";
import type { Activity, DocumentSummary, ScoringGroup, ScoringRow } from "../api/types";
import { ActivityForm } from "./ActivityForm";
import { InvalidActivitiesSection } from "./InvalidActivitiesSection";
import { Modal } from "./Modal";
import { ValidActivitiesSection } from "./ValidActivitiesSection";

/**
 * SEC-01, SEC-08, SEC-09, SEC-12: the two sections of the Etapa 3. It splits the list by the
 * validity the server sent and owns the edit dialog. A write never moves an activity by itself:
 * `onChanged` makes the parent reload the list, and the activity lands in the section its new
 * validity says (a corrected date, a reopened rejection), without reloading the page.
 */
export function ActivityWorkspace({
  processId,
  activities,
  rows,
  groups,
  documents,
  onChanged,
}: {
  processId: string;
  activities: Activity[];
  rows: ScoringRow[];
  groups: ScoringGroup[];
  documents: DocumentSummary[];
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState<Activity | null>(null);

  const done = () => {
    setEditing(null);
    onChanged();
  };

  return (
    <div className="activity-workspace">
      <ValidActivitiesSection
        processId={processId}
        activities={activities.filter(isValid)}
        rows={rows}
        groups={groups}
        documents={documents}
        onEdit={setEditing}
        onChanged={onChanged}
      />
      <InvalidActivitiesSection
        activities={activities.filter((a) => !isValid(a))}
        groups={groups}
        onEdit={setEditing}
        onChanged={onChanged}
      />
      {editing && (
        <Modal title="Editar atividade" onClose={() => setEditing(null)}>
          <ActivityForm
            key={`edit-${editing.id}`}
            processId={processId}
            groups={groups}
            activity={editing}
            onSaved={done}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </div>
  );
}
