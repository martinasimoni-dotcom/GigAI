using Newtonsoft.Json.Linq;
using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace GigAi.RevitPlugin
{
    public class LocateRfiDialog : Form
    {
        private static readonly HttpClient _http = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        private const string BackendUrl = "http://localhost:8000";

        private readonly TextBox _rfiIdBox;
        private readonly Button  _findButton;
        private readonly Label   _statusLabel;

        public LocateRfiDialog()
        {
            Text            = "GigAI — Locate RFI";
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox     = false;
            MinimizeBox     = false;
            StartPosition   = FormStartPosition.CenterScreen;
            ClientSize      = new System.Drawing.Size(340, 110);

            var labelRfi = new Label
            {
                Text      = "RFI ID:",
                Left      = 12, Top = 14,
                Width     = 60, Height = 20,
                TextAlign = System.Drawing.ContentAlignment.MiddleLeft
            };

            _rfiIdBox = new TextBox
            {
                Left = 76, Top = 12,
                Width = 240, Height = 24,
            };
            _rfiIdBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _ = SearchAsync(); }
            };

            _findButton = new Button
            {
                Text = "Find in Model",
                Left = 76, Top = 44,
                Width = 140, Height = 28
            };
            _findButton.Click += (s, e) => _ = SearchAsync();

            _statusLabel = new Label
            {
                Left      = 12, Top = 80,
                Width     = 310, Height = 20,
                ForeColor = System.Drawing.Color.Gray,
                Font      = new System.Drawing.Font(Font, System.Drawing.FontStyle.Italic)
            };

            Controls.AddRange(new Control[] { labelRfi, _rfiIdBox, _findButton, _statusLabel });
            AcceptButton = _findButton;
        }

        private async Task SearchAsync()
        {
            string rfiId = _rfiIdBox.Text?.Trim();
            if (string.IsNullOrEmpty(rfiId))
            {
                _statusLabel.Text = "Please enter an RFI ID.";
                return;
            }

            _findButton.Enabled = false;
            _statusLabel.Text   = "Searching…";

            try
            {
                string url  = $"{BackendUrl}/api/proposals?source_rfi_id={Uri.EscapeDataString(rfiId)}";
                string json = await _http.GetStringAsync(url);

                JToken root = JToken.Parse(json);

                JObject proposal = root is JArray arr && arr.Count > 0
                    ? arr[0] as JObject
                    : root as JObject;

                if (proposal == null)
                {
                    MessageBox.Show($"No proposal found for RFI ID: {rfiId}",
                        "GigAI — Not Found", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    _statusLabel.Text = "No results.";
                    return;
                }

                // ── The AI-generated content lives inside proposal_data ──────────
                // Fall back to root proposal if proposal_data is absent.
                JObject pd = proposal["proposal_data"] as JObject ?? proposal;

                // ── Top-level scalar fields ─────────────────────────────────────
                string title          = proposal["title"]?.ToString()       ?? pd["title"]?.ToString()       ?? "(no title)";
                string directAnswer   = pd["direct_answer"]?.ToString()     ?? proposal["direct_answer"]?.ToString() ?? "";
                string summary        = pd["summary"]?.ToString()           ?? proposal["summary"]?.ToString() ?? "";
                string justification  = pd["justification"]?.ToString()     ?? "";
                string recommendation = pd["recommendation"]?.ToString()    ?? proposal["recommendation"]?.ToString() ?? "review";
                int    timeline       = pd["timeline_weeks"]?.Value<int>()  ?? proposal["timeline_weeks"]?.Value<int>() ?? 0;

                // Confidence: top-level float 0–1 → percentage
                double confidenceRaw  = proposal["confidence"]?.Value<double>() ?? 0.0;
                int    confidencePct  = (int)Math.Round(confidenceRaw * 100);
                string confidenceLbl  = confidencePct >= 80 ? "High" : confidencePct >= 60 ? "Medium" : "Low";

                // ── Material change ─────────────────────────────────────────────
                JObject mc       = pd["material_change"] as JObject;
                string  matFrom  = mc?["from"]?.ToString()           ?? proposal["extracted"]?["material_from"]?.ToString() ?? "current material";
                string  matTo    = mc?["to"]?.ToString()             ?? proposal["extracted"]?["material_to"]?.ToString()   ?? "proposed material";
                string  location = mc?["affected_areas"]?.ToString() ?? proposal["extracted"]?["location"]?.ToString()     ?? "not specified";
                string  qty      = mc?["quantity"]?.ToString()       ?? "";
                string  unit     = mc?["unit"]?.ToString()           ?? "units";

                // ── Cost analysis ───────────────────────────────────────────────
                JObject ca        = pd["cost_analysis"] as JObject;
                string  totalCost = ca?["total_delta_eur"]?.ToString() ?? proposal["cost"]?.ToString() ?? "0";
                JArray  breakdown = ca?["breakdown"] as JArray;

                // ── Technical specs ─────────────────────────────────────────────
                JObject specs = pd["technical_specs"] as JObject;

                // ── Timeline breakdown ──────────────────────────────────────────
                JObject tlBreak = pd["timeline_breakdown"] as JObject;

                // ── Revit families ──────────────────────────────────────────────
                string revitPrimary = proposal["revit_family_primary"]?.ToString()
                                   ?? pd["revit_family_primary"]?.ToString()
                                   ?? proposal["revit_family_suggestion"]?.ToString()
                                   ?? "";
                string revitAlt     = proposal["revit_family_alternative"]?.ToString()
                                   ?? pd["revit_family_alternative"]?.ToString()
                                   ?? "";

                // ── Build message ───────────────────────────────────────────────
                string msg = BuildMessage(
                    title, directAnswer, summary, justification, recommendation,
                    location, matFrom, matTo, qty, unit,
                    totalCost, breakdown,
                    timeline, tlBreak,
                    specs,
                    revitPrimary, revitAlt,
                    confidencePct, confidenceLbl);

                MessageBox.Show(msg, "GigAI — RFI Response", MessageBoxButtons.OK, MessageBoxIcon.Information);
                _statusLabel.Text = "Done.";
            }
            catch (HttpRequestException ex)
            {
                MessageBox.Show(
                    $"Could not reach GigAI backend.\n\n{ex.Message}\n\nMake sure the backend is running on {BackendUrl}.",
                    "GigAI — Connection Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                _statusLabel.Text = "Connection failed.";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Unexpected error:\n{ex.Message}",
                    "GigAI — Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                _statusLabel.Text = "Error.";
            }
            finally
            {
                _findButton.Enabled = true;
            }
        }

        // ── Message builder ────────────────────────────────────────────────────
        private static string BuildMessage(
            string title, string directAnswer, string summary, string justification,
            string recommendation,
            string location, string matFrom, string matTo, string qty, string unit,
            string totalCost, JArray breakdown,
            int timeline, JObject tlBreak,
            JObject specs,
            string revitPrimary, string revitAlt,
            int confidencePct, string confidenceLbl)
        {
            string sep = new string('━', 36);
            var sb = new StringBuilder();

            sb.AppendLine(sep);
            sb.AppendLine("GigAI — RFI Response");
            sb.AppendLine(sep);
            sb.AppendLine();

            // Answer
            if (!string.IsNullOrEmpty(directAnswer))
            {
                sb.AppendLine($"ANSWER: {directAnswer}");
                sb.AppendLine();
            }

            // Location
            sb.AppendLine("LOCATION:");
            sb.AppendLine($"  {location}");
            sb.AppendLine();

            // Change required
            sb.AppendLine("CHANGE REQUIRED:");
            string changeText = !string.IsNullOrEmpty(summary) ? summary
                              : $"Replace {matFrom} with {matTo}";
            // Word-wrap at ~60 chars for readability
            foreach (string line in WrapText(changeText, 60))
                sb.AppendLine($"  {line}");
            sb.AppendLine();

            // Specifications
            bool hasSpecs = specs != null && specs.HasValues;
            if (hasSpecs || !string.IsNullOrEmpty(qty))
            {
                sb.AppendLine("SPECIFICATIONS:");
                if (hasSpecs)
                {
                    foreach (var kv in specs)
                        sb.AppendLine($"  {TitleCase(kv.Key)}: {kv.Value}");
                }
                if (!string.IsNullOrEmpty(qty))
                    sb.AppendLine($"  Quantity: {qty} {unit}");
                sb.AppendLine();
            }

            // Cost
            sb.AppendLine($"COST ESTIMATE: €{FormatNumber(totalCost)}");
            if (breakdown != null && breakdown.Count > 0)
            {
                foreach (var item in breakdown)
                {
                    string itemName = item["item"]?.ToString() ?? "";
                    string itemCost = item["cost_eur"]?.ToString() ?? "0";
                    if (double.TryParse(itemCost, System.Globalization.NumberStyles.Any,
                            System.Globalization.CultureInfo.InvariantCulture, out double c) && c > 0)
                        sb.AppendLine($"  • {itemName}: €{FormatNumber(itemCost)}");
                    else if (!string.IsNullOrEmpty(itemName))
                        sb.AppendLine($"  • {itemName}");
                }
            }
            sb.AppendLine();

            // Timeline
            if (timeline > 0)
            {
                sb.AppendLine($"TIMELINE: {timeline} weeks");
                if (tlBreak != null)
                {
                    string fab  = tlBreak["fabrication_weeks"]?.ToString();
                    string inst = tlBreak["installation_weeks"]?.ToString();
                    if (!string.IsNullOrEmpty(fab))  sb.AppendLine($"  Fabrication:  {fab} week{(fab == "1" ? "" : "s")}");
                    if (!string.IsNullOrEmpty(inst)) sb.AppendLine($"  Installation: {inst} week{(inst == "1" ? "" : "s")}");
                    string notes = tlBreak["notes"]?.ToString();
                    if (!string.IsNullOrEmpty(notes)) sb.AppendLine($"  Note: {notes}");
                }
                sb.AppendLine();
            }

            // Revit family
            if (!string.IsNullOrEmpty(revitPrimary))
            {
                sb.AppendLine("REVIT FAMILY:");
                sb.AppendLine($"  {revitPrimary}");
                if (!string.IsNullOrEmpty(revitAlt))
                    sb.AppendLine($"  (Alternative: {revitAlt})");
                sb.AppendLine();
            }

            // Confidence + recommendation
            sb.AppendLine($"CONFIDENCE: {confidencePct}% ({confidenceLbl})");
            sb.AppendLine($"AI RECOMMENDATION: {recommendation.Replace("_", " ").ToUpper()}");
            sb.AppendLine();
            sb.AppendLine(sep);

            return sb.ToString();
        }

        // ── Helpers ────────────────────────────────────────────────────────────
        private static string FormatCostBreakdown(JArray breakdown)
        {
            if (breakdown == null || breakdown.Count == 0) return "  • Breakdown not available";
            var sb = new StringBuilder();
            foreach (var item in breakdown)
            {
                string name = item["item"]?.ToString() ?? "Item";
                string cost = item["cost_eur"]?.ToString() ?? "0";
                if (double.TryParse(cost, System.Globalization.NumberStyles.Any,
                        System.Globalization.CultureInfo.InvariantCulture, out double c) && c > 0)
                    sb.AppendLine($"  • {name}: €{FormatNumber(cost)}");
                else
                    sb.AppendLine($"  • {name}");
            }
            return sb.ToString().TrimEnd();
        }

        private static string FormatNumber(string raw)
        {
            if (double.TryParse(raw, System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out double n))
                return n.ToString("N0", System.Globalization.CultureInfo.GetCultureInfo("it-IT"));
            return raw;
        }

        private static string TitleCase(string s)
        {
            if (string.IsNullOrEmpty(s)) return s;
            string spaced = s.Replace("_", " ");
            return char.ToUpper(spaced[0]) + spaced.Substring(1);
        }

        private static System.Collections.Generic.IEnumerable<string> WrapText(string text, int maxWidth)
        {
            if (string.IsNullOrEmpty(text)) { yield return ""; yield break; }
            string[] words = text.Split(' ');
            var line = new StringBuilder();
            foreach (string word in words)
            {
                if (line.Length + word.Length + 1 > maxWidth && line.Length > 0)
                {
                    yield return line.ToString();
                    line.Clear();
                }
                if (line.Length > 0) line.Append(' ');
                line.Append(word);
            }
            if (line.Length > 0) yield return line.ToString();
        }
    }
}
