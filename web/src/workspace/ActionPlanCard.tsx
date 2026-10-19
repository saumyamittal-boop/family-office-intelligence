import type { Schemas } from "../api/client";
import { cr, signedCr } from "../format";
import { Card } from "../ui/Card";
import { Icon } from "../ui/Icon";
import { Badge } from "../ui/Status";

type Row = Schemas["ActionRow"];
const THRESHOLD_CR = 0.5; // ignore changes smaller than this, as the Streamlit app does

/** What to buy and sell, in rupees, to move from today's holdings to the chosen mix. Illiquid holdings stay as they are. */
export function ActionPlanCard({ rows, label }: { rows: Row[]; label: string }) {
  const moves = rows
    .filter((r) => Math.abs(r.change_cr) > THRESHOLD_CR)
    .sort((a, b) => Math.abs(b.change_cr) - Math.abs(a.change_cr));
  const buys = moves.filter((r) => r.change_cr > 0).reduce((sum, r) => sum + r.change_cr, 0);
  const sells = -moves.filter((r) => r.change_cr < 0).reduce((sum, r) => sum + r.change_cr, 0);

  return (
    <Card title="What to buy and sell" subtitle={`To move from today's holdings to the ${label} mix`}>
      <div className="stack-lg">
        <div className="pills">
          <Badge tone="good">Buy {cr(buys)}</Badge>
          <Badge tone="bad">Sell {cr(sells)}</Badge>
          <Badge>Illiquid holdings unchanged</Badge>
        </div>
        {moves.length === 0 ? (
          <p className="muted">Nothing to change: today's holdings are within {cr(THRESHOLD_CR)} of this mix in every class.</p>
        ) : (
          <ul className="plan-list">
            {moves.map((r) => (
              <li key={r.asset_class} className={`plan-row ${r.change_cr > 0 ? "plan-buy" : "plan-sell"}`}>
                <span>
                  <span className="kind">
                    <Icon name={r.change_cr > 0 ? "plus" : "minus"} size={14} /> {r.change_cr > 0 ? "Buy" : "Sell"}
                  </span>{" "}
                  {r.asset_class}
                </span>
                <span className="muted num">
                  {cr(r.current_cr, 0)} to {cr(r.recommended_cr, 0)}
                </span>
                <span className="delta">{signedCr(r.change_cr)}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="hint">Kinds of asset, not specific products. Illustrative, on synthetic data.</p>
      </div>
    </Card>
  );
}
