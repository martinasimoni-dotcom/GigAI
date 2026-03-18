using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using GigAi.RevitAddin.Models;
using GigAi.RevitAddin.Utils;

namespace GigAi.RevitAddin.Services
{
    internal sealed class RevisionInputEnvelope
    {
        public RevisionInputEnvelope(RevisionRequest request, string sourcePath)
        {
            Request = request;
            SourcePath = sourcePath;
        }

        public RevisionRequest Request { get; }

        public string SourcePath { get; }
    }

    internal static class GigAiSyncRuntime
    {
        private static readonly object Sync = new object();

        private static InputListenerService? _listener;
        private static HttpInputListenerService? _httpListener;
        private static ExternalEvent? _externalEvent;
        private static GigAiRevisionEventHandler? _handler;
        private static bool _initialized;

        public static string InboxDirectory => ResolveInboxDirectory();

        public static void Initialize()
        {
            lock (Sync)
            {
                if (_initialized)
                {
                    return;
                }

                _handler = new GigAiRevisionEventHandler();
                _externalEvent = ExternalEvent.Create(_handler);
                _listener = new InputListenerService(InboxDirectory, EnqueueAndRaise);
                _httpListener = TryCreateHttpListener();

                foreach (string file in _listener.CollectPendingFiles())
                {
                    _listener.EnqueueFile(file);
                }

                _initialized = true;
                Logger.Info("GigAiSyncRuntime initialized.");
            }
        }

        public static void Shutdown()
        {
            lock (Sync)
            {
                _listener?.Dispose();
                _listener = null;
                _httpListener?.Dispose();
                _httpListener = null;
                _externalEvent?.Dispose();
                _externalEvent = null;
                _handler = null;
                _initialized = false;
                Logger.Info("GigAiSyncRuntime shutdown completed.");
            }
        }

        public static int TriggerManualSync()
        {
            EnsureInitialized();

            int count = 0;
            foreach (string file in _listener!.CollectPendingFiles())
            {
                _listener.EnqueueFile(file);
                count++;
            }

            return count;
        }

        private static void EnqueueAndRaise(RevisionInputEnvelope envelope)
        {
            _handler!.Enqueue(envelope);
            ExternalEventRequest request = _externalEvent!.Raise();
            Logger.Info($"Revision request queued from '{envelope.SourcePath}'. ExternalEvent status: {request}.");
        }

        private static string ResolveInboxDirectory()
        {
            string configured = (Environment.GetEnvironmentVariable("GIGAI_REVIT_INBOX") ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(configured))
            {
                Directory.CreateDirectory(configured);
                return configured;
            }

            string defaultPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "GigAI",
                "revit",
                "inbox");
            Directory.CreateDirectory(defaultPath);
            return defaultPath;
        }

        private static void EnsureInitialized()
        {
            if (_initialized)
            {
                return;
            }

            Initialize();
        }

        private static HttpInputListenerService? TryCreateHttpListener()
        {
            bool enabled = ParseBoolean(Environment.GetEnvironmentVariable("GIGAI_REVIT_HTTP_ENABLED"), defaultValue: true);
            if (!enabled)
            {
                Logger.Info("HTTP listener disabled by GIGAI_REVIT_HTTP_ENABLED=false.");
                return null;
            }

            string prefix = (Environment.GetEnvironmentVariable("GIGAI_REVIT_HTTP_PREFIX") ?? "http://127.0.0.1:8765/").Trim();
            string route = (Environment.GetEnvironmentVariable("GIGAI_REVIT_HTTP_ROUTE") ?? "/gigai/revit/revisions").Trim();

            try
            {
                return new HttpInputListenerService(prefix, route, EnqueueAndRaise);
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to start HTTP listener at '{prefix}{route}'.", ex);
                return null;
            }
        }

        private static bool ParseBoolean(string? value, bool defaultValue)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return defaultValue;
            }

            if (bool.TryParse(value, out bool parsed))
            {
                return parsed;
            }

            return defaultValue;
        }
    }

    internal sealed class GigAiRevisionEventHandler : IExternalEventHandler
    {
        private readonly ConcurrentQueue<RevisionInputEnvelope> _queue = new ConcurrentQueue<RevisionInputEnvelope>();
        private readonly RevisionService _revisionService = new RevisionService();
        private readonly CloudService _cloudService = new CloudService();

        public string GetName()
        {
            return "GigAI Revision Sync Handler";
        }

        public void Enqueue(RevisionInputEnvelope envelope)
        {
            _queue.Enqueue(envelope);
        }

        public void Execute(UIApplication app)
        {
            Document? document = ResolveTargetDocument(app);
            if (document == null)
            {
                Logger.Error("No active Revit project document is available for processing revision requests.");
                return;
            }

            while (_queue.TryDequeue(out RevisionInputEnvelope? envelope))
            {
                ProcessEnvelope(document, envelope);
            }
        }

        private void ProcessEnvelope(Document document, RevisionInputEnvelope envelope)
        {
            try
            {
                using (var transaction = new Transaction(document, "GigAI Create Revision Cloud"))
                {
                    transaction.Start();

                    Revision revision = _revisionService.CreateRevision(
                        document,
                        envelope.Request.Description,
                        envelope.Request.Issued);

                    View view = _cloudService.FindViewByName(document, envelope.Request.ViewName);
                    RevisionCloud cloud = _cloudService.CreateCloud(
                        document,
                        view,
                        revision.Id,
                        envelope.Request.ToXyzPoints());

                    transaction.Commit();

                    Logger.Info(
                        $"Processed revision request successfully. View='{view.Name}', RevisionId={revision.Id.Value}, CloudId={cloud.Id.Value}, RequestId='{envelope.Request.RequestId}'.");
                }

                MoveSourceFile(envelope.SourcePath, "processed");
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to process revision request from '{envelope.SourcePath}'.", ex);
                MoveSourceFile(envelope.SourcePath, "failed");
            }
        }

        private static Document? ResolveTargetDocument(UIApplication app)
        {
            if (app.ActiveUIDocument?.Document != null)
            {
                return app.ActiveUIDocument.Document;
            }

            return app.Application.Documents
                .Cast<Document>()
                .FirstOrDefault(document => !document.IsFamilyDocument);
        }

        private static void MoveSourceFile(string sourcePath, string bucket)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(sourcePath) || !File.Exists(sourcePath))
                {
                    return;
                }

                string inbox = GigAiSyncRuntime.InboxDirectory;
                string archiveRoot = Path.Combine(Path.GetDirectoryName(inbox) ?? inbox, bucket);
                Directory.CreateDirectory(archiveRoot);

                string fileName = Path.GetFileNameWithoutExtension(sourcePath);
                string extension = Path.GetExtension(sourcePath);
                string stampedName = $"{DateTime.UtcNow:yyyyMMddTHHmmssfffZ}_{fileName}{extension}";
                string destinationPath = Path.Combine(archiveRoot, stampedName);

                File.Move(sourcePath, destinationPath);
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to archive source file '{sourcePath}' to '{bucket}'.", ex);
            }
        }
    }
}