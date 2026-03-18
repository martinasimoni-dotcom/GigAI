using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using GigAi.RevitAddin.Models;
using GigAi.RevitAddin.Utils;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Services
{
    internal sealed class InputListenerService : IDisposable
    {
        private readonly FileSystemWatcher _watcher;
        private readonly ConcurrentDictionary<string, byte> _pendingPaths = new ConcurrentDictionary<string, byte>(StringComparer.OrdinalIgnoreCase);
        private readonly Action<RevisionInputEnvelope> _onRequest;
        private readonly string _inboxDirectory;

        public InputListenerService(string inboxDirectory, Action<RevisionInputEnvelope> onRequest)
        {
            _inboxDirectory = inboxDirectory;
            _onRequest = onRequest;

            Directory.CreateDirectory(_inboxDirectory);

            _watcher = new FileSystemWatcher(_inboxDirectory, "*.json")
            {
                IncludeSubdirectories = false,
                NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.CreationTime,
                EnableRaisingEvents = true
            };

            _watcher.Created += OnFileChanged;
            _watcher.Changed += OnFileChanged;
            _watcher.Renamed += OnFileRenamed;
            _watcher.Error += OnWatcherError;

            Logger.Info($"InputListenerService started. Inbox: {_inboxDirectory}");
        }

        public IReadOnlyList<string> CollectPendingFiles()
        {
            return Directory
                .EnumerateFiles(_inboxDirectory, "*.json", SearchOption.TopDirectoryOnly)
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        public void EnqueueFile(string path)
        {
            if (string.IsNullOrWhiteSpace(path) || !path.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            if (!_pendingPaths.TryAdd(path, 0))
            {
                return;
            }

            try
            {
                RevisionRequest request = ReadRequest(path);
                var envelope = new RevisionInputEnvelope(request, path);
                _onRequest(envelope);
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to read request file '{path}'.", ex);
            }
            finally
            {
                _pendingPaths.TryRemove(path, out _);
            }
        }

        public void Dispose()
        {
            _watcher.Created -= OnFileChanged;
            _watcher.Changed -= OnFileChanged;
            _watcher.Renamed -= OnFileRenamed;
            _watcher.Error -= OnWatcherError;
            _watcher.Dispose();
        }

        private void OnFileChanged(object sender, FileSystemEventArgs args)
        {
            EnqueueFile(args.FullPath);
        }

        private void OnFileRenamed(object sender, RenamedEventArgs args)
        {
            EnqueueFile(args.FullPath);
        }

        private static RevisionRequest ReadRequest(string path)
        {
            const int maxAttempts = 8;
            const int delayMilliseconds = 120;

            Exception? lastException = null;

            for (int attempt = 1; attempt <= maxAttempts; attempt++)
            {
                try
                {
                    string raw = File.ReadAllText(path);
                    RevisionRequest? request = JsonConvert.DeserializeObject<RevisionRequest>(raw);
                    if (request == null)
                    {
                        throw new InvalidOperationException("JSON payload is empty or invalid.");
                    }

                    IReadOnlyList<string> errors = request.Validate();
                    if (errors.Count > 0)
                    {
                        throw new InvalidOperationException(string.Join(" ", errors));
                    }

                    return request;
                }
                catch (IOException ex)
                {
                    lastException = ex;
                    Thread.Sleep(delayMilliseconds);
                }
                catch (UnauthorizedAccessException ex)
                {
                    lastException = ex;
                    Thread.Sleep(delayMilliseconds);
                }
            }

            throw new InvalidOperationException(
                $"Could not read input file '{path}' after {maxAttempts} attempts.",
                lastException);
        }

        private static void OnWatcherError(object sender, ErrorEventArgs args)
        {
            Logger.Error("File watcher encountered an error.", args.GetException());
        }
    }
}