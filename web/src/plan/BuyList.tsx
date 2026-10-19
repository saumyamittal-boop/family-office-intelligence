import type { Strategy } from "../api/client";
import { classColor, HATCH_CSS } from "../charts/colors";
import { cr } from "../format";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Status";

const KEEP_BELOW_CR = 0.5; // changes smaller than this are shown as "Keep", as in the Streamlit plan

/** What to buy and sell, by plain kind of fund (never a named product), with the illiquid holdings left as they are. */
export function BuyList({ strategy }: { strategy: Strategy }) {
  return (
    <Card title="What to buy and sell" subtitle={`To run the family's money as Strategy ${strategy.letter}`}>
      <ul className="buy-list">
        {strategy.action_plan.map((row) => (
          <li key={row.asset_class} className="buy-row">
            <span className="swatch" style={{ background: classColor(row.asset_class) }} aria-hidden="true" />
            <span className="buy-main">
              <b>{row.instrument_name}</b>
              <span className="hint">{row.instrument_note}</span>
              <span className="hint">
                {cr(row.current_cr)} now &rarr; <b>{cr(row.recommended_cr)}</b>
              </span>
            </span>
            <span className="buy-end">
              {Math.abs(row.change_cr) < KEEP_BELOW_CR ? (
                <Badge>Keep</Badge>
              ) : row.change_cr > 0 ? (
                <Badge tone="good">Buy {cr(row.change_cr)}</Badge>
              ) : (
                <Badge tone="bad">Sell {cr(-row.change_cr)}</Badge>
              )}
            </span>
          </li>
        ))}
        <li className="buy-row">
          <span className="swatch" style={{ background: HATCH_CSS }} aria-hidden="true" />
          <span className="buy-main">
            <b>{strategy.illiquid_name}</b>
            <span className="hint">{strategy.illiquid_note}</span>
            <span className="hint">{cr(strategy.illiquid_cr)}</span>
          </span>
          <span className="buy-end">
            <Badge>Keep</Badge>
          </span>
        </li>
      </ul>
      <p className="hint">Kinds of product, not specific recommendations. Illustrative, on synthetic data.</p>
    </Card>
  );
}
