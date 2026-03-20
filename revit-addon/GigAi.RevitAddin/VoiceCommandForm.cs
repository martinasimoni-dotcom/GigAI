using System;
using System.Linq;
using System.Windows.Forms;

namespace GigAi.RevitAddin
{
    internal sealed class LanguageDisplayOption
    {
        public string Code { get; set; } = "en";
        public string Display { get; set; } = string.Empty;

        public override string ToString()
        {
            return string.IsNullOrWhiteSpace(Display) ? Code : Display;
        }
    }

    public class VoiceCommandForm : Form
    {
        private readonly TextBox _apiUrlTextBox;
        private readonly TextBox _projectIdTextBox;
        private readonly TextBox _transcriptTextBox;
        private readonly Label _micStatusLabel;
        private readonly ComboBox _languageComboBox;
        private readonly Button _startMicButton;
        private readonly Button _stopMicButton;
        private readonly Button _testApiButton;
        private readonly AudioCaptureService _audioCaptureService;
        private readonly string[] _speechHints;
        private string _capturedAudioBase64 = string.Empty;

        public string ApiUrl => _apiUrlTextBox.Text.Trim();
        public string ProjectId => _projectIdTextBox.Text.Trim();
        public string Transcript => _transcriptTextBox.Text.Trim();
        public string CapturedAudioBase64 => _capturedAudioBase64;
        public bool HasCapturedAudio => !string.IsNullOrWhiteSpace(_capturedAudioBase64);
        public string LanguageCode => (_languageComboBox.SelectedValue as string ?? "en").Trim();

