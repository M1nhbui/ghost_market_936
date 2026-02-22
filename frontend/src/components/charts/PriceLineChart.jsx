function scale(series, w, h, pad) {
	const ys = series.map((p) => p.p)
	const minY = Math.min(...ys)
	const maxY = Math.max(...ys)
	const range = maxY - minY || 1

	const x = (i) => pad + (i / Math.max(1, series.length - 1)) * (w - pad * 2)
	const y = (v) => h - pad - ((v - minY) / range) * (h - pad * 2)
	return { x, y, minY, maxY }
}

export default function PriceLineChart({ series }) {
	const w = 520
	const h = 150
	const pad = 12

	const s = series ?? []
	if (s.length < 2) {
		return (
			<div className="rounded-2xl border border-slate-200 bg-white p-4">
				<div className="text-xs font-medium text-slate-500">Price Trend</div>
				<div className="mt-2 text-sm text-slate-500">Not enough data.</div>
			</div>
		)
	}

	const { x, y } = scale(s, w, h, pad)

	const d = s.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.p)}`).join(" ")

	return (
		<div className="rounded-2xl border border-slate-200 bg-white p-4">
			<div className="flex items-center justify-between">
				<div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Price Trend</div>
				<div className="text-[11px] text-slate-400">
					{s[0].t} → {s[s.length - 1].t}
				</div>
			</div>

			<div className="mt-3 overflow-hidden rounded-2xl bg-slate-50">
				<svg viewBox={`0 0 ${w} ${h}`} className="h-[150px] w-full">
					<defs>
						<linearGradient id="gmFill" x1="0" x2="0" y1="0" y2="1">
							<stop offset="0%" stopColor="rgba(15,23,42,0.18)" />
							<stop offset="100%" stopColor="rgba(15,23,42,0.02)" />
						</linearGradient>
					</defs>

					{/* area fill */}
					<path d={`${d} L ${x(s.length - 1)} ${h - pad} L ${x(0)} ${h - pad} Z`} fill="url(#gmFill)" />

					{/* line */}
					<path d={d} fill="none" stroke="rgb(15,23,42)" strokeWidth="2.5" />

					{/* last point */}
					<circle cx={x(s.length - 1)} cy={y(s[s.length - 1].p)} r="4" fill="rgb(15,23,42)" />
				</svg>
			</div>

			<div className="mt-2 flex justify-between text-[11px] text-slate-500">
				<span>{s[0].t}</span>
				<span>{s[s.length - 1].t}</span>
			</div>
		</div>
	)
}
