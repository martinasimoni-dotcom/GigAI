using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace GigAi.RevitAddin
{
    internal static class GigAiApiClient
    {
        private static readonly int[] PreferredLocalPorts = { 8011, 8000, 8010 };
        private static readonly TimeSpan ProbeTimeout = TimeSpan.FromMilliseconds(1200);
        private static readonly TimeSpan StartupWaitTimeout = TimeSpan.FromSeconds(12);
        private static readonly HttpClient Http = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(20)
        };

        public static VoiceCommandResponse SendVoiceCommand(string apiUrl, VoiceCommandRequest payload)
        {
            Uri endpoint = ResolveReachableEndpoint(apiUrl, "/voice/command");
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

        public static VoiceAudioCommandResponse SendVoiceAudioCommand(string apiUrl, VoiceCommandAudioRequest payload)
        {
            Uri endpoint = ResolveReachableEndpoint(apiUrl, "/voice/command/audio");
            string json = JsonConvert.SerializeObject(payload);

            try
            {
                using StringContent content = new StringContent(json, Encoding.UTF8, "application/json");
                HttpResponseMessage response = Http.PostAsync(endpoint, content).GetAwaiter().GetResult();
                string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();

                if (!response.IsSuccessStatusCode)
                {
                    throw new InvalidOperationException(
                        $"GigAI audio API call failed ({(int)response.StatusCode}) on {endpoint}. Response: {body}"
                    );
                }

                VoiceAudioCommandResponse? parsed = JsonConvert.DeserializeObject<VoiceAudioCommandResponse>(body);
                if (parsed == null || parsed.Pipeline == null)
                {
                    throw new InvalidOperationException("GigAI audio API returned empty or invalid JSON.");
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
            Uri requestedEndpoint = NormalizeVoiceEndpoint(apiUrl);
            Uri endpoint = ResolveReachableEndpoint(apiUrl, "/voice/command");
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

                if (AreEquivalentEndpoints(requestedEndpoint, endpoint))
                {
                    return $"Connected successfully to {healthEndpoint}.";
                }

                return
                    $"Connected successfully to {healthEndpoint}.\n" +
                    $"Requested endpoint {requestedEndpoint} was unreachable, so GigAI auto-detected {endpoint}.";
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
            Uri endpoint = ResolveReachableEndpoint(apiUrl, "/revit/revision-marked");
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
            string host = string.IsNullOrWhiteSpace(endpoint.Host) ? "127.0.0.1" : endpoint.Host;
            int port = endpoint.IsDefaultPort ? (endpoint.Scheme == Uri.UriSchemeHttps ? 443 : 80) : endpoint.Port;
            string docsUrl = $"{endpoint.Scheme}://{host}:{port}/docs";
            string startScriptHint = FindStartApiScriptPath() is string scriptPath
                ? $"2. Start API: powershell -ExecutionPolicy Bypass -File \"{scriptPath}\" -App orchestrator -Port {port} -Reload\n"
                : $"2. Start API: powershell -ExecutionPolicy Bypass -File .\\start-api.ps1 -App orchestrator -Port {port} -Reload\n";

            return
                $"Could not connect to GigAI API.\n" +
                $"Endpoint: {endpoint}\n" +
                $"Details: {details}\n\n" +
                "Fix:\n" +
                $"1. Make sure the API is running on your machine ({host}:{port}).\n" +
                startScriptHint +
                $"3. Open {docsUrl} in browser to confirm the API is reachable.\n" +
                "4. If you changed the port, update the API URL in the GigAI dialog accordingly.\n" +
                "5. If you still can’t connect, check firewall / VPN settings that may block localhost connections.";
        }

        private static string? FindStartApiScriptPath()
        {
            try
            {
                string configuredScript = Environment.GetEnvironmentVariable("GIGAI_START_API_SCRIPT") ?? string.Empty;
                if (!string.IsNullOrWhiteSpace(configuredScript) && File.Exists(configuredScript))
                {
                    return configuredScript;
                }

                string configuredProjectRoot = Environment.GetEnvironmentVariable("GIGAI_PROJECT_ROOT") ?? string.Empty;
                if (!string.IsNullOrWhiteSpace(configuredProjectRoot))
                {
                    string configuredCandidate = Path.Combine(configuredProjectRoot, "start-api.ps1");
                    if (File.Exists(configuredCandidate))
                    {
                        return configuredCandidate;
                    }
                }

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

                string desktopDir = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                if (!string.IsNullOrWhiteSpace(desktopDir))
                {
                    string desktopCandidate = Path.Combine(desktopDir, "GigAi", "start-api.ps1");
                    if (File.Exists(desktopCandidate))
                    {
                        return desktopCandidate;
                    }
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

        private static Uri ResolveReachableEndpoint(string rawApiUrl, string defaultPath)
        {
            Uri requestedEndpoint = NormalizeEndpoint(rawApiUrl, defaultPath);
            Uri? reachable = TryResolveReachableEndpoint(requestedEndpoint);
            if (reachable != null)
            {
                return reachable;
            }

            if (TryStartLocalApi(requestedEndpoint))
            {
                reachable = WaitForReachableEndpoint(requestedEndpoint, StartupWaitTimeout);
                if (reachable != null)
                {
                    return reachable;
                }
            }

            return requestedEndpoint;
        }

        private static Uri? TryResolveReachableEndpoint(Uri requestedEndpoint)
        {
            foreach (Uri candidate in BuildEndpointCandidates(requestedEndpoint))
            {
                if (TryReachHealthEndpoint(candidate))
                {
                    return candidate;
                }
            }

            return null;
        }

        private static IEnumerable<Uri> BuildEndpointCandidates(Uri requestedEndpoint)
        {
            yield return requestedEndpoint;

            if (!IsLoopbackHost(requestedEndpoint.Host))
            {
                yield break;
            }

            List<int> ports = new List<int>();
            AddCandidatePort(ports, requestedEndpoint.Port);

            foreach (int preferredPort in PreferredLocalPorts)
            {
                AddCandidatePort(ports, preferredPort);
            }

            for (int offset = 1; offset <= 10; offset++)
            {
                AddCandidatePort(ports, requestedEndpoint.Port + offset);
            }

            foreach (int port in ports)
            {
                Uri candidate = CreateEndpointWithPort(requestedEndpoint, port);
                if (!AreEquivalentEndpoints(requestedEndpoint, candidate))
                {
                    yield return candidate;
                }
            }
        }

        private static void AddCandidatePort(ICollection<int> ports, int port)
        {
            if (port <= 0 || ports.Contains(port))
            {
                return;
            }

            ports.Add(port);
        }

        private static bool TryReachHealthEndpoint(Uri endpoint)
        {
            try
            {
                using HttpClient probe = new HttpClient
                {
                    Timeout = ProbeTimeout
                };

                HttpResponseMessage response = probe.GetAsync(BuildHealthEndpoint(endpoint)).GetAwaiter().GetResult();
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        private static Uri? WaitForReachableEndpoint(Uri requestedEndpoint, TimeSpan timeout)
        {
            DateTime deadline = DateTime.UtcNow.Add(timeout);
            while (DateTime.UtcNow < deadline)
            {
                Uri? reachable = TryResolveReachableEndpoint(requestedEndpoint);
                if (reachable != null)
                {
                    return reachable;
                }

                Thread.Sleep(500);
            }

            return null;
        }

        private static Uri CreateEndpointWithPort(Uri endpoint, int port)
        {
            UriBuilder builder = new UriBuilder(endpoint)
            {
                Port = port,
                Path = endpoint.AbsolutePath,
                Query = endpoint.Query.TrimStart('?')
            };

            return builder.Uri;
        }

        private static bool IsLoopbackHost(string host)
        {
            if (string.Equals(host, "localhost", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            return IPAddress.TryParse(host, out IPAddress? address) && IPAddress.IsLoopback(address);
        }

        private static bool AreEquivalentEndpoints(Uri left, Uri right)
        {
            return Uri.Compare(
                left,
                right,
                UriComponents.SchemeAndServer | UriComponents.PathAndQuery,
                UriFormat.Unescaped,
                StringComparison.OrdinalIgnoreCase
            ) == 0;
        }

        private static bool TryStartLocalApi(Uri requestedEndpoint)
        {
            if (!IsLoopbackHost(requestedEndpoint.Host))
            {
                return false;
            }

            string? scriptPath = FindStartApiScriptPath();
            if (string.IsNullOrWhiteSpace(scriptPath) || !File.Exists(scriptPath))
            {
                return false;
            }

            int port = requestedEndpoint.IsDefaultPort
                ? (requestedEndpoint.Scheme == Uri.UriSchemeHttps ? 443 : 80)
                : requestedEndpoint.Port;

            try
            {
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = "powershell",
                    Arguments = $"-ExecutionPolicy Bypass -File \"{scriptPath}\" -App orchestrator -Port {port}",
                    WorkingDirectory = Path.GetDirectoryName(scriptPath) ?? Environment.CurrentDirectory,
                    UseShellExecute = true,
                    WindowStyle = ProcessWindowStyle.Minimized,
                };

                Process.Start(startInfo);
                return true;
            }
            catch
            {
                return false;
            }
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

    public class VoiceCommandAudioRequest
    {
        [JsonProperty("projectId")]
        public string ProjectId { get; set; } = "project_alpha";

        [JsonProperty("audio_base64")]
        public string AudioBase64 { get; set; } = string.Empty;

        [JsonProperty("language")]
        public string Language { get; set; } = "en";

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

    public class VoiceAudioCommandResponse
    {
        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("transcript")]
        public string Transcript { get; set; } = string.Empty;

        [JsonProperty("transcript_original")]
        public string TranscriptOriginal { get; set; } = string.Empty;

        [JsonProperty("pipeline")]
        public VoiceCommandResponse Pipeline { get; set; } = new VoiceCommandResponse();
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

        [JsonProperty("applied_at")]
        public string AppliedAt { get; set; } = DateTime.UtcNow.ToString("o");

        [JsonProperty("meeting_title")]
        public string MeetingTitle { get; set; } = "Revit Revision";

        [JsonProperty("view_name")]
        public string ViewName { get; set; } = string.Empty;

        [JsonProperty("view_type")]
        public string ViewType { get; set; } = string.Empty;

        [JsonProperty("cloud_id")]
        public string CloudId { get; set; } = string.Empty;

        [JsonProperty("note_id")]
        public string NoteId { get; set; } = string.Empty;

        [JsonProperty("priority")]
        public string Priority { get; set; } = "HIGH";
    }
}