        public VoiceCommandForm(
            string defaultApiUrl,
            string defaultProjectId,
            string defaultTranscript,
            string[] speechHints
        )
        {
            SuspendLayout();

            Text = "GigAI Voice Command";
            AutoScaleMode = AutoScaleMode.Dpi;
            ClientSize = new System.Drawing.Size(920, 620);
            MinimumSize = new System.Drawing.Size(860, 580);
            FormBorderStyle = FormBorderStyle.Sizable;
            MaximizeBox = true;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            Font = new System.Drawing.Font("Segoe UI", 10F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point);

            const int leftMargin = 18;
            const int topMargin = 16;
            const int labelWidth = 120;
            const int controlHeight = 32;
            const int buttonHeight = 36;
            const int controlLeft = leftMargin + labelWidth;
            const int rightMargin = 16;
            int inputWidth = ClientSize.Width - controlLeft - rightMargin;
            int apiTop = topMargin;
            int projectTop = apiTop + controlHeight + 14;
            int transcriptTop = projectTop + controlHeight + 38;
            int bottomSectionHeight = 130;

            Label apiLabel = new Label
            {
                Text = "API URL:",
                Left = leftMargin,
                Top = apiTop + 6,
                Width = labelWidth,
                AutoSize = true
            };

            _apiUrlTextBox = new TextBox
            {
                Left = controlLeft,
                Top = apiTop,
                Width = inputWidth,
                Height = controlHeight,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Text = defaultApiUrl
            };

            Label projectLabel = new Label
            {
                Text = "Project ID:",
                Left = leftMargin,
                Top = projectTop + 6,
                Width = labelWidth,
                AutoSize = true
            };

            _projectIdTextBox = new TextBox
            {
                Left = controlLeft,
                Top = projectTop,
                Width = inputWidth,
                Height = controlHeight,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Text = defaultProjectId
            };

            Label transcriptLabel = new Label
            {
                Text = "Transcript:",
                Left = leftMargin,
                Top = transcriptTop,
                Width = labelWidth,
                AutoSize = true
            };

            int transcriptBodyTop = transcriptTop + 26;
            int transcriptHeight = ClientSize.Height - transcriptBodyTop - bottomSectionHeight;

            _transcriptTextBox = new TextBox
            {
                Left = controlLeft,
                Top = transcriptBodyTop,
                Width = inputWidth,
                Height = transcriptHeight,
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right,
                Multiline = true,
                ScrollBars = ScrollBars.Vertical,
                Text = defaultTranscript
            };

            int commandRowTop = transcriptBodyTop + transcriptHeight + 12;

            _startMicButton = new Button
            {
                Text = "Start Mic",
                Left = controlLeft,
                Top = commandRowTop,
                Width = 116,
                Height = buttonHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            };
            _startMicButton.Click += OnStartMicClicked;

            _stopMicButton = new Button
            {
                Text = "Stop Mic",
                Left = controlLeft + 124,
                Top = commandRowTop,
                Width = 116,
                Height = buttonHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left,
                Enabled = false
            };
            _stopMicButton.Click += OnStopMicClicked;

            _testApiButton = new Button
            {
                Text = "Test API",
                Left = controlLeft + 248,
                Top = commandRowTop,
                Width = 116,
                Height = buttonHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            };
            _testApiButton.Click += OnTestApiClicked;

            int settingsRowTop = commandRowTop + buttonHeight + 10;

            Label languageLabel = new Label
            {
                Text = "Audio language:",
                Left = leftMargin,
                Top = settingsRowTop + 6,
                Width = labelWidth,
                AutoSize = true
            };

            _languageComboBox = new ComboBox
            {
                Left = controlLeft,
                Top = settingsRowTop,
                Width = 300,
                Height = controlHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left,
                DropDownStyle = ComboBoxStyle.DropDownList
            };
            _languageComboBox.SelectedIndexChanged += OnLanguageChanged;

            _micStatusLabel = new Label
            {
                Left = controlLeft + 316,
                Top = settingsRowTop + 6,
                Width = ClientSize.Width - (controlLeft + 316) - 220,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right,
                Text = "Mic: idle"
            };

            Button okButton = new Button
            {
                Text = "Send",
                Left = ClientSize.Width - 214,
                Top = settingsRowTop,
                Width = 96,
                Height = buttonHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right,
                DialogResult = DialogResult.OK
            };

            Button cancelButton = new Button
            {
                Text = "Cancel",
                Left = ClientSize.Width - 110,
                Top = settingsRowTop,
                Width = 96,
                Height = buttonHeight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right,
                DialogResult = DialogResult.Cancel
            };

            AcceptButton = okButton;
            CancelButton = cancelButton;

            Controls.Add(apiLabel);
            Controls.Add(_apiUrlTextBox);
            Controls.Add(projectLabel);
            Controls.Add(_projectIdTextBox);
            Controls.Add(transcriptLabel);
            Controls.Add(_transcriptTextBox);
            Controls.Add(_startMicButton);
            Controls.Add(_stopMicButton);
            Controls.Add(_testApiButton);
            Controls.Add(languageLabel);
            Controls.Add(_languageComboBox);
            Controls.Add(_micStatusLabel);
            Controls.Add(okButton);
            Controls.Add(cancelButton);

            _audioCaptureService = new AudioCaptureService();
            _speechHints = speechHints ?? Array.Empty<string>();

            PopulateLanguageList();

            if (!_audioCaptureService.IsAvailable)
            {
                _startMicButton.Enabled = false;
                _micStatusLabel.Text = $"Mic unavailable: {_audioCaptureService.AvailabilityMessage}";
            }
            else
            {
                int hintCount = _speechHints
                    .Where(h => !string.IsNullOrWhiteSpace(h))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Count();
                _micStatusLabel.Text = $"Mic: ready (Whisper backend, {hintCount} space hints)";
                _startMicButton.Enabled = true;
                _stopMicButton.Enabled = false;
            }

            FormClosing += OnFormClosing;
            Shown += (_, _) =>
            {
                if (_audioCaptureService.IsAvailable)
                {
                    TryStartMicAutomatically();
                }
            };

            ResumeLayout(false);
        }

        private void TryStartMicAutomatically()
        {
            try
            {
                _audioCaptureService.Start();
                _capturedAudioBase64 = string.Empty;
                _startMicButton.Enabled = false;
                _stopMicButton.Enabled = true;
                _micStatusLabel.Text = $"Mic: recording ({LanguageCode}, Whisper backend)...";
            }
            catch
            {
                _startMicButton.Enabled = _audioCaptureService.IsAvailable;
                _stopMicButton.Enabled = false;
                _micStatusLabel.Text = "Mic: ready (click Start Mic)";
            }
        }

