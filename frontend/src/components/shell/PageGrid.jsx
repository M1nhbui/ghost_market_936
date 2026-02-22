export default function PageGrid({ left, right }) {
	return (
		<div className="mx-auto max-w-6xl px-4 py-6">
			<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
				{left}
				{right}
			</div>
		</div>
	)
}
