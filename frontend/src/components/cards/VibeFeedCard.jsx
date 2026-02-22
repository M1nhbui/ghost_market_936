import StatCard from "./StatCard"
import VibeTable from "../tables/VibeTable"

function signalPill(signalUp) {
	return signalUp ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-50 text-slate-700 border-slate-200"
}

export default function VibeFeedCard({ data }) {
	const s = data.stats

	return (
		<div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
			<div className="flex items-start justify-between gap-4">
				<div>
					<div className="text-sm font-semibold text-slate-900">Vibe Feed</div>
					<div className="mt-1 text-xs text-slate-500">
						Latest sentiment events for <span className="font-medium text-slate-700">{data.ticker.label}</span>
					</div>
				</div>

				<span className={["inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-wide", signalPill(s.signalUp)].join(" ")}>{s.signalUp ? "SIGNAL UP" : "NO STRONG SIGNAL"}</span>
			</div>

			<div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
				<StatCard title="Avg Sentiment" value={s.avgSentiment} sub="Rolling window" />
				<StatCard title="Sources" value={s.sources} sub="Platforms scanned" />
				<StatCard title="Events" value={s.eventsCount} sub={`Signal: ${s.eventsLabel}`} />
			</div>

			<div className="mt-5">
				<VibeTable rows={data.vibeFeed} />
			</div>
		</div>
	)
}