        private void PopulateLanguageList()
        {
            var languages = new[]
            {
                new LanguageDisplayOption { Code = "en", Display = "en (English)" },
                new LanguageDisplayOption { Code = "fr", Display = "fr (French)" },
                new LanguageDisplayOption { Code = "ar", Display = "ar (Arabic)" },
            };

            _languageComboBox.DisplayMember = "Display";
            _languageComboBox.ValueMember = "Code";
            _languageComboBox.DataSource = languages;
            _languageComboBox.SelectedIndex = 0;
        }

        private void OnLanguageChanged(object? sender, EventArgs e)
        {
            if (_audioCaptureService.IsRecording)
            {
                _micStatusLabel.Text = $"Mic: recording ({LanguageCode}, Whisper backend)...";
                return;
            }

            string audioState = HasCapturedAudio ? "audio captured" : "ready";
            _micStatusLabel.Text = $"Mic: {audioState} ({LanguageCode}, Whisper backend)";
        }

        private void OnStartMicClicked(object? sender, EventArgs e)
        {
            try
            {
                _audioCaptureService.Start();
                _capturedAudioBase64 = string.Empty;
                _startMicButton.Enabled = false;
                _stopMicButton.Enabled = true;
                _micStatusLabel.Text = $"Mic: recording ({LanguageCode}, Whisper backend)...";
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    ex.Message,
                    "GigAI Microphone Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        private void OnStopMicClicked(object? sender, EventArgs e)
        {
            try
            {
                byte[] audioBytes = _audioCaptureService.StopAndReadWav();
                _capturedAudioBase64 = audioBytes.Length > 0
                    ? Convert.ToBase64String(audioBytes)
                    : string.Empty;
                _startMicButton.Enabled = _audioCaptureService.IsAvailable;
                _stopMicButton.Enabled = false;

                if (audioBytes.Length > 0)
                {
                    double sizeKb = audioBytes.Length / 1024.0;
                    _micStatusLabel.Text =
                        $"Mic: audio captured ({sizeKb:0.0} KB). Whisper will transcribe on Send.";
                }
                else
                {
                    _micStatusLabel.Text = "Mic: stopped, but no audio was captured.";
                }
            }
            catch (Exception ex)
            {
                _startMicButton.Enabled = _audioCaptureService.IsAvailable;
                _stopMicButton.Enabled = false;
                MessageBox.Show(
                    ex.Message,
                    "GigAI Microphone Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        private void OnTestApiClicked(object? sender, EventArgs e)
        {
            try
            {
                string message = GigAiApiClient.TestConnection(ApiUrl);
                MessageBox.Show(
                    message,
                    "GigAI API",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    ex.Message,
                    "GigAI API Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        private void OnFormClosing(object? sender, FormClosingEventArgs e)
        {
            if (DialogResult == DialogResult.OK && _audioCaptureService.IsRecording)
            {
                try
                {
                    byte[] audioBytes = _audioCaptureService.StopAndReadWav();
                    _capturedAudioBase64 = audioBytes.Length > 0
                        ? Convert.ToBase64String(audioBytes)
                        : _capturedAudioBase64;
                }
                catch (Exception ex)
                {
                    MessageBox.Show(
                        ex.Message,
                        "GigAI Microphone Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    e.Cancel = true;
                    return;
                }
            }

            if (DialogResult == DialogResult.OK &&
                string.IsNullOrWhiteSpace(ApiUrl))
            {
                MessageBox.Show(
                    "API URL is required.",
                    "GigAI",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                e.Cancel = true;
                return;
            }

            if (DialogResult == DialogResult.OK &&
                string.IsNullOrWhiteSpace(Transcript) &&
                !HasCapturedAudio)
            {
                string guidance = _audioCaptureService.IsAvailable
                    ? "No transcript or recorded audio was provided.\nSpeak while Mic is recording, or type a command before clicking Send."
                    : $"No transcript was captured and microphone recording is unavailable.\n{_audioCaptureService.AvailabilityMessage}";
                MessageBox.Show(
                    guidance,
                    "GigAI",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                e.Cancel = true;
                return;
            }

            _audioCaptureService.Dispose();
        }
    }
}
