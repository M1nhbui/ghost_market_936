export default function TopBar({ ticker, onTickerChange, onRefresh }) {
	return (
		<div className="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur">
			<div className="mx-auto max-w-6xl px-4 py-3">
				<div className="flex items-center justify-between gap-4">
					<div className="flex items-center gap-3">
						<div className="leading-tight">
							<div className="text-sm font-semibold text-slate-900">GhostMarket</div>
							<div className="text-xs text-slate-500">Real-time vibe & price decoupling</div>
						</div>
					</div>

					<div className="flex items-center gap-3">
						<button onClick={onRefresh} className="gm-btn">
							Refresh
						</button>

						<select value={ticker?.key ?? "bitcoin"} onChange={(e) => onTickerChange(e.target.value)} className="gm-select" aria-label="Select ticker">
							<option value="dogecoin">Dogecoin (DOGE)</option>
							<option value="bitcoin">Bitcoin (BTC)</option>
							<option value="ethereum">Ethereum (ETH)</option>
						</select>
					</div>
				</div>
			</div>
		</div>
	)
}
