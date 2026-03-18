using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using GigAi.RevitAddin.Models;
using GigAi.RevitAddin.Utils;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Services
{
    internal sealed class HttpInputListenerService : IDisposable
    {
        private readonly HttpListener _listener;
        private readonly Action<RevisionInputEnvelope> _onRequest;
        private readonly CancellationTokenSource _cts = new CancellationTokenSource();
        private readonly Task _worker;
        private readonly string _routePath;

        public HttpInputListenerService(string prefix, string routePath, Action<RevisionInputEnvelope> onRequest)
        {
            _onRequest = onRequest;
            _routePath = NormalizeRoute(routePath);

            _listener = new HttpListener();
            _listener.Prefixes.Add(EnsureTrailingSlash(prefix));
            _listener.Start();

            _worker = Task.Run(() => ListenLoop(_cts.Token), _cts.Token);
            Logger.Info($"HTTP listener started. Prefix='{prefix}', Route='{_routePath}'.");
        }

        public void Dispose()
        {
            try
            {
                _cts.Cancel();
                _listener.Stop();
                _listener.Close();
                _worker.Wait(TimeSpan.FromSeconds(2));
            }
            catch
            {
                // Best effort shutdown.
            }
            finally
            {
                _cts.Dispose();
            }
        }

        private async Task ListenLoop(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                HttpListenerContext context;
                try
                {
                    context = await _listener.GetContextAsync().ConfigureAwait(false);
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (HttpListenerException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Logger.Error("HTTP listener loop failure.", ex);
                    continue;
                }

                _ = Task.Run(() => HandleContext(context), cancellationToken);
            }
        }

        private void HandleContext(HttpListenerContext context)
        {
            try
            {
                if (!string.Equals(context.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                {
                    WriteJson(context.Response, 405, new { error = "Only POST is supported." });
                    return;
                }

                string requestPath = (context.Request.Url?.AbsolutePath ?? "/").TrimEnd('/');
                if (!string.Equals(requestPath, _routePath, StringComparison.OrdinalIgnoreCase))
                {
                    WriteJson(context.Response, 404, new { error = "Route not found." });
                    return;
                }

                string rawBody;
                using (var reader = new StreamReader(context.Request.InputStream, context.Request.ContentEncoding ?? Encoding.UTF8))
                {
                    rawBody = reader.ReadToEnd();
                }

                RevisionRequest? request = JsonConvert.DeserializeObject<RevisionRequest>(rawBody);
                if (request == null)
                {
                    WriteJson(context.Response, 400, new { error = "Request body is empty or invalid JSON." });
                    return;
                }

                var validation = request.Validate();
                if (validation.Count > 0)
                {
                    WriteJson(context.Response, 400, new { error = "Validation failed.", details = validation });
                    return;
                }

                string source = "webhook:" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ");
                _onRequest(new RevisionInputEnvelope(request, source));

                WriteJson(context.Response, 202, new { status = "accepted", request_id = request.RequestId });
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to process HTTP revision request.", ex);
                WriteJson(context.Response, 500, new { error = "Internal server error." });
            }
        }

        private static void WriteJson(HttpListenerResponse response, int statusCode, object payload)
        {
            try
            {
                response.StatusCode = statusCode;
                response.ContentType = "application/json";

                string json = JsonConvert.SerializeObject(payload);
                byte[] bytes = Encoding.UTF8.GetBytes(json);
                response.ContentLength64 = bytes.LongLength;

                using (Stream output = response.OutputStream)
                {
                    output.Write(bytes, 0, bytes.Length);
                }
            }
            catch
            {
                // Response may already be closed.
            }
        }

        private static string EnsureTrailingSlash(string prefix)
        {
            if (string.IsNullOrWhiteSpace(prefix))
            {
                throw new InvalidOperationException("HTTP listener prefix is required.");
            }

            return prefix.EndsWith("/", StringComparison.Ordinal) ? prefix : prefix + "/";
        }

        private static string NormalizeRoute(string routePath)
        {
            if (string.IsNullOrWhiteSpace(routePath))
            {
                return "/";
            }

            string normalized = routePath.Trim();
            if (!normalized.StartsWith("/", StringComparison.Ordinal))
            {
                normalized = "/" + normalized;
            }

            return normalized.TrimEnd('/');
        }
    }
}