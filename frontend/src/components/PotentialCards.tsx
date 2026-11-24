import { formatDecimal } from "../labels";

type Props = {
  potentialTotal: string;
  potentialDated: string;
  potentialUndated: string;
};

/** GRES-06: the potential points in three small cards, only when there is any potential. */
export function PotentialCards({ potentialTotal, potentialDated, potentialUndated }: Props) {
  if (!(Number(potentialTotal) > 0)) return null;
  return (
    <dl className="potential-cards">
      <div>
        <dt>Pontuação potencial</dt>
        <dd>{formatDecimal(potentialTotal)}</dd>
      </div>
      <div>
        <dt>Potencial com data no interstício</dt>
        <dd>{formatDecimal(potentialDated)}</dd>
      </div>
      <div>
        <dt>Potencial sem data — aguardando revisão</dt>
        <dd>{formatDecimal(potentialUndated)}</dd>
      </div>
    </dl>
  );
}
