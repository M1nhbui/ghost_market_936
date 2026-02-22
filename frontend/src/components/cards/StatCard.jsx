export default function StatCard({ title, value, sub, rightSlot }) {
	return (
		<div className="rounded-2xl border border-slate-200 bg-slate-50/60 p-4">
			<div className="flex items-start justify-between gap-3">
				<div>
					<div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{title}</div>
					<div className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{value}</div>
				</div>
				{rightSlot ? <div className="text-slate-400">{rightSlot}</div> : null}
			</div>

			{sub ? <div className="mt-2 text-xs text-slate-500">{sub}</div> : null}
		</div>
	)
}
