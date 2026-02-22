function getBannerClass(kind) {
	if (kind === "imminent") return "bg-amber-50 border-amber-200"
	if (kind === "confirmed") return "bg-emerald-50 border-emerald-200"
	return "bg-slate-50 border-slate-200"
}

function getPillClass(kind) {
	if (kind === "imminent") return "bg-amber-100 text-amber-800"
	if (kind === "confirmed") return "bg-emerald-100 text-emerald-800"
	return "bg-slate-200 text-slate-700"
}

export default function AlertBanner({ signal }) {
	const alert = signal?.alert ?? null

	const kind = alert === "IMMINENT_HYPE_PUMP" ? "imminent" : alert === "HYPE_PUMP_CONFIRMED" ? "confirmed" : "neutral"

	let title, subtitle, icon

	if (kind === "imminent") {
		icon = <span className="text-3xl">🚨</span>
		title = "IMMINENT HYPE PUMP"
		subtitle = "Vibe is surging, but price hasn’t moved yet (ΔP < 0.02)."
	} else if (kind === "confirmed") {
		icon = <span className="text-3xl">✅</span>
		title = "HYPE CONFIRMED"
		subtitle = "Vibe is surging and price is already reacting (ΔP ≥ 0.02)."
	} else {
		// neutral
		icon = null
		title = "NO STRONG SIGNAL"
		subtitle = "Waiting for a clear vibe/price divergence."
	}

	const showPill = kind === "neutral"

	return (
		<div className="mt-8">
			<div className={`gm-card p-8 text-center border ${getBannerClass(kind)}`}>
				<div className="mx-auto flex max-w-4xl flex-col items-center">
					{showPill && <span className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wide ${getPillClass(kind)}`}>{alert ?? "NONE"}</span>}

					<h2 className={`mt-4 flex items-center justify-center gap-3 font-semibold tracking-tight text-slate-900 ${kind === "neutral" ? "text-3xl sm:text-4xl" : "text-4xl sm:text-5xl"}`}>
						{icon}
						<span>{title}</span>
					</h2>

					<p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">{subtitle}</p>

					<div className="mt-7 grid w-full max-w-4xl grid-cols-2 gap-3 sm:grid-cols-4">
						<Metric label="Δ Price" value={signal?.deltaPrice} />
						<Metric label="Δ Vibe" value={signal?.deltaVibe} />
						<Metric label="Hype Momentum" value={signal?.hypeMomentum} />
						<Metric label="Events (N)" value={signal?.n} />
					</div>
				</div>
			</div>
		</div>
	)
}

function Metric({ label, value }) {
	const v = value == null ? "—" : typeof value === "number" ? String(value) : value
	return (
		<div className="rounded-2xl border border-slate-200 bg-white/60 p-4 text-left">
			<div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
			<div className="mt-1 text-lg font-semibold tracking-tight text-slate-900">{v}</div>
		</div>
	)
}
