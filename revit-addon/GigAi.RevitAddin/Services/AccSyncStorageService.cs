using System;
using System.IO;
using GigAi.RevitAddin.Models;
using GigAi.RevitAddin.Utils;
using Newtonsoft.Json;

namespace GigAi.RevitAddin.Services
{
    internal sealed class AccSyncStorageService
    {
        public string RootDirectory => ResolveRootDirectory();

        public string SnapshotPath
        {
            get
            {
                string configured = (Environment.GetEnvironmentVariable("GIGAI_ACC_SYNC_SNAPSHOT") ?? string.Empty).Trim();
                return !string.IsNullOrWhiteSpace(configured)
                    ? configured
                    : Path.Combine(RootDirectory, "latest-acc-items.json");
            }
        }

        public string StatePath
        {
            get
            {
                string configured = (Environment.GetEnvironmentVariable("GIGAI_ACC_SYNC_STATE") ?? string.Empty).Trim();
                return !string.IsNullOrWhiteSpace(configured)
                    ? configured
                    : Path.Combine(RootDirectory, "annotation-state.json");
            }
        }

        public string ConfigPath
        {
            get
            {
                string configured = (Environment.GetEnvironmentVariable("GIGAI_ACC_SYNC_CONFIG") ?? string.Empty).Trim();
                return !string.IsNullOrWhiteSpace(configured)
                    ? configured
                    : Path.Combine(RootDirectory, "config.json");
            }
        }

        public AccSyncPayload LoadSnapshot()
        {
            if (!File.Exists(SnapshotPath))
            {
                throw new FileNotFoundException("ACC snapshot file was not found.", SnapshotPath);
            }

            try
            {
                string raw = File.ReadAllText(SnapshotPath);
                AccSyncPayload? payload = JsonConvert.DeserializeObject<AccSyncPayload>(raw);
                if (payload == null)
                {
                    throw new InvalidOperationException("ACC snapshot JSON is empty or invalid.");
                }

                return payload;
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to read ACC snapshot '{SnapshotPath}'.", ex);
                throw;
            }
        }

        public AccSyncState LoadState()
        {
            if (!File.Exists(StatePath))
            {
                return new AccSyncState();
            }

            try
            {
                string raw = File.ReadAllText(StatePath);
                return JsonConvert.DeserializeObject<AccSyncState>(raw) ?? new AccSyncState();
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to read ACC sync state '{StatePath}'. Starting with an empty state.", ex);
                return new AccSyncState();
            }
        }

        public void SaveState(AccSyncState state)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(StatePath) ?? RootDirectory);
                File.WriteAllText(StatePath, JsonConvert.SerializeObject(state, Formatting.Indented));
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to write ACC sync state to '{StatePath}'.", ex);
                throw;
            }
        }

        public AccSyncConfiguration LoadConfiguration()
        {
            if (!File.Exists(ConfigPath))
            {
                return new AccSyncConfiguration();
            }

            try
            {
                string raw = File.ReadAllText(ConfigPath);
                return JsonConvert.DeserializeObject<AccSyncConfiguration>(raw) ?? new AccSyncConfiguration();
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to read ACC sync config '{ConfigPath}'. Using defaults.", ex);
                return new AccSyncConfiguration();
            }
        }

        private static string ResolveRootDirectory()
        {
            string configured = (Environment.GetEnvironmentVariable("GIGAI_ACC_SYNC_ROOT") ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(configured))
            {
                Directory.CreateDirectory(configured);
                return configured;
            }

            string path = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "GigAI",
                "acc-sync");
            Directory.CreateDirectory(path);
            return path;
        }
    }
}
