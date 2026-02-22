import TopBar from "../components/shell/TopBar"
import PageGrid from "../components/shell/PageGrid"
import useGhostMarketApiData from "../hooks/useGhostMarketApiData"
import VibeFeedCard from "../components/cards/VibeFeedCard"
import PriceCard from "../components/cards/PriceCard"
import AlertBanner from "../components/alerts/AlertBanner"

export default function App() {
	const { state, refresh, setTicker } = useGhostMarketApiData()

	return (
		<div className="min-h-screen">
			{/* soft background */}
			<div className="pointer-events-none fixed inset-0 -z-10 bg-slate-50" />
			<div className="pointer-events-none fixed inset-0 -z-10 opacity-40">
				<div className="absolute -top-40 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-slate-200 blur-3xl" />
			</div>

			<TopBar ticker={state.ticker} onTickerChange={setTicker} onRefresh={refresh} />

			<PageGrid left={<VibeFeedCard data={state} />} right={<PriceCard data={state} />} />

			<div className="mx-auto max-w-6xl px-4 pb-10">
				<AlertBanner signal={state.signal} />
			</div>

			<footer className="mx-auto max-w-6xl px-4 pb-10">
				<div className="flex flex-col items-start justify-between gap-2 border-t border-slate-200 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center">
					<span>GhostMarket demo UI • React + Tailwind</span>
					<span>Data: demo-only (swap hook later)</span>
				</div>
			</footer>
		</div>
	)
}
