import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const artifactToolSpecifier = process.env.UKACTIVE_ARTIFACT_TOOL_MODULE
  ? pathToFileURL(path.resolve(process.env.UKACTIVE_ARTIFACT_TOOL_MODULE)).href
  : "@oai/artifact-tool";
const { Workbook } = await import(artifactToolSpecifier);

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = process.env.UKACTIVE_PAPER_ROOT
  ? path.resolve(process.env.UKACTIVE_PAPER_ROOT)
  : path.resolve(scriptDir, "..");
const tableDir = path.join(root, "tables");
const qaDir = path.join(root, "qa");

const tableNames = (await fs.readdir(tableDir))
  .filter((name) => name.toLowerCase().endsWith(".csv"))
  .sort();
const rootNames = [
  "UKACTIVE_PAPER_FIGURE_MANIFEST.csv",
  "UKACTIVE_PAPER_SOURCE_EVIDENCE_MATRIX.csv",
];
const files = [
  ...tableNames.map((name) => path.join(tableDir, name)),
  ...rootNames.map((name) => path.join(root, name)),
];

const records = [];
for (const file of files) {
  const csvText = await fs.readFile(file, "utf8");
  const workbook = await Workbook.fromCSV(csvText, { sheetName: "Data" });
  const inspection = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 3000,
    tableMaxRows: 3,
    tableMaxCols: 8,
    tableMaxCellChars: 80,
  });
  const nonemptyLines = csvText.split(/\r?\n/u).filter((line) => line.length > 0);
  records.push({
    file: path.relative(root, file).replaceAll("\\", "/"),
    status: "PASS",
    artifact_tool_imported: true,
    nonempty_csv_lines: nonemptyLines.length,
    inspection_returned: Boolean(inspection?.ndjson),
  });
}

const result = {
  status: records.every((item) => item.status === "PASS" && item.artifact_tool_imported && item.inspection_returned)
    ? "PASS"
    : "FAIL",
  tool: "@oai/artifact-tool Workbook.fromCSV + inspect",
  validated_files: records.length,
  files: records,
};
await fs.mkdir(qaDir, { recursive: true });
await fs.writeFile(
  path.join(qaDir, "UKACTIVE_PAPER_TABULAR_VALIDATION.json"),
  `${JSON.stringify(result, null, 2)}\n`,
  "utf8",
);
if (result.status !== "PASS") process.exitCode = 1;
else process.stdout.write(`${JSON.stringify({ status: result.status, validated_files: result.validated_files })}\n`);
