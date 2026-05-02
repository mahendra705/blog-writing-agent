/** Filename for downloaded PDF (matches server `safe_pdf_filename` rules). */
export function pdfFilenameFromTitle(title: string | undefined): string {
  const raw = (title ?? "research-report").trim();
  const slug = raw
    .replace(/[^a-zA-Z0-9\s_-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 96);
  return `${slug || "research-report"}.pdf`;
}
