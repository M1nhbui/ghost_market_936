export function fmtMoney(x) {
	if (x == null || Number.isNaN(Number(x))) return "—"
	const n = Number(x)
	if (n >= 1) return n.toFixed(2)
	return n.toFixed(4)
}

export function fmtPct(x) {
	if (x == null || Number.isNaN(Number(x))) return "—"
	const n = Number(x)
	const sign = n > 0 ? "+" : ""
	return `${sign}${n.toFixed(2)}%`
}
