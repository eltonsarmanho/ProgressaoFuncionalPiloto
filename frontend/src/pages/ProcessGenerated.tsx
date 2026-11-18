import { useParams } from "react-router";
import { StepNav } from "../components/StepNav";

/** Etapa 5: the page of the generated documents. The blocks of each document come in later tasks. */
export function ProcessGenerated() {
  const { id = "" } = useParams();
  return (
    <>
      <StepNav current={5} processId={id} />
      <h1>Etapa 5 · Documentos gerados</h1>
    </>
  );
}
