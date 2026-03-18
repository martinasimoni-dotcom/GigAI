using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Models
{
    public sealed class RevisionRequest
    {
        [JsonProperty("action")]
        public string Action { get; set; } = string.Empty;

        [JsonProperty("description")]
        public string Description { get; set; } = string.Empty;

        [JsonProperty("view_name")]
        public string ViewName { get; set; } = string.Empty;

        [JsonProperty("coordinates")]
        public List<List<double>> Coordinates { get; set; } = new List<List<double>>();

        [JsonProperty("issued")]
        public bool Issued { get; set; }

        [JsonProperty("request_id")]
        public string RequestId { get; set; } = string.Empty;

        [JsonProperty("source")]
        public string Source { get; set; } = "gigai";

        public IReadOnlyList<string> Validate()
        {
            var errors = new List<string>();

            if (!string.Equals(Action?.Trim(), "create_revision", StringComparison.OrdinalIgnoreCase))
            {
                errors.Add("action must be 'create_revision'.");
            }

            if (string.IsNullOrWhiteSpace(Description))
            {
                errors.Add("description is required.");
            }

            if (string.IsNullOrWhiteSpace(ViewName))
            {
                errors.Add("view_name is required.");
            }

            if (Coordinates == null || Coordinates.Count < 2)
            {
                errors.Add("coordinates must contain at least two points.");
                return errors;
            }

            for (int index = 0; index < Coordinates.Count; index++)
            {
                List<double> point = Coordinates[index];
                if (point == null || point.Count < 2)
                {
                    errors.Add($"coordinates[{index}] must contain at least X and Y values.");
                    continue;
                }

                if (point.Any(value => double.IsNaN(value) || double.IsInfinity(value)))
                {
                    errors.Add($"coordinates[{index}] contains invalid numeric values.");
                }
            }

            return errors;
        }

        public IList<Autodesk.Revit.DB.XYZ> ToXyzPoints()
        {
            return Coordinates
                .Select(values => new Autodesk.Revit.DB.XYZ(
                    values.ElementAtOrDefault(0),
                    values.ElementAtOrDefault(1),
                    values.ElementAtOrDefault(2)))
                .ToList();
        }
    }
}