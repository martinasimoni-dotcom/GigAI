using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using RevitView = Autodesk.Revit.DB.View;

namespace GigAi.RevitAddin
{
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class FocusVoiceCommand : IExternalCommand
    {
        private const string FallbackApiUrl    = "http://127.0.0.1:8011";
        private const string FallbackProjectId = "project_alpha";
        private const double CloudScaleFactor  = 3.0;

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc      = commandData.Application.ActiveUIDocument;
            Document   doc        = uidoc.Document;
            RevitView  activeView = uidoc.ActiveView;

            string[] availableSpaces  = CollectAvailableSpaces(doc);
            string[] visibleSpaces    = CollectVisibleSpaces(doc, activeView);
            string   defaultApiUrl    = ResolveDefaultApiUrl();
            string   defaultProjectId = ResolveDefaultProjectId();
            string[] speechHints      = BuildSpeechHints(
                visibleSpaces.Length > 0
                    ? visibleSpaces.Concat(availableSpaces).ToArray()
                    : availableSpaces);

            using VoiceCommandForm form = new VoiceCommandForm(
                defaultApiUrl, defaultProjectId, string.Empty, speechHints);

            if (form.ShowDialog() != DialogResult.OK)
                return Result.Cancelled;

            string apiUrl     = form.ApiUrl;
            string projectId  = form.ProjectId;
            string transcript = form.Transcript;
            string audioBase64 = form.CapturedAudioBase64;
            string languageCode = form.LanguageCode;

            if (string.IsNullOrWhiteSpace(transcript) && string.IsNullOrWhiteSpace(audioBase64))
            {
                TaskDialog.Show("GigAI", "No transcript or recorded audio was provided.");
                return Result.Cancelled;
            }

            VoiceCommandResponse response = new VoiceCommandResponse();

            DrawingContext drawingContext = new DrawingContext
            {
                ViewName  = activeView.Name,
                ViewType  = activeView.ViewType.ToString(),
                ViewScale = activeView.Scale,
            };

            if (!string.IsNullOrWhiteSpace(audioBase64))
            {
                VoiceCommandAudioRequest audioRequest = new VoiceCommandAudioRequest
                {
                    ProjectId = projectId,
                    AudioBase64 = audioBase64,
                    Language = languageCode,
                    AvailableSpaces = availableSpaces,
                    VisibleSpaces = visibleSpaces,
                    DrawingContext = drawingContext,
                };

                try
                {
                    VoiceAudioCommandResponse audioResponse = GigAiApiClient.SendVoiceAudioCommand(apiUrl, audioRequest);
                    response = audioResponse.Pipeline ?? new VoiceCommandResponse();
                    if (string.IsNullOrWhiteSpace(transcript))
                    {
                        transcript = audioResponse.Transcript ?? string.Empty;
                    }
                }
                catch (Exception ex)
                {
                    TaskDialog.Show("GigAI API Error", ex.Message);
                    return Result.Failed;
                }
            }
            else
            {
                VoiceCommandRequest request = new VoiceCommandRequest
                {
                    ProjectId = projectId,
                    Transcript = transcript,
                    AvailableSpaces = availableSpaces,
                    VisibleSpaces = visibleSpaces,
                    DrawingContext = drawingContext,
                };

                try
                {
                    response = GigAiApiClient.SendVoiceCommand(apiUrl, request);
                }
                catch (Exception ex)
                {
                    TaskDialog.Show("GigAI API Error", ex.Message);
                    return Result.Failed;
                }
            }

            string focusSpace = response?.Event?.FocusSpace ?? string.Empty;
            if (string.IsNullOrWhiteSpace(focusSpace))
                focusSpace = InferFocusSpaceFromTranscript(transcript, availableSpaces);

            string        noteText       = BuildChangeNote(response);
            List<Element> allElements    = CollectAllSpaceElements(doc);
            Element       target         = FindBestMatch(allElements, focusSpace);
            RevitView     annotationView = FindBestAnnotationView(doc, activeView, target);
            XYZ           center         = ResolveAnchorPoint(annotationView, target);

            using (Transaction t = new Transaction(doc, "GigAI Revision Cloud"))
            {
                t.Start();

                CreateRevisionCloudAndNote(
                    doc, annotationView, target, center, noteText,
                    out bool bubbleCreated, out string bubbleError,
                    out bool noteCreated,   out string noteError,
                    out ElementId bubbleId, out ElementId noteId);

                t.Commit();

                if (target != null)
                    try { uidoc.ShowElements(target.Id); } catch { }

                string resultMsg = bubbleCreated
                    ? $"Revision cloud created for: {focusSpace}"
                    : $"Cloud failed: {bubbleError}";
                if (!noteCreated && !string.IsNullOrEmpty(noteError))
                    resultMsg += $"\nNote failed: {noteError}";

                if (bubbleCreated)
                {
                    try
                    {
                        string revisionId = bubbleId != ElementId.InvalidElementId
                            ? bubbleId.Value.ToString()
                            : $"rev_{DateTimeOffset.UtcNow.ToUnixTimeSeconds()}";

                        var revisionPayload = new RevisionMarkedRequest
                        {
                            RevisionId = revisionId,
                            MeetingId = "meet_revit",
                            ProjectId = projectId,
                            SpaceName = string.IsNullOrWhiteSpace(focusSpace) ? "Unknown Space" : focusSpace,
                            ElementType = target?.Category?.Name ?? "room",
                            Action = "REVISION_MARKED",
                            CommentText = noteText,
                            AppliedBy = Environment.UserName,
                        };

                        GigAiApiClient.NotifyRevisionMarked(apiUrl, revisionPayload);
                        resultMsg += "\nDashboard updated and completion email triggered.";
                    }
                    catch (Exception ex)
                    {
                        resultMsg += $"\nPost-sync warning: {ex.Message}";
                    }
                }

                TaskDialog.Show("GigAI", resultMsg);
            }

            return Result.Succeeded;
        }

