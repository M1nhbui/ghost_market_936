function pillClasses(sentimentValue) {
	if (sentimentValue >= 0.35) return "bg-emerald-50 text-emerald-700 border-emerald-200"
	if (sentimentValue >= 0.1) return "bg-lime-50 text-lime-700 border-lime-200"
	if (sentimentValue >= -0.1) return "bg-slate-50 text-slate-700 border-slate-200"
	return "bg-rose-50 text-rose-700 border-rose-200"
}

export default function VibeTable({ rows }) {
	return (
		<div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
			<div className="max-h-[380px] overflow-auto">
				<table className="w-full text-left text-sm">
					<thead className="sticky top-0 z-10 bg-white/90 backdrop-blur">
						<tr className="border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
							<th className="px-4 py-3">Message</th>
							<th className="px-4 py-3">Sentiment</th>
							<th className="px-4 py-3">Time</th>
							<th className="px-4 py-3">Source</th>
						</tr>
					</thead>

					<tbody className="bg-white">
						{rows.map((r, idx) => (
							<tr key={idx} className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/60">
								<td className="px-4 py-3 text-slate-800">
									<div className="line-clamp-2">{r.message}</div>
								</td>

								<td className="px-4 py-3">
									<span className={["inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold", pillClasses(r.sentimentValue)].join(" ")} title={`value=${r.sentimentValue}`}>
										{r.sentimentLabel}
									</span>
								</td>

								<td className="px-4 py-3 text-slate-600 whitespace-nowrap">{r.timeLabel}</td>
								<td className="px-4 py-3 text-slate-600 whitespace-nowrap">{r.source}</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	)
}
