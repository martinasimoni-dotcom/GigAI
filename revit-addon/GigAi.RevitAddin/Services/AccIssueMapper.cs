using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Autodesk.Revit.DB;
using GigAi.RevitAddin.Models;

namespace GigAi.RevitAddin.Services
{
    internal sealed class AccResolvedTarget
    {
        public AccResolvedTarget(View view, Element? element, XYZ anchorPoint, double widthFeet, double heightFeet)
        {
            View = view;
            Element = element;
            AnchorPoint = anchorPoint;
            WidthFeet = widthFeet;
            HeightFeet = heightFeet;
        }

        public View View { get; }

        public Element? Element { get; }

        public XYZ AnchorPoint { get; }

        public double WidthFeet { get; }

        public double HeightFeet { get; }
    }

    internal sealed class AccIssueMapper
    {
        public bool TryResolve(
            Document document,
            View activeView,
            AccSyncItem item,
            AccSyncConfiguration configuration,
            out AccResolvedTarget? target,
            out string reason)
        {
            View view = ResolveView(document, activeView, item, configuration, out bool usedFallbackView);
            Element? element = ResolveElement(document, view, item, configuration);

            XYZ? anchor = ResolveAnchorPoint(element, item.Location, configuration);
            if (anchor == null)
            {
                target = null;
                reason = "No element or coordinates could be resolved from ACC payload.";
                return false;
            }

            (double widthFeet, double heightFeet) = ResolveBubbleSize(element, view, anchor, configuration);
            target = new AccResolvedTarget(view, element, anchor, widthFeet, heightFeet);
            reason = usedFallbackView ? $"Resolved with fallback view '{view.Name}'." : "Resolved successfully.";
            return true;
        }

        private static View ResolveView(
            Document document,
            View activeView,
            AccSyncItem item,
            AccSyncConfiguration configuration,
            out bool usedFallback)
        {
            string[] candidates =
            {
                Lookup(configuration.ViewMappings, item.Location.ViewId),
                item.Location.ViewId,
                configuration.DefaultViewName,
            };

            foreach (string? candidate in candidates)
            {
                View? view = FindView(document, candidate);
                if (view != null)
                {
                    usedFallback = !string.IsNullOrWhiteSpace(configuration.DefaultViewName)
                        && string.Equals(candidate, configuration.DefaultViewName, StringComparison.OrdinalIgnoreCase);
                    return view;
                }
            }

            usedFallback = true;
            return activeView;
        }

        private static Element? ResolveElement(
            Document document,
            View view,
            AccSyncItem item,
            AccSyncConfiguration configuration)
        {
            string mappedElement = Lookup(configuration.ElementMappings, item.Location.ElementId);
            Element? element = FindElement(document, mappedElement) ?? FindElement(document, item.Location.ElementId);
            if (element != null)
            {
                return element;
            }

            XYZ? point = TryNormalizePoint(item.Location, configuration);
            if (point == null)
            {
                return null;
            }

            return FindNearestElement(document, view, point, configuration.SearchToleranceFeet);
        }

        private static XYZ? ResolveAnchorPoint(Element? element, AccSyncLocation location, AccSyncConfiguration configuration)
        {
            XYZ? normalizedPoint = TryNormalizePoint(location, configuration);
            if (normalizedPoint != null)
            {
                return normalizedPoint;
            }

            if (element == null)
            {
                return null;
            }

            BoundingBoxXYZ? box = element.get_BoundingBox(null);
            if (box == null)
            {
                return null;
            }

            return (box.Min + box.Max) / 2.0;
        }

        private static (double widthFeet, double heightFeet) ResolveBubbleSize(
            Element? element,
            View view,
            XYZ anchor,
            AccSyncConfiguration configuration)
        {
            if (element == null)
            {
                return (configuration.DefaultBubbleWidthFeet, configuration.DefaultBubbleHeightFeet);
            }

            BoundingBoxXYZ? box = element.get_BoundingBox(view) ?? element.get_BoundingBox(null);
            if (box == null)
            {
                return (configuration.DefaultBubbleWidthFeet, configuration.DefaultBubbleHeightFeet);
            }

            XYZ right = NormalizeOrFallback(view.RightDirection, XYZ.BasisX);
            XYZ up = NormalizeOrFallback(view.UpDirection, XYZ.BasisY);
            List<XYZ> corners = BuildBoundingBoxCorners(box);

            double minU = double.PositiveInfinity;
            double maxU = double.NegativeInfinity;
            double minV = double.PositiveInfinity;
            double maxV = double.NegativeInfinity;

            foreach (XYZ corner in corners)
            {
                XYZ relative = corner - anchor;
                double u = relative.DotProduct(right);
                double v = relative.DotProduct(up);
                minU = Math.Min(minU, u);
                maxU = Math.Max(maxU, u);
                minV = Math.Min(minV, v);
                maxV = Math.Max(maxV, v);
            }

            double width = Math.Max(maxU - minU + (configuration.BubblePaddingFeet * 2.0), configuration.DefaultBubbleWidthFeet);
            double height = Math.Max(maxV - minV + (configuration.BubblePaddingFeet * 2.0), configuration.DefaultBubbleHeightFeet);
            return (width, height);
        }