        // ── Space collection ─────────────────────────────────────────────
        private static string[] CollectAvailableSpaces(Document doc)
        {
            var names = new List<string>();
            names.AddRange(new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms).OfType<Room>()
                .Where(r => r.Area > 0).Select(r => GetElementDisplayName(r)));
            names.AddRange(new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Areas).OfType<Element>()
                .Select(a => GetElementDisplayName(a)));
            return names.Where(n => !string.IsNullOrWhiteSpace(n)).Distinct().ToArray();
        }

        private static List<Element> CollectAllSpaceElements(Document doc)
        {
            var list = new List<Element>();
            list.AddRange(new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms).OfType<Room>()
                .Where(r => r.Area > 0));
            list.AddRange(new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Areas).OfType<Element>());
            return list;
        }

        private static string[] CollectVisibleSpaces(Document doc, RevitView view)
        {
            if (view == null)
                return Array.Empty<string>();

            try
            {
                var names = new List<string>();
                names.AddRange(new FilteredElementCollector(doc, view.Id)
                    .OfCategory(BuiltInCategory.OST_Rooms).OfType<Room>()
                    .Where(r => r.Area > 0)
                    .Select(r => GetElementDisplayName(r)));
                names.AddRange(new FilteredElementCollector(doc, view.Id)
                    .OfCategory(BuiltInCategory.OST_Areas).OfType<Element>()
                    .Select(a => GetElementDisplayName(a)));

                return names
                    .Where(n => !string.IsNullOrWhiteSpace(n))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToArray();
            }
            catch
            {
                return Array.Empty<string>();
            }
        }

        private static string GetElementDisplayName(Element e)
        {
            string number = e.get_Parameter(BuiltInParameter.ROOM_NUMBER)?.AsString() ?? string.Empty;
            string name   = e.get_Parameter(BuiltInParameter.ROOM_NAME)?.AsString() ?? e.Name ?? string.Empty;
            return (!string.IsNullOrWhiteSpace(number) && !string.IsNullOrWhiteSpace(name))
                ? $"{number} - {name}".Trim() : name.Trim();
        }

        // ── Revision cloud + note ────────────────────────────────────────
        private static void CreateRevisionCloudAndNote(
            Document doc, RevitView view, Element target, XYZ center, string noteText,
            out bool bubbleCreated, out string bubbleError,
            out bool noteCreated,   out string noteError,
            out ElementId bubbleId, out ElementId noteId)
        {
            bubbleCreated = false; bubbleError = string.Empty;
            noteCreated   = false; noteError   = string.Empty;
            bubbleId      = ElementId.InvalidElementId;
            noteId        = ElementId.InvalidElementId;

            if (CanTryCreateDetailCurve(view))
            {
                try
                {
                    if (target == null)
                        throw new InvalidOperationException(
                            "No matching room/area found. Please mention a valid Revit room or area name in the voice command.");

                    IList<Curve> arcs  = BuildCloudArcsFromRoom(target, view);
                    ElementId    revId = GetOrCreateRevision(doc);
                    RevisionCloud cloud = RevisionCloud.Create(doc, view, revId, arcs);
                    ApplyCloudOverrides(view, cloud.Id);
                    bubbleCreated = true;
                    bubbleId      = cloud.Id;
                }
                catch (Exception ex) { bubbleError = ex.Message; }
            }
            else { bubbleError = "View type does not support revision clouds."; }

            if (CanTryCreateTextNote(view))
            {
                try
                {
                    double    offset    = ComputeCloudHalfSize(view, target) * 1.3;
                    XYZ       notePoint = center + view.RightDirection.Multiply(offset);
                    ElementId typeId    = GetDefaultTextNoteTypeId(doc);
                    TextNote  note      = TextNote.Create(doc, view.Id, notePoint, noteText, typeId);
                    noteId      = note.Id;
                    noteCreated = true;
                }
                catch (Exception ex) { noteError = ex.Message; }
            }
            else { noteError = "View type does not support text notes."; }
        }

        // ── Build revision cloud from actual room/space extents ──────────
        private static IList<Curve> BuildCloudArcsFromRoom(Element target, RevitView view)
        {
            if (target == null)
                throw new InvalidOperationException("Cannot create revision cloud without a target element.");

            double viewZ   = view.Origin.Z;
            double margin  = 0.5 * CloudScaleFactor;
            double minX, minY, maxX, maxY;

            // First choice: use room boundary segments, which represent the real room outline.
            if (target is Room room)
            {
                try
                {
                    var opts = new SpatialElementBoundaryOptions();
                    IList<IList<BoundarySegment>> loops = room.GetBoundarySegments(opts);
                    if (loops != null && loops.Count > 0)
                    {
                        foreach (IList<BoundarySegment> loop in loops)
                        {
                            var pts = loop
                                .SelectMany(seg => new[]
                                {
                                    seg.GetCurve().GetEndPoint(0),
                                    seg.GetCurve().GetEndPoint(1)
                                })
                                .ToList();

                            if (pts.Count >= 4)
                            {
                                minX = pts.Min(p => p.X) - margin;
                                minY = pts.Min(p => p.Y) - margin;
                                maxX = pts.Max(p => p.X) + margin;
                                maxY = pts.Max(p => p.Y) + margin;
                                return BuildArcsOnRect(minX, minY, maxX, maxY, viewZ);
                            }
                        }
                    }
                }
                catch { }
            }

            // Second choice: use room model bounding box rather than a center point.
            BoundingBoxXYZ modelBounds = target.get_BoundingBox(null);
            if (modelBounds != null)
            {
                minX = modelBounds.Min.X - margin;
                minY = modelBounds.Min.Y - margin;
                maxX = modelBounds.Max.X + margin;
                maxY = modelBounds.Max.Y + margin;
                return BuildArcsOnRect(minX, minY, maxX, maxY, viewZ);
            }

            // Third choice: use view bounding box if available.
            BoundingBoxXYZ bb = target.get_BoundingBox(view);
            if (bb != null)
            {
                minX = bb.Min.X - margin;
                minY = bb.Min.Y - margin;
                maxX = bb.Max.X + margin;
                maxY = bb.Max.Y + margin;
                return BuildArcsOnRect(minX, minY, maxX, maxY, viewZ);
            }

            throw new InvalidOperationException(
                "Could not resolve a valid room/area boundary in this view for revision cloud creation.");
        }

        // ── Build bumpy arcs on a rectangle at given Z ───────────────────
        private static IList<Curve> BuildArcsOnRect(
            double minX, double minY, double maxX, double maxY, double z)
        {
            double width  = maxX - minX;
            double height = maxY - minY;
            double bumpR  = Math.Max(0.30,
                            Math.Min(Math.Min(width, height) / 10.0, 1.50));

            var corners = new List<(double x, double y)>
            {
                (minX, minY), (maxX, minY), (maxX, maxY), (minX, maxY)
            };

            var arcs = new List<Curve>();

            for (int i = 0; i < 4; i++)
            {
                double x0 = corners[i].x,       y0 = corners[i].y;
                double x1 = corners[(i+1)%4].x, y1 = corners[(i+1)%4].y;

                double edgeLen = Math.Sqrt(Math.Pow(x1-x0, 2) + Math.Pow(y1-y0, 2));
                int    nBumps  = Math.Max(2, (int)Math.Round(edgeLen / (2 * bumpR)));
                double actualR = edgeLen / (2.0 * nBumps);
                double dx = (x1-x0)/edgeLen, dy = (y1-y0)/edgeLen;
                double nx = -dy,              ny =  dx;

                for (int b = 0; b < nBumps; b++)
                {
                    double t0   = (double)b     / nBumps * edgeLen;
                    double t1   = (double)(b+1) / nBumps * edgeLen;
                    double tMid = (t0 + t1) / 2.0;

                    XYZ start = new XYZ(x0 + dx*t0,              y0 + dy*t0,              z);
                    XYZ end   = new XYZ(x0 + dx*t1,              y0 + dy*t1,              z);
                    XYZ mid   = new XYZ(x0 + dx*tMid + nx*actualR*2,
                                        y0 + dy*tMid + ny*actualR*2, z);
                    try { arcs.Add(Arc.Create(start, end, mid)); } catch { }
                }
            }

            return arcs;
        }

        private static double ComputeCloudHalfSize(RevitView view, Element target)
        {
            return ComputeCloudHalfSizeFromElement(target,
                fallback: 1.5 * (view.Scale <= 0 ? 100 : view.Scale) / 100.0);
        }

        private static double ComputeCloudHalfSizeFromElement(Element target, double fallback = 10.0)
        {
            if (target is Room room)
            {
                try
                {
                    var opts = new SpatialElementBoundaryOptions();
                    var loops = room.GetBoundarySegments(opts);
                    if (loops != null && loops.Count > 0)
                    {
                        var pts = loops[0].Select(s => s.GetCurve().GetEndPoint(0)).ToList();
                        if (pts.Count >= 2)
                        {
                            double w = pts.Max(p => p.X) - pts.Min(p => p.X);
                            double h = pts.Max(p => p.Y) - pts.Min(p => p.Y);
                            return Math.Max(w, h) / 2.0 + 0.5;
                        }
                    }
                }
                catch { }
            }
            return fallback;
        }

        private static void ApplyCloudOverrides(RevitView view, ElementId id)
        {
            var ogs = new OverrideGraphicSettings();
            ogs.SetProjectionLineColor(new Color(0, 0, 200));
            ogs.SetProjectionLineWeight(5);
            view.SetElementOverrides(id, ogs);
        }

        // ── Revision ─────────────────────────────────────────────────────
        private static ElementId GetOrCreateRevision(Document doc)
        {
            var revisions = new FilteredElementCollector(doc)
                .OfClass(typeof(Revision)).OfType<Revision>().ToList();
            if (revisions.Any()) return revisions.Last().Id;
            Revision rev = Revision.Create(doc);
            rev.Description = "GigAI Auto Revision";
            return rev.Id;
        }

        // ── View helpers ──────────────────────────────────────────────────
        private static bool CanTryCreateDetailCurve(RevitView view)
        {
            if (view.IsTemplate || view is View3D) return false;
            switch (view.ViewType)
            {
                case ViewType.Schedule:
                case ViewType.ProjectBrowser:
                case ViewType.SystemBrowser:
                case ViewType.Undefined:
                case ViewType.Internal: return false;
                default: return true;
            }
        }

        private static bool CanTryCreateTextNote(RevitView view)
        {
            if (view.IsTemplate || view is View3D) return false;
            switch (view.ViewType)
            {
                case ViewType.ProjectBrowser:
                case ViewType.SystemBrowser:
                case ViewType.Undefined:
                case ViewType.Internal: return false;
                default: return true;
            }
        }

        private static RevitView FindBestAnnotationView(Document doc, RevitView activeView, Element target)
        {
            if (activeView.ViewType == ViewType.DrawingSheet)
            {
                foreach (Viewport vp in new FilteredElementCollector(doc)
                    .OfClass(typeof(Viewport)).Cast<Viewport>()
                    .Where(vp => vp.SheetId == activeView.Id))
                {
                    RevitView vpView = doc.GetElement(vp.ViewId) as RevitView;
                    if (vpView == null) continue;
                    if (!CanTryCreateDetailCurve(vpView) && !CanTryCreateTextNote(vpView)) continue;
                    if (target?.get_BoundingBox(vpView) != null) return vpView;
                }
            }

            if (CanTryCreateDetailCurve(activeView) || CanTryCreateTextNote(activeView))
                return activeView;

            return new FilteredElementCollector(doc)
                .OfClass(typeof(RevitView)).Cast<RevitView>()
                .FirstOrDefault(v => !v.IsTemplate
                    && v.ViewType != ViewType.ProjectBrowser
                    && v.ViewType != ViewType.SystemBrowser
                    && (CanTryCreateDetailCurve(v) || CanTryCreateTextNote(v))
                    && (target == null || target.get_BoundingBox(v) != null))
                ?? activeView;
        }

        private static XYZ ResolveAnchorPoint(RevitView view, Element target)
        {
            if (target is Room room)
            {
                try
                {
                    var opts = new SpatialElementBoundaryOptions();
                    var loops = room.GetBoundarySegments(opts);
                    if (loops != null && loops.Count > 0)
                    {
                        var pts = loops[0].Select(s => s.GetCurve().GetEndPoint(0)).ToList();
                        if (pts.Count >= 2)
                        {
                            double cx = (pts.Max(p => p.X) + pts.Min(p => p.X)) / 2.0;
                            double cy = (pts.Max(p => p.Y) + pts.Min(p => p.Y)) / 2.0;
                            return new XYZ(cx, cy, view.Origin.Z);
                        }
                    }
                }
                catch { }
            }

            if (target != null)
            {
                XYZ loc = TryGetLocationPoint(target);
                if (loc != null) return new XYZ(loc.X, loc.Y, view.Origin.Z);
            }

            if (view.CropBox != null)
                return Midpoint(view.CropBox.Min, view.CropBox.Max);

            return XYZ.Zero;
        }

        // ── Element matching ──────────────────────────────────────────────
        private static Element FindBestMatch(IEnumerable<Element> elements, string focusSpace)
        {
            if (string.IsNullOrWhiteSpace(focusSpace)) return null;
            string norm = Normalize(focusSpace);

            Element exact = elements.FirstOrDefault(e =>
                string.Equals(Normalize(GetElementDisplayName(e)), norm, StringComparison.Ordinal));
            if (exact != null) return exact;

            var targetTokens = ToTokenSet(norm);
            var targetRoots  = ExtractRoomRoots(norm);
            Element best = null;
            double bestScore = 0;

            foreach (Element e in elements)
            {
                string cand      = Normalize(GetElementDisplayName(e));
                double rootOvlp  = targetRoots.Count > 0
                    ? (double)targetRoots.Intersect(ExtractRoomRoots(cand)).Count() / targetRoots.Count : 0;
                double tokenOvlp = targetTokens.Count > 0
                    ? (double)targetTokens.Intersect(ToTokenSet(cand)).Count() / targetTokens.Count : 0;
                double contains  = cand.Contains(norm) || norm.Contains(cand) ? 1.0 : 0.0;
                double score     = rootOvlp*0.60 + tokenOvlp*0.30 + contains*0.10;
                if (score > bestScore) { bestScore = score; best = e; }
            }

            if (best != null && bestScore >= 0.60) return best;
            return null;
        }

        // ── Text note ─────────────────────────────────────────────────────
        private static ElementId GetDefaultTextNoteTypeId(Document doc)
        {
            ElementId id = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType);
            if (id != ElementId.InvalidElementId) return id;
            return new FilteredElementCollector(doc)
                .OfClass(typeof(TextNoteType)).Cast<TextNoteType>().First().Id;
        }

        // ── Geometry helpers ──────────────────────────────────────────────
        private static XYZ Midpoint(XYZ a, XYZ b) =>
            new XYZ((a.X+b.X)/2, (a.Y+b.Y)/2, (a.Z+b.Z)/2);

        private static XYZ TryGetLocationPoint(Element e)
        {
            if (e.Location is LocationPoint lp) return lp.Point;
            if (e.Location is LocationCurve lc)
                return Midpoint(lc.Curve.GetEndPoint(0), lc.Curve.GetEndPoint(1));
            return null;
        }

        // ── String helpers ────────────────────────────────────────────────
        private static string Normalize(string value) =>
            new string(value.ToLowerInvariant()
                .Where(ch => char.IsLetterOrDigit(ch) || char.IsWhiteSpace(ch) || ch == '-')
                .ToArray()).Trim();

        private static HashSet<string> ToTokenSet(string value) =>
            value.Split(new[]{' '}, StringSplitOptions.RemoveEmptyEntries)
                 .ToHashSet(StringComparer.Ordinal);

        private static HashSet<string> ExtractRoomRoots(string value)
        {
            var roots = new HashSet<string>(StringComparer.Ordinal);
            foreach (Match m in Regex.Matches(value ?? string.Empty, @"\b[a-z]?[0-9]{2,4}[a-z]?\b"))
            {
                string digits = new string(m.Value.Where(char.IsDigit).ToArray());
                if (digits.Length >= 2) roots.Add(digits);
            }
            return roots;
        }

        private static string InferFocusSpaceFromTranscript(string transcript, string[] spaces)
        {
            if (string.IsNullOrWhiteSpace(transcript) || spaces.Length == 0)
                return string.Empty;
            string norm = Normalize(ConvertSpokenNumbersToDigits(transcript));
            foreach (string space in spaces)
                if (norm.Contains(Normalize(space))) return space;
            if (TryExtractRoomNumber(norm, out string roomNum))
                foreach (string space in spaces)
                    if (Normalize(space).Contains(roomNum)) return space;
            return string.Empty;
        }

        private static string BuildChangeNote(VoiceCommandResponse? response)
        {
            string focus = response?.Event?.FocusSpace ?? "Unknown";
            string proposal = string.IsNullOrWhiteSpace(response?.Decision?.Proposal)
                ? "review_issue"
                : response.Decision.Proposal;
            string remarks = HumanizeRemark(proposal);

            string confidenceLine = response != null && response.Decision != null && response.Decision.Confidence > 0
                ? $"\nConfidence: {response.Decision.Confidence:0.00}"
                : string.Empty;

            string risk = string.IsNullOrWhiteSpace(response?.Decision?.RiskLevel)
                ? string.Empty
                : $"\nRisk: {HumanizeRemark(response.Decision.RiskLevel)}";

            string actionStatus = string.IsNullOrWhiteSpace(response?.Action?.Status)
                ? string.Empty
                : $"\nAction: {HumanizeRemark(response.Action.Status)}";

            string writeback = string.IsNullOrWhiteSpace(response?.Action?.Outputs?.Bim360)
                ? string.Empty
                : $"\nBIM 360: {HumanizeRemark(response.Action.Outputs.Bim360)}";

            return
                $"GigAI Decision\n" +
                $"Space: {focus}\n" +
                $"Proposal: {remarks}" +
                confidenceLine +
                risk +
                actionStatus +
                writeback;
        }

        private static string HumanizeRemark(string value)
        {
            string cleaned = (value ?? string.Empty).Replace("_"," ").Replace("-"," ").Trim();
            if (string.IsNullOrWhiteSpace(cleaned)) return "Review issue and update drawing.";
            return char.ToUpperInvariant(cleaned[0]) + cleaned.Substring(1);
        }

        private static string[] BuildSpeechHints(string[] spaces)
        {
            var hints = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string s in spaces)
            {
                hints.Add(s);
                foreach (string part in s.Split('-'))
                    if (!string.IsNullOrWhiteSpace(part)) hints.Add(part.Trim());

                Match roomStyle = Regex.Match(
                    s,
                    @"^\s*(?<number>[A-Za-z]?\d{2,4}[A-Za-z]?)\s*-\s*(?<name>.+?)\s*$",
                    RegexOptions.IgnoreCase
                );
                if (roomStyle.Success)
                {
                    string number = roomStyle.Groups["number"].Value.Trim();
                    string name = roomStyle.Groups["name"].Value.Trim();
                    string spokenNumber = ToSpokenDigitSequence(number);
                    hints.Add(number);
                    hints.Add(name);
                    hints.Add($"{name} {number}");
                    hints.Add($"{number} {name}");
                    hints.Add($"room {number}");
                    hints.Add($"space {number}");
                    hints.Add($"unit {number}");
                    hints.Add($"mark {name} {number}");
                    hints.Add($"focus on {name} {number}");
                    hints.Add($"mark {number}");
                    hints.Add($"focus on {number}");
                    hints.Add($"select {number}");
                    hints.Add($"show {number}");
                    hints.Add($"find {number}");
                    if (!string.IsNullOrWhiteSpace(spokenNumber))
                    {
                        hints.Add(spokenNumber);
                        hints.Add($"{name} {spokenNumber}");
                        hints.Add($"{spokenNumber} {name}");
                        hints.Add($"room {spokenNumber}");
                        hints.Add($"space {spokenNumber}");
                        hints.Add($"unit {spokenNumber}");
                        hints.Add($"mark {name} {spokenNumber}");
                        hints.Add($"focus on {name} {spokenNumber}");
                        hints.Add($"mark {spokenNumber}");
                        hints.Add($"focus on {spokenNumber}");
                        hints.Add($"select {spokenNumber}");
                        hints.Add($"show {spokenNumber}");
                        hints.Add($"find {spokenNumber}");
                    }
                }
            }
            hints.UnionWith(new[]{"focus on","go to","select","review","check","show","find",
                                   "mark revision","corridor","lobby","elevator","stair",
                                   "restroom","unit","room","space","core","grid"});
            return hints.ToArray();
        }

        private static string ToSpokenDigitSequence(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return string.Empty;

            var spoken = new List<string>();
            foreach (char ch in value)
            {
                switch (ch)
                {
                    case '0': spoken.Add("zero"); break;
                    case '1': spoken.Add("one"); break;
                    case '2': spoken.Add("two"); break;
                    case '3': spoken.Add("three"); break;
                    case '4': spoken.Add("four"); break;
                    case '5': spoken.Add("five"); break;
                    case '6': spoken.Add("six"); break;
                    case '7': spoken.Add("seven"); break;
                    case '8': spoken.Add("eight"); break;
                    case '9': spoken.Add("nine"); break;
                    default:
                        if (char.IsLetter(ch))
                            spoken.Add(ch.ToString().ToLowerInvariant());
                        break;
                }
            }
            return string.Join(" ", spoken);
        }

        private static string ResolveDefaultApiUrl()
        {
            string v = Environment.GetEnvironmentVariable("GIGAI_API_URL") ?? string.Empty;
            return string.IsNullOrWhiteSpace(v) ? FallbackApiUrl : v.Trim();
        }

        private static string ResolveDefaultProjectId()
        {
            string v = Environment.GetEnvironmentVariable("GIGAI_PROJECT_ID") ?? string.Empty;
            return string.IsNullOrWhiteSpace(v) ? FallbackProjectId : v.Trim();
        }

        private static string ConvertSpokenNumbersToDigits(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return text;
            var map = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase)
            {
                ["zero"]="0",["oh"]="0",["o"]="0",["one"]="1",["two"]="2",["too"]="2",
                ["to"]="2",["three"]="3",["four"]="4",["for"]="4",["five"]="5",
                ["six"]="6",["seven"]="7",["eight"]="8",["nine"]="9",
            };
            var output = new List<string>();
            var buf    = new List<string>();
            void Flush(){if(buf.Count>0){output.Add(string.Concat(buf));buf.Clear();}}
            foreach (string tok in Regex.Split(text, @"(\s+|[^\w]+)"))
            {
                if (string.IsNullOrWhiteSpace(tok)){Flush();output.Add(tok);continue;}
                if (map.TryGetValue(tok.Trim(), out string d)){buf.Add(d);continue;}
                if (tok.All(char.IsDigit)){Flush();output.Add(tok);continue;}
                Flush(); output.Add(tok);
            }
            Flush();
            return string.Concat(output);
        }

        private static bool TryExtractRoomNumber(string transcript, out string roomNumber)
        {
            roomNumber = string.Empty;
            if (string.IsNullOrWhiteSpace(transcript)) return false;
            Match m = Regex.Match(transcript, @"\b\d{2,4}\b");
            if (m.Success) { roomNumber = m.Value; return true; }
            return false;
        }
    }
}
