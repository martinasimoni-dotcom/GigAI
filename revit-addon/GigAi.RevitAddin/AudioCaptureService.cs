using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace GigAi.RevitAddin
{
    internal sealed class AudioCaptureService : IDisposable
    {
        private readonly string _alias = "gigaiwave_" + Guid.NewGuid().ToString("N");
        private string? _tempFilePath;

        public bool IsRecording { get; private set; }
        public bool IsAvailable => true;
        public string AvailabilityMessage { get; private set; } = "Ready";

        public void Start()
        {
            if (IsRecording)
            {
                return;
            }

            _tempFilePath = Path.Combine(Path.GetTempPath(), _alias + ".wav");
            DeleteTempFile();

            try
            {
                Execute($"open new type waveaudio alias {_alias}");
                Execute($"record {_alias}");
                IsRecording = true;
                AvailabilityMessage = "Recording";
            }
            catch (Exception ex)
            {
                TryClose();
                AvailabilityMessage = ex.Message;
                throw new InvalidOperationException(
                    "Could not start microphone recording. Check microphone permissions and default input device.",
                    ex
                );
            }
        }

        public byte[] StopAndReadWav()
        {
            if (!IsRecording)
            {
                return Array.Empty<byte>();
            }

            try
            {
                Execute($"stop {_alias}");
                if (string.IsNullOrWhiteSpace(_tempFilePath))
                {
                    throw new InvalidOperationException("Recording file path was not initialized.");
                }

                Execute($"save {_alias} \"{_tempFilePath}\"");
                if (!File.Exists(_tempFilePath))
                {
                    throw new InvalidOperationException("Microphone recording did not produce a WAV file.");
                }

                return File.ReadAllBytes(_tempFilePath);
            }
            finally
            {
                IsRecording = false;
                TryClose();
                DeleteTempFile();
            }
        }

        private void Execute(string command)
        {
            int errorCode = mciSendString(command, null, 0, IntPtr.Zero);
            if (errorCode == 0)
            {
                return;
            }

            StringBuilder message = new StringBuilder(256);
            if (!mciGetErrorString(errorCode, message, message.Capacity))
            {
                message.Append("Unknown multimedia device error.");
            }

            throw new InvalidOperationException(message.ToString().Trim());
        }

        private void TryClose()
        {
            try
            {
                mciSendString($"close {_alias}", null, 0, IntPtr.Zero);
            }
            catch
            {
                // Best effort cleanup.
            }
        }

        private void DeleteTempFile()
        {
            if (string.IsNullOrWhiteSpace(_tempFilePath))
            {
                return;
            }

            try
            {
                if (File.Exists(_tempFilePath))
                {
                    File.Delete(_tempFilePath);
                }
            }
            catch
            {
                // Best effort cleanup.
            }
        }

        public void Dispose()
        {
            if (IsRecording)
            {
                try
                {
                    StopAndReadWav();
                }
                catch
                {
                    TryClose();
                    DeleteTempFile();
                }
            }
            else
            {
                TryClose();
                DeleteTempFile();
            }
        }

        [DllImport("winmm.dll", CharSet = CharSet.Auto)]
        private static extern int mciSendString(
            string command,
            StringBuilder? returnValue,
            int returnLength,
            IntPtr winHandle
        );

        [DllImport("winmm.dll", CharSet = CharSet.Auto)]
        private static extern bool mciGetErrorString(
            int errorCode,
            StringBuilder errorText,
            int errorTextSize
        );
    }
}
