using System;
using System.Globalization;
using System.IO;

namespace GigAi.RevitAddin.Utils
{
    internal static class Logger
    {
        private static readonly object Sync = new object();

        private static readonly string LogFilePath = ResolveLogFilePath();

        public static void Info(string message)
        {
            Write("INFO", message, null);
        }

        public static void Error(string message, Exception? exception = null)
        {
            Write("ERROR", message, exception);
        }

        private static string ResolveLogFilePath()
        {
            string configured = (Environment.GetEnvironmentVariable("GIGAI_REVIT_LOG") ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(configured))
            {
                return configured;
            }

            string root = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "GigAI",
                "revit");
            return Path.Combine(root, "gigai-revit-addon.log");
        }

        private static void Write(string level, string message, Exception? exception)
        {
            try
            {
                string directory = Path.GetDirectoryName(LogFilePath) ?? string.Empty;
                if (!string.IsNullOrWhiteSpace(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                string timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
                string line = $"{timestamp} [{level}] {message}";
                if (exception != null)
                {
                    line += $"{Environment.NewLine}{exception}";
                }

                lock (Sync)
                {
                    File.AppendAllText(LogFilePath, line + Environment.NewLine);
                }
            }
            catch
            {
                // Logging must never throw into Revit API flow.
            }
        }
    }
}