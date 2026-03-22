using System.Collections.Generic;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Models
{
    internal sealed class AccSyncPayload
    {
        [JsonProperty("metadata")]
        public AccSyncMetadata Metadata { get; set; } = new AccSyncMetadata();

        [JsonProperty("items")]
        public List<AccSyncItem> Items { get; set; } = new List<AccSyncItem>();
    }

    internal sealed class AccSyncMetadata
    {
        [JsonProperty("generatedAt")]
        public string GeneratedAt { get; set; } = string.Empty;

        [JsonProperty("projectId")]
        public string ProjectId { get; set; } = string.Empty;

        [JsonProperty("itemsWritten")]
        public int ItemsWritten { get; set; }

        [JsonProperty("ignoredWithoutLocation")]
        public int IgnoredWithoutLocation { get; set; }

        [JsonProperty("newItems")]
        public int NewItems { get; set; }

        [JsonProperty("updatedItems")]
        public int UpdatedItems { get; set; }

        [JsonProperty("sources")]
        public List<string> Sources { get; set; } = new List<string>();
    }

    internal sealed class AccSyncItem
    {
        [JsonProperty("id")]
        public string Id { get; set; } = string.Empty;

        [JsonProperty("type")]
        public string Type { get; set; } = string.Empty;

        [JsonProperty("title")]
        public string Title { get; set; } = string.Empty;

        [JsonProperty("description")]
        public string Description { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("createdBy")]
        public string CreatedBy { get; set; } = string.Empty;

        [JsonProperty("assignedUser")]
        public string AssignedUser { get; set; } = string.Empty;

        [JsonProperty("dueDate")]
        public string DueDate { get; set; } = string.Empty;

        [JsonProperty("location")]
        public AccSyncLocation Location { get; set; } = new AccSyncLocation();

        [JsonProperty("sourceUpdatedAt")]
        public string SourceUpdatedAt { get; set; } = string.Empty;
    }

    internal sealed class AccSyncLocation
    {
        [JsonProperty("x")]
        public double? X { get; set; }

        [JsonProperty("y")]
        public double? Y { get; set; }

        [JsonProperty("z")]
        public double? Z { get; set; }

        [JsonProperty("elementId")]
        public string ElementId { get; set; } = string.Empty;

        [JsonProperty("viewId")]
        public string ViewId { get; set; } = string.Empty;

        [JsonProperty("modelUrn")]
        public string ModelUrn { get; set; } = string.Empty;

        [JsonProperty("sourceUrl")]
        public string SourceUrl { get; set; } = string.Empty;
    }
}
