using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using GigAi.RevitAddin.Models;
using GigAi.RevitAddin.Utils;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Services
{
    internal sealed class AccAnnotationSyncSummary
    {
        public int Created { get; set; }
        public int Updated { get; set; }
        public int Removed { get; set; }
        public int Unchanged { get; set; }
        public int Failed { get; set; }
    }

    internal sealed class AccAnnotationService
    {
        private readonly AccSyncStorageService _storage = new AccSyncStorageService();
        private readonly AccIssueMapper _mapper = new AccIssueMapper();

        public AccAnnotationSyncSummary Run(UIApplication uiapp)
        {
            UIDocument? uiDocument = uiapp.ActiveUIDocument;
            if (uiDocument?.Document == null)
            {
                throw new InvalidOperationException("No active Revit document is available.");
            }

            Document document = uiDocument.Document;
            View activeView = document.ActiveView;
            if (activeView == null)
            {
                throw new InvalidOperationException("No active view is available in the Revit document.");
            }

            AccSyncPayload payload = _storage.LoadSnapshot();
            AccSyncConfiguration configuration = _storage.LoadConfiguration();
            AccSyncState state = _storage.LoadState();
            var stateMap = state.Entries.ToDictionary(entry => entry.SyncKey, StringComparer.OrdinalIgnoreCase);
            var seenKeys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var summary = new AccAnnotationSyncSummary();

            using (var transaction = new Transaction(document, "Sync ACC Issues (Read Only)"))
            {
                transaction.Start();

                ElementId revisionId = EnsureReadonlyRevision(document);

                foreach (AccSyncItem item in payload.Items)
                {
                    string syncKey = BuildSyncKey(item);
                    seenKeys.Add(syncKey);

                    try
                    {
                        if (!_mapper.TryResolve(document, activeView, item, configuration, out AccResolvedTarget? target, out string reason)
                            || target == null)
                        {
                            summary.Failed++;
                            Logger.Error($"{Timestamp()} {syncKey} -> resolve -> skipped ({reason})");
                            continue;
                        }

                        string hash = ComputePayloadHash(item);
                        if (stateMap.TryGetValue(syncKey, out AccSyncStateEntry? existing)
                            && string.Equals(existing.PayloadHash, hash, StringComparison.OrdinalIgnoreCase)
                            && ManagedElementsExist(document, existing))
                        {
                            summary.Unchanged++;
                            existing.LastSyncedAt = DateTimeOffset.UtcNow;
                            existing.Status = item.Status;
                            Logger.Info($"{Timestamp()} {syncKey} -> unchanged -> ok");
                            continue;
                        }

                        if (existing != null)
                        {
                            RemoveManagedElements(document, existing);
                            Logger.Info($"{Timestamp()} {syncKey} -> update -> old annotations removed");
                        }

                        AccSyncStateEntry entry = CreateOrReplaceAnnotation(document, revisionId, item, target, hash);
                        stateMap[syncKey] = entry;
                        if (existing == null)
                        {
                            summary.Created++;
                        }
                        else
                        {
                            summary.Updated++;
                        }

                        Logger.Info($"{Timestamp()} {syncKey} -> apply -> ok ({reason})");
                    }
                    catch (Exception ex)
                    {
                        summary.Failed++;
                        Logger.Error($"{Timestamp()} {syncKey} -> apply -> failed", ex);
                    }
                }

                foreach (AccSyncStateEntry stale in stateMap.Values.Where(entry => !seenKeys.Contains(entry.SyncKey)).ToList())
                {
                    RemoveManagedElements(document, stale);
                    stateMap.Remove(stale.SyncKey);
                    summary.Removed++;
                    Logger.Info($"{Timestamp()} {stale.SyncKey} -> remove -> stale annotation deleted");
                }

                transaction.Commit();
            }

            state.Entries = stateMap.Values.OrderBy(entry => entry.SyncKey, StringComparer.OrdinalIgnoreCase).ToList();
            _storage.SaveState(state);
            return summary;
        }

        private static AccSyncStateEntry CreateOrReplaceAnnotation(
            Document document,
            ElementId revisionId,
            AccSyncItem item,
            AccResolvedTarget target,
            string hash)
        {
            IList<Curve> curves = BuildBubbleCurves(target.View, target.AnchorPoint, target.WidthFeet, target.HeightFeet);
            RevisionCloud cloud = RevisionCloud.Create(document, target.View, revisionId, curves);
            ApplyStatusOverrides(target.View, cloud.Id, ResolveStatusColor(item.Status));

            XYZ notePoint = target.AnchorPoint
                + (NormalizeOrFallback(target.View.UpDirection, XYZ.BasisY) * ((target.HeightFeet / 2.0) + 1.0))
                + (NormalizeOrFallback(target.View.RightDirection, XYZ.BasisX) * 1.0);

            string noteText = BuildAnnotationText(item);
            TextNote note = TextNote.Create(
                document,
                target.View.Id,
                notePoint,
                noteText,
                document.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType));
            ApplyStatusOverrides(target.View, note.Id, ResolveStatusColor(item.Status));

            return new AccSyncStateEntry
            {
                SyncKey = BuildSyncKey(item),
                SourceId = item.Id,
                SourceType = item.Type,
                ElementRef = target.Element?.Id.Value.ToString(CultureInfo.InvariantCulture) ?? item.Location.ElementId,
                ViewRef = target.View.UniqueId,
                CloudId = cloud.Id.Value,
                NoteId = note.Id.Value,
                PayloadHash = hash,
                LastSyncedAt = DateTimeOffset.UtcNow,
                Status = item.Status,
            };
        }

        private static void ApplyStatusOverrides(View view, ElementId elementId, Color color)
        {
            var overrides = new OverrideGraphicSettings();
            overrides.SetProjectionLineColor(color);
            overrides.SetSurfaceForegroundPatternColor(color);
            overrides.SetCutLineColor(color);
            view.SetElementOverrides(elementId, overrides);
        }

        private static IList<Curve> BuildBubbleCurves(View view, XYZ center, double widthFeet, double heightFeet)
        {
            XYZ right = NormalizeOrFallback(view.RightDirection, XYZ.BasisX);
            XYZ up = NormalizeOrFallback(view.UpDirection, XYZ.BasisY);
            double halfWidth = widthFeet / 2.0;
            double halfHeight = heightFeet / 2.0;

            XYZ p1 = center - (right * halfWidth) - (up * halfHeight);
            XYZ p2 = center + (right * halfWidth) - (up * halfHeight);
            XYZ p3 = center + (right * halfWidth) + (up * halfHeight);
            XYZ p4 = center - (right * halfWidth) + (up * halfHeight);

            return new List<Curve>
            {
                Line.CreateBound(p1, p2),
                Line.CreateBound(p2, p3),
                Line.CreateBound(p3, p4),
                Line.CreateBound(p4, p1),
            };
        }

        private static ElementId EnsureReadonlyRevision(Document document)
        {
            Revision? existing = new FilteredElementCollector(document)
                .OfClass(typeof(Revision))
                .Cast<Revision>()
                .FirstOrDefault(revision =>
                    string.Equals(revision.Description, "ACC Readonly Sync", StringComparison.OrdinalIgnoreCase));

            if (existing != null)
            {
                return existing.Id;
            }

            Revision revision = Revision.Create(document);
            revision.Description = "ACC Readonly Sync";
            revision.Issued = false;
            return revision.Id;
        }

        private static void RemoveManagedElements(Document document, AccSyncStateEntry entry)
        {
            TryDelete(document, entry.CloudId);
            TryDelete(document, entry.NoteId);
        }

        private static bool ManagedElementsExist(Document document, AccSyncStateEntry entry)
        {
            return document.GetElement(new ElementId(entry.CloudId)) != null
                && document.GetElement(new ElementId(entry.NoteId)) != null;
        }

        private static void TryDelete(Document document, long elementId)
        {
            if (elementId <= 0)
            {
                return;
            }

            ElementId id = new ElementId(elementId);
            if (document.GetElement(id) == null)
            {
                return;
            }

            document.Delete(id);
        }

        private static string ComputePayloadHash(AccSyncItem item)
        {
            string json = JsonConvert.SerializeObject(item);
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            using (SHA256 sha256 = SHA256.Create())
            {
                return Convert.ToBase64String(sha256.ComputeHash(bytes));
            }
        }

        private static string BuildAnnotationText(AccSyncItem item)
        {
            string typeLabel = string.Equals(item.Type, "rfi", StringComparison.OrdinalIgnoreCase) ? "RFI" : "ISSUE";
            string title = SafeTrim(item.Title, 60);
            string description = FirstLines(item.Description, 2, 120);
            string assigned = string.IsNullOrWhiteSpace(item.AssignedUser) ? "Unassigned" : item.AssignedUser.Trim();
            string due = string.IsNullOrWhiteSpace(item.DueDate) ? "N/A" : item.DueDate.Trim();

            var lines = new List<string>
            {
                $"[TYPE: {typeLabel}]",
                $"ID: {item.Id}",
                string.Empty,
                $"Title: {title}",
                $"Description: {description}",
                $"Status: {item.Status}",
                $"Assigned: {assigned}",
                $"Due: {due}",
            };

            if (!string.IsNullOrWhiteSpace(item.CreatedBy))
            {
                lines.Add($"Created By: {item.CreatedBy.Trim()}");
            }

            return string.Join("\n", lines.Where(line => line != null));
        }

        private static string SafeTrim(string value, int maxLength)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return string.Empty;
            }

            string trimmed = value.Trim();
            return trimmed.Length <= maxLength ? trimmed : trimmed.Substring(0, maxLength - 3) + "...";
        }

        private static string FirstLines(string value, int maxLines, int maxLength)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return "(none)";
            }

            string compact = string.Join(" ", value
                .Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.RemoveEmptyEntries)
                .Select(part => part.Trim())
                .Where(part => !string.IsNullOrWhiteSpace(part))
                .Take(maxLines));

            return SafeTrim(compact, maxLength);
        }

        private static Color ResolveStatusColor(string status)
        {
            switch ((status ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "closed":
                case "close":
                case "resolved":
                    return new Color(0, 170, 0);
                case "pending":
                case "in_review":
                case "in review":
                    return new Color(230, 191, 0);
                case "open":
                default:
                    return new Color(220, 40, 40);
            }
        }

        private static string BuildSyncKey(AccSyncItem item)
        {
            return $"{item.Type}:{item.Id}";
        }

        private static XYZ NormalizeOrFallback(XYZ vector, XYZ fallback)
        {
            return vector == null || vector.GetLength() < 1e-9 ? fallback : vector.Normalize();
        }

        private static string Timestamp()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
        }
    }
}
