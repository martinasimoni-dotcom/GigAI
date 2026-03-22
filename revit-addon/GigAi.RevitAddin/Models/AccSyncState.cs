using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Models
{
    internal sealed class AccSyncState
    {
        [JsonProperty("entries")]
        public List<AccSyncStateEntry> Entries { get; set; } = new List<AccSyncStateEntry>();
    }

    internal sealed class AccSyncStateEntry
    {
        [JsonProperty("sync_key")]
        public string SyncKey { get; set; } = string.Empty;

        [JsonProperty("source_id")]
        public string SourceId { get; set; } = string.Empty;

        [JsonProperty("source_type")]
        public string SourceType { get; set; } = string.Empty;

        [JsonProperty("element_ref")]
        public string ElementRef { get; set; } = string.Empty;

        [JsonProperty("view_ref")]
        public string ViewRef { get; set; } = string.Empty;

        [JsonProperty("cloud_id")]
        public long CloudId { get; set; }

        [JsonProperty("note_id")]
        public long NoteId { get; set; }

        [JsonProperty("payload_hash")]
        public string PayloadHash { get; set; } = string.Empty;

        [JsonProperty("last_synced_at")]
        [JsonConverter(typeof(Newtonsoft.Json.Converters.IsoDateTimeConverter))]
        public DateTimeOffset? LastSyncedAt { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;
    }

    internal sealed class AccSyncConfiguration
    {
        [JsonProperty("defaultViewName")]
        public string DefaultViewName { get; set; } = string.Empty;

        [JsonProperty("coordinateUnits")]
        public string CoordinateUnits { get; set; } = "feet";

        [JsonProperty("coordinateOffset")]
        public AccSyncPoint CoordinateOffset { get; set; } = new AccSyncPoint();

        [JsonProperty("searchToleranceFeet")]
        public double SearchToleranceFeet { get; set; } = 12.0;

        [JsonProperty("bubblePaddingFeet")]
        public double BubblePaddingFeet { get; set; } = 2.0;

        [JsonProperty("defaultBubbleWidthFeet")]
        public double DefaultBubbleWidthFeet { get; set; } = 8.0;

        [JsonProperty("defaultBubbleHeightFeet")]
        public double DefaultBubbleHeightFeet { get; set; } = 4.0;

        [JsonProperty("viewMappings")]
        public Dictionary<string, string> ViewMappings { get; set; } = new Dictionary<string, string>();

        [JsonProperty("elementMappings")]
        public Dictionary<string, string> ElementMappings { get; set; } = new Dictionary<string, string>();
    }

    internal sealed class AccSyncPoint
    {
        [JsonProperty("x")]
        public double X { get; set; }

        [JsonProperty("y")]
        public double Y { get; set; }

        [JsonProperty("z")]
        public double Z { get; set; }
    }
}
