import { useMemo } from "react";

type CsvRow = Record<string, unknown>;

type CsvTableProps = {
	title: string;
	rows: CsvRow[];
	columns: string[];
};

function renderCellValue(value: unknown) {
	if (value === null || value === undefined) {
		return "";
	}

	if (typeof value === "object") {
		return JSON.stringify(value);
	}

	return String(value);
}

export default function CsvTable({ title, rows, columns }: CsvTableProps) {
	const visibleColumns = useMemo(() => columns.filter(Boolean), [columns]);

	return (
		<section className="csv-table-card">
			<div className="csv-table-card__header">
				<h3>{title}</h3>
				<span>{rows.length} filas</span>
			</div>

			<div className="csv-table-wrap">
				<table className="csv-table">
					<thead>
						<tr>
							{visibleColumns.map((column) => (
								<th key={column}>{column}</th>
							))}
						</tr>
					</thead>
					<tbody>
						{rows.map((row, rowIndex) => (
							<tr key={`${title}-${rowIndex}`}>
								{visibleColumns.map((column) => (
									<td key={column}>{renderCellValue(row[column])}</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</section>
	);
}