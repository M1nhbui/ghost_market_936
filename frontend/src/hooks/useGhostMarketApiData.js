import { useEffect, useState } from "react"

const TICKERS = [
	{ key: "dogecoin", label: "Dogecoin", symbol: "DOGE" },
	{ key: "bitcoin", label: "Bitcoin", symbol: "BTC" },
	{ key: "ethereum", label: "Ethereum", symbol: "ETH" },
]

const API_BASE = "http://127.0.0.1:8000"

export default function useGhostMarketApiData() {
	const [tickerKey, setTickerKey] = useState("dogecoin")
	const [state, setState] = useState(null)
	const [bump, setBump] = useState(0)

	async function fetchState() {
		const res = await fetch(`${API_BASE}/api/state?ticker=${encodeURIComponent(tickerKey)}`)
		if (!res.ok) throw new Error(`API error: ${res.status}`)
		const data = await res.json()

		// keep your UI’s ticker dropdown object stable
		const t = TICKERS.find((x) => x.key === tickerKey) ?? TICKERS[0]
		data.ticker = t

		setState(data)
	}

	useEffect(() => {
		fetchState().catch((e) => {
			console.error(e)
		})
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [tickerKey, bump])

	function refresh() {
		setBump((x) => x + 1)
	}

	function setTicker(nextKey) {
		setTickerKey(nextKey)
	}

	// provide a fallback shape so components don’t crash before first fetch
	const safeState = state ?? {
		ticker: TICKERS[0],
		stats: { avgSentiment: 0, signalUp: false, sources: 0, eventsCount: 0, eventsLabel: "demo" },
		price: { last: 0, changePct: 0, series: [] },
		vibeFeed: [],
		signal: { alert: null, deltaPrice: 0, deltaVibe: 0, hypeMomentum: 0, n: 0 },
	}

	return { state: safeState, refresh, setTicker, tickers: TICKERS }
}
