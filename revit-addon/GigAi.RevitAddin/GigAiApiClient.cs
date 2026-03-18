using System;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace GigAi.RevitAddin
{
    internal static class GigAiApiClient
    {
        private static readonly HttpClient Http = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(20)
        };

        public static VoiceCommandResponse SendVoiceCommand(string apiUrl, VoiceCommandRequest payload)
        {
            Uri endpoint = NormalizeVoiceEndpoint(apiUrl);
            string json = JsonConvert.SerializeObject(payload);

            try
            {
                using StringContent content = new StringContent(json, Encoding.UTF8, "application/json");
                HttpResponseMessage response = Http.PostAsync(endpoint, content).GetAwaiter().GetResult();
                string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();

                if (!response.IsSuccessStatusCode)
                {
                    throw new InvalidOperationException(
                        $"GigAI API call failed ({(int)response.StatusCode}) on {endpoint}. Response: {body}"
                    );
                }

                VoiceCommandResponse? parsed = JsonConvert.DeserializeObject<VoiceCommandResponse>(body);
                if (parsed == null)
                {
                    throw new InvalidOperationException("GigAI API returned empty or invalid JSON.");
                }

                return parsed;
            }
            catch (TaskCanceledException ex)
            {
                throw new InvalidOperationException(
                    $"Request timed out while calling {endpoint}. Confirm the API is running and reachable.",
                    ex
                );
            }
            catch (HttpRequestException ex)
            {
                throw new InvalidOperationException(BuildConnectionError(endpoint, ex), ex);
            }
        }

        public static string TestConnection(string apiUrl)
        {
            Uri endpoint = NormalizeVoiceEndpoint(apiUrl);
            Uri healthEndpoint = BuildHealthEndpoint(endpoint);

            try
            {
                HttpResponseMessage response = Http.GetAsync(healthEndpoint).GetAwaiter().GetResult();
                string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                if (!response.IsSuccessStatusCode)
                {
                    throw new InvalidOperationException(
                        $"Health check failed ({(int)response.StatusCode}) on {healthEndpoint}. Response: {body}"
                    );
                }

                return $"Connected successfully to {healthEndpoint}.";
            }
            catch (TaskCanceledException ex)
            {
                throw new InvalidOperationException(
                    $"Health check timed out on {healthEndpoint}.",
                    ex
                );
            }
            catch (HttpRequestException ex)
            {
                throw new InvalidOperationException(BuildConnectionError(endpoint, ex), ex);
            }
        }

        public static string NotifyRevisionMarked(string apiUrl, RevisionMarkedRequest payload)
        {
            Uri endpoint = NormalizeEndpoint(apiUrl, "/revit/revision-marked");
            string json = JsonConvert.SerializeObject(payload);

            try
            {
                using StringContent content = new StringContent(json, Encoding.UTF8, "application/json");
                HttpResponseMessage response = Http.PostAsync(endpoint, content).GetAwaiter().GetResult();
                string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();

                if (!response.IsSuccessStatusCode)
                {
                    throw new InvalidOperationException(
                        $"Revision webhook failed ({(int)response.StatusCode}) on {endpoint}. Response: {body}"
                    );
                }

                return body;
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException(
                    $"Could not notify revision-marked webhook at {endpoint}. {ex.Message}",
                    ex
                );
            }
        }

        private static string BuildConnectionError(Uri endpoint, HttpRequestException ex)
        {
            string details = ex.InnerException?.Message ?? ex.Message;
            string startScriptHint = FindStartApiScriptPath() is string scriptPath
                ? $"2. Start API: powershell -ExecutionPolicy Bypass -File \"{scriptPath}\" -Reload\n"
                : "2. Start API: powershell -ExecutionPolicy Bypass -File .\\start-api.ps1 -Reload\n";

            return
                $"Could not connect to GigAI API.\n" +
                $"Endpoint: {endpoint}\n" +
                $"Details: {details}\n\n" +
                "Fix:\n" +
                "1. Make sure the API is running on your machine (127.0.0.1:8000).\n" +
                startScriptHint +
                "3. Open http://127.0.0.1:8000/docs in browser to confirm the API is reachable.\n" +
                "4. If you changed the port, update the API URL in the GigAI dialog accordingly.\n" +
                "5. If you still can’t connect, check firewall / VPN settings that may block localhost connections.";
        }

        private static string? FindStartApiScriptPath()
        {
            try
            {
                string assemblyDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? string.Empty;
                string current = assemblyDir;
                for (int i = 0; i < 8; i++)
                {
                    string candidate = Path.Combine(current, "start-api.ps1");
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }

                    string parent = Path.GetDirectoryName(current);
                    if (string.IsNullOrEmpty(parent) || parent == current)
                    {
                        break;
                    }

                    current = parent;
                }
            }
            catch
            {
                // Best effort only; ignore errors.
            }

            return null;
        }

        private static Uri NormalizeVoiceEndpoint(string rawApiUrl)
        {
            return NormalizeEndpoint(rawApiUrl, "/voice/command");
        }

        private static Uri NormalizeEndpoint(string rawApiUrl, string defaultPath)
        {
            string raw = (rawApiUrl ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(raw))
            {
                throw new InvalidOperationException("API URL is required.");
            }

            if (!raw.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
                !raw.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                raw = "http://" + raw;
            }

            if (!Uri.TryCreate(raw, UriKind.Absolute, out Uri? uri))
            {
                throw new InvalidOperationException($"Invalid API URL: {rawApiUrl}");
            }

            if (uri.AbsolutePath == "/" || string.IsNullOrWhiteSpace(uri.AbsolutePath))
            {
                return new Uri(uri, defaultPath);
            }

            if (uri.AbsolutePath.IndexOf(defaultPath, StringComparison.OrdinalIgnoreCase) < 0)
            {
                return new Uri(uri, defaultPath);
            }

            return uri;
        }

        private static Uri BuildHealthEndpoint(Uri endpoint)
        {
            return new Uri(endpoint, "/health");
        }
    }

    public class VoiceCommandRequest
    {
        [JsonProperty("projectId")]
        public string ProjectId { get; set; } = "project_alpha";

        [JsonProperty("transcript")]
        public string Transcript { get; set; } = string.Empty;

        [JsonProperty("fireflies_latest")]
        public bool FirefliesLatest { get; set; }

        [JsonProperty("available_spaces")]
        public string[] AvailableSpaces { get; set; } = Array.Empty<string>();

        [JsonProperty("visible_spaces")]
        public string[] VisibleSpaces { get; set; } = Array.Empty<string>();

        [JsonProperty("drawing_context")]
        public DrawingContext DrawingContext { get; set; } = new DrawingContext();
    }

    public class DrawingContext
    {
        [JsonProperty("view_name")]
        public string ViewName { get; set; } = string.Empty;

        [JsonProperty("view_type")]
        public string ViewType { get; set; } = string.Empty;

        [JsonProperty("view_scale")]
        public int ViewScale { get; set; }
    }

    public class VoiceCommandResponse
    {
        [JsonProperty("event")]
        public VoiceCommandEvent Event { get; set; } = new VoiceCommandEvent();

        [JsonProperty("decision")]
        public VoiceCommandDecision Decision { get; set; } = new VoiceCommandDecision();

        [JsonProperty("action")]
        public VoiceCommandAction Action { get; set; } = new VoiceCommandAction();
    }

    public class VoiceCommandEvent
    {
        [JsonProperty("focus_space")]
        public string FocusSpace { get; set; } = string.Empty;

        [JsonProperty("focus_reason")]
        public string FocusReason { get; set; } = string.Empty;
    }

    public class VoiceCommandDecision
    {
        [JsonProperty("proposal")]
        public string Proposal { get; set; } = string.Empty;

        [JsonProperty("confidence")]
        public double Confidence { get; set; }

        [JsonProperty("risk_level")]
        public string RiskLevel { get; set; } = string.Empty;

        [JsonProperty("alternatives")]
        public string[] Alternatives { get; set; } = Array.Empty<string>();
    }

    public class VoiceCommandAction
    {
        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("reason")]
        public string Reason { get; set; } = string.Empty;

        [JsonProperty("outputs")]
        public VoiceCommandOutputs Outputs { get; set; } = new VoiceCommandOutputs();
    }

    public class VoiceCommandOutputs
    {
        [JsonProperty("bim360")]
        public string Bim360 { get; set; } = string.Empty;

        [JsonProperty("dashboard")]
        public string Dashboard { get; set; } = string.Empty;

        [JsonProperty("email")]
        public string Email { get; set; } = string.Empty;
    }

    public class RevisionMarkedRequest
    {
        [JsonProperty("revision_id")]
        public string RevisionId { get; set; } = string.Empty;

        [JsonProperty("meeting_id")]
        public string MeetingId { get; set; } = "meet_revit";

        [JsonProperty("project_id")]
        public string ProjectId { get; set; } = "project_alpha";

        [JsonProperty("space_name")]
        public string SpaceName { get; set; } = string.Empty;

        [JsonProperty("element_type")]
        public string ElementType { get; set; } = "room";

        [JsonProperty("action")]
        public string Action { get; set; } = "REVISION_MARKED";

        [JsonProperty("comment_text")]
        public string CommentText { get; set; } = string.Empty;

        [JsonProperty("applied_by")]
        public string AppliedBy { get; set; } = Environment.UserName;
    }
}
