using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;

namespace GigAi.RevitAddin.Services
{
    internal sealed class CloudService
    {
        public View FindViewByName(Document document, string viewName)
        {
            View? view = new FilteredElementCollector(document)
                .OfClass(typeof(View))
                .Cast<View>()
                .FirstOrDefault(candidate =>
                    !candidate.IsTemplate &&
                    string.Equals(candidate.Name, viewName, StringComparison.OrdinalIgnoreCase));

            if (view == null)
            {
                throw new InvalidOperationException($"View '{viewName}' was not found.");
            }

            if (view is View3D)
            {
                throw new InvalidOperationException(
                    $"View '{viewName}' is a 3D view. Revision clouds must be placed in graphical non-3D views or sheets.");
            }

            return view;
        }

        public RevisionCloud CreateCloud(Document document, View view, ElementId revisionId, IList<XYZ> points)
        {
            IList<Curve> curves = BuildCloudCurves(points);
            if (curves.Count == 0)
            {
                throw new InvalidOperationException("No valid curves could be generated for revision cloud creation.");
            }

            return RevisionCloud.Create(document, view, revisionId, curves);
        }

        private static IList<Curve> BuildCloudCurves(IList<XYZ> points)
        {
            if (points == null || points.Count < 2)
            {
                throw new InvalidOperationException("At least two coordinates are required.");
            }

            IList<XYZ> projected = ProjectToSinglePlane(points);
            var curves = new List<Curve>();

            for (int index = 1; index < projected.Count; index++)
            {
                XYZ start = projected[index - 1];
                XYZ end = projected[index];
                if (!start.IsAlmostEqualTo(end))
                {
                    curves.Add(Line.CreateBound(start, end));
                }
            }

            bool shouldCloseLoop = projected.Count >= 3;
            if (shouldCloseLoop && !projected[0].IsAlmostEqualTo(projected[projected.Count - 1]))
            {
                curves.Add(Line.CreateBound(projected[projected.Count - 1], projected[0]));
            }

            return curves;
        }

        private static IList<XYZ> ProjectToSinglePlane(IList<XYZ> points)
        {
            double z = points[0].Z;
            return points.Select(point => new XYZ(point.X, point.Y, z)).ToList();
        }
    }
}