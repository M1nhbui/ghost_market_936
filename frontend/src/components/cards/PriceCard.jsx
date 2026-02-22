import StatCard from "./StatCard"
import PriceLineChart from "../charts/PriceLineChart"
import { fmtMoney, fmtPct } from "../../lib_with_format/format"

function changePillClass(changePct) {
	if (changePct > 0.01) return "bg-emerald-50 text-emerald-700 border-emerald-200"
	if (changePct < -0.01) return "bg-rose-50 text-rose-700 border-rose-200"
	return "bg-slate-50 text-slate-700 border-slate-200"
}

export default function PriceCard({ data }) {
	const p = data.price

	return (
		<div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
			<div className="flex items-start justify-between gap-4">
				<div>
					<div className="text-sm font-semibold text-slate-900">Live Price</div>
					<div className="mt-1 text-xs text-slate-500">
						Latest snapshot for <span className="font-medium text-slate-700">{data.ticker.label}</span>
					</div>
				</div>

				<span className={["inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-wide", changePillClass(p.changePct)].join(" ")}>{fmtPct(p.changePct)}</span>
			</div>

			<div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
				<StatCard title="Last Price" value={fmtMoney(p.last)} sub="Most recent tick" />
				<StatCard title="24h Change" value={fmtPct(p.changePct)} sub="Demo percent" />
				<StatCard title="Series Pts" value={p.series.length} sub="Mini trend" />
			</div>

			<div className="mt-5">
				<PriceLineChart series={p.series} />
			</div>
		</div>
	)
}