        private static View? FindView(Document document, string? key)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                return null;
            }

            string value = key.Trim();
            if (int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int viewId))
            {
                Element? element = document.GetElement(new ElementId(viewId));
                if (element is View directView && !directView.IsTemplate)
                {
                    return directView;
                }
            }

            Element? uniqueMatch = document.GetElement(value);
            if (uniqueMatch is View uniqueView && !uniqueView.IsTemplate)
            {
                return uniqueView;
            }

            return new FilteredElementCollector(document)
                .OfClass(typeof(View))
                .Cast<View>()
                .FirstOrDefault(candidate =>
                    !candidate.IsTemplate &&
                    (string.Equals(candidate.Name, value, StringComparison.OrdinalIgnoreCase)
                        || string.Equals(candidate.UniqueId, value, StringComparison.OrdinalIgnoreCase)
                        || string.Equals(candidate.Id.IntegerValue.ToString(CultureInfo.InvariantCulture), value, StringComparison.OrdinalIgnoreCase)));
        }

        private static Element? FindElement(Document document, string? key)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                return null;
            }

            string value = key.Trim();
            if (int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int elementId))
            {
                Element? byId = document.GetElement(new ElementId(elementId));
                if (byId != null)
                {
                    return byId;
                }
            }

            return document.GetElement(value);
        }

        private static Element? FindNearestElement(Document document, View view, XYZ point, double toleranceFeet)
        {
            double bestDistance = double.MaxValue;
            Element? best = null;

            foreach (Element element in new FilteredElementCollector(document, view.Id).WhereElementIsNotElementType())
            {
                Category? category = element.Category;
                if (category == null || category.CategoryType != CategoryType.Model)
                {
                    continue;
                }

                BoundingBoxXYZ? box = element.get_BoundingBox(view) ?? element.get_BoundingBox(null);
                if (box == null)
                {
                    continue;
                }

                XYZ center = (box.Min + box.Max) / 2.0;
                double distance = center.DistanceTo(point);
                if (distance <= toleranceFeet && distance < bestDistance)
                {
                    bestDistance = distance;
                    best = element;
                }
            }

            return best;
        }

        private static string Lookup(Dictionary<string, string> mapping, string key)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                return string.Empty;
            }

            foreach (KeyValuePair<string, string> pair in mapping)
            {
                if (string.Equals(pair.Key, key, StringComparison.OrdinalIgnoreCase))
                {
                    return pair.Value ?? string.Empty;
                }
            }

            return string.Empty;
        }

        private static XYZ? TryNormalizePoint(AccSyncLocation location, AccSyncConfiguration configuration)
        {
            if (location.X == null || location.Y == null)
            {
                return null;
            }

            double factor;
            switch ((configuration.CoordinateUnits ?? "feet").Trim().ToLowerInvariant())
            {
                case "meters":
                case "meter":
                case "m":
                    factor = 3.280839895;
                    break;
                case "millimeters":
                case "millimeter":
                case "mm":
                    factor = 0.003280839895;
                    break;
                case "feet":
                case "foot":
                case "ft":
                default:
                    factor = 1.0;
                    break;
            }

            return new XYZ(
                (location.X.Value * factor) + configuration.CoordinateOffset.X,
                (location.Y.Value * factor) + configuration.CoordinateOffset.Y,
                ((location.Z ?? 0.0) * factor) + configuration.CoordinateOffset.Z);
        }

        private static List<XYZ> BuildBoundingBoxCorners(BoundingBoxXYZ box)
        {
            XYZ min = box.Min;
            XYZ max = box.Max;
            return new List<XYZ>
            {
                new XYZ(min.X, min.Y, min.Z),
                new XYZ(min.X, min.Y, max.Z),
                new XYZ(min.X, max.Y, min.Z),
                new XYZ(min.X, max.Y, max.Z),
                new XYZ(max.X, min.Y, min.Z),
                new XYZ(max.X, min.Y, max.Z),
                new XYZ(max.X, max.Y, min.Z),
                new XYZ(max.X, max.Y, max.Z),
            };
        }

        private static XYZ NormalizeOrFallback(XYZ vector, XYZ fallback)
        {
            return vector == null || vector.GetLength() < 1e-9 ? fallback : vector.Normalize();
        }
    }
}
