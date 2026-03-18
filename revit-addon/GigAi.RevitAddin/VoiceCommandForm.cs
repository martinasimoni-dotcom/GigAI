using System;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using System.Speech.Recognition;

namespace GigAi.RevitAddin
{
    internal sealed class RecognizerDisplayOption
    {
        public string Name { get; set; } = string.Empty;
        public string Display { get; set; } = string.Empty;

        public override string ToString()
        {
            return string.IsNullOrWhiteSpace(Display) ? Name : Display;
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
        private readonly VoiceDictationService _dictationService;
        private readonly string[] _speechHints;

        public string ApiUrl => _apiUrlTextBox.Text.Trim();
        public string ProjectId => _projectIdTextBox.Text.Trim();
        public string Transcript => _transcriptTextBox.Text.Trim();

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
                Text = "Speech language:",
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

            _dictationService = new VoiceDictationService();
            _speechHints = speechHints ?? Array.Empty<string>();
            _dictationService.TextRecognized += AppendRecognizedText;
            _dictationService.ConfigurePhraseHints(_speechHints);

            PopulateLanguageList();

            if (!_dictationService.IsAvailable)
            {
                _startMicButton.Enabled = false;
                _micStatusLabel.Text = $"Mic unavailable: {_dictationService.AvailabilityMessage}";
            }
            else
            {
                int hintCount = speechHints
                    .Where(h => !string.IsNullOrWhiteSpace(h))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Count();
                string culture = string.IsNullOrWhiteSpace(_dictationService.RecognizerCulture)
                    ? "default"
                    : _dictationService.RecognizerCulture;
                _micStatusLabel.Text = $"Mic: ready ({hintCount} hints, {culture})";
                _startMicButton.Enabled = true;
                _stopMicButton.Enabled = false;
            }

            FormClosing += OnFormClosing;
            Shown += (_, _) =>
            {
                if (_dictationService.IsAvailable)
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
                _dictationService.Start();
                _startMicButton.Enabled = false;
                _stopMicButton.Enabled = true;
                _micStatusLabel.Text = "Mic: listening...";
            }
            catch
            {
                // Keep manual start available if auto-start fails.
                _startMicButton.Enabled = _dictationService.IsAvailable;
                _stopMicButton.Enabled = false;
                _micStatusLabel.Text = "Mic: ready (click Start Mic)";
            }
        }

        private void PopulateLanguageList()
        {
            try
            {
                var recognizers = SpeechRecognitionEngine.InstalledRecognizers()
                    .OrderBy(r => r.Culture.Name)
                    .Select(r => new RecognizerDisplayOption
                    {
                        Name = r.Culture.Name,
                        Display = $"{r.Culture.Name} ({r.Culture.DisplayName})",
                    })
                    .GroupBy(r => r.Name, StringComparer.OrdinalIgnoreCase)
                    .Select(g => g.First())
                    .ToList();

                _languageComboBox.DisplayMember = "Display";
                _languageComboBox.ValueMember = "Name";
                _languageComboBox.DataSource = recognizers;

                string current = _dictationService.RecognizerCulture;
                if (!string.IsNullOrWhiteSpace(current))
                {
                    int index = recognizers.FindIndex(r => string.Equals(r.Name, current, StringComparison.OrdinalIgnoreCase));
                    if (index >= 0)
                    {
                        _languageComboBox.SelectedIndex = index;
                    }
                }
            }
            catch
            {
                // Ignore: if recognizers cannot be enumerated, leave the control empty.
            }
        }

        private void OnLanguageChanged(object? sender, EventArgs e)
        {
            if (_languageComboBox.SelectedItem == null)
            {
                return;
            }

            bool wasListening = _dictationService.IsListening;
            if (wasListening)
            {
                _dictationService.StopAndWaitForFinalResult();
            }

            string selectedCulture = (string)_languageComboBox.SelectedValue;
            _dictationService.SetPreferredCulture(selectedCulture);
            _dictationService.ConfigurePhraseHints(_speechHints);

            string culture = string.IsNullOrWhiteSpace(_dictationService.RecognizerCulture)
                ? "default"
                : _dictationService.RecognizerCulture;

            if (wasListening && _dictationService.IsAvailable)
            {
                TryStartMicAutomatically();
                _micStatusLabel.Text = $"Mic: listening ({culture})...";
            }
            else
            {
                _micStatusLabel.Text = $"Mic: ready ({culture})";
            }
        }

        private void OnStartMicClicked(object? sender, EventArgs e)
        {
            try
            {
                _dictationService.Start();
                _startMicButton.Enabled = false;
                _stopMicButton.Enabled = true;
                string culture = string.IsNullOrWhiteSpace(_dictationService.RecognizerCulture)
                    ? "default"
                    : _dictationService.RecognizerCulture;
                _micStatusLabel.Text = $"Mic: listening ({culture})...";
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
            _dictationService.StopAndWaitForFinalResult();
            _startMicButton.Enabled = _dictationService.IsAvailable;
            _stopMicButton.Enabled = false;
            _micStatusLabel.Text = "Mic: stopped";

            if (string.IsNullOrWhiteSpace(Transcript) &&
                !string.IsNullOrWhiteSpace(_dictationService.LastHeardText))
            {
                _transcriptTextBox.Text = _dictationService.LastHeardText;
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

        private void AppendRecognizedText(string text)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<string>(AppendRecognizedText), text);
                return;
            }

            string currentText = _transcriptTextBox.Text.Trim();
            if (IsDuplicateRecognition(currentText, text))
            {
                return;
            }

            if (ShouldReplaceTranscript(currentText, text))
            {
                _transcriptTextBox.Text = text;
            }

            _transcriptTextBox.SelectionStart = _transcriptTextBox.TextLength;
            _transcriptTextBox.ScrollToCaret();
        }

        private void OnFormClosing(object? sender, FormClosingEventArgs e)
        {
            if (DialogResult == DialogResult.OK && _dictationService.IsListening)
            {
                // Flush pending recognition when user clicks Send while mic is active.
                _dictationService.StopAndWaitForFinalResult();
            }

            if (DialogResult == DialogResult.OK &&
                string.IsNullOrWhiteSpace(Transcript) &&
                !string.IsNullOrWhiteSpace(_dictationService.LastHeardText))
            {
                _transcriptTextBox.Text = _dictationService.LastHeardText;
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
                string.IsNullOrWhiteSpace(Transcript))
            {
                string guidance = _dictationService.IsAvailable
                    ? "No voice command was captured.\nPlease speak while Mic is listening, then click Send."
                    : $"No transcript was captured and microphone dictation is unavailable.\n{_dictationService.AvailabilityMessage}";
                MessageBox.Show(
                    guidance,
                    "GigAI",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                e.Cancel = true;
                return;
            }

            _dictationService.Dispose();
        }

        private static bool IsDuplicateRecognition(string currentText, string incomingText)
        {
            string current = NormalizeTranscript(currentText);
            string incoming = NormalizeTranscript(incomingText);
            if (string.IsNullOrWhiteSpace(current) || string.IsNullOrWhiteSpace(incoming))
            {
                return false;
            }

            return current == incoming || current.EndsWith(incoming, StringComparison.Ordinal);
        }

        private static bool ShouldReplaceTranscript(string currentText, string incomingText)
        {
            string current = NormalizeTranscript(currentText);
            string incoming = NormalizeTranscript(incomingText);
            if (string.IsNullOrWhiteSpace(incoming))
            {
                return false;
            }

            if (string.IsNullOrWhiteSpace(current))
            {
                return true;
            }

            if (incoming.IndexOf(current, StringComparison.Ordinal) >= 0 && incoming.Length >= current.Length)
            {
                return true;
            }

            int currentScore = ScoreTranscriptCandidate(currentText);
            int incomingScore = ScoreTranscriptCandidate(incomingText);
            if (incomingScore != currentScore)
            {
                return incomingScore > currentScore;
            }

            return incoming.Length > current.Length + 2;
        }

        private static int ScoreTranscriptCandidate(string text)
        {
            string normalized = NormalizeTranscript(text);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                return int.MinValue;
            }

            int score = 0;
            if (Regex.IsMatch(normalized, @"\b[a-z]?\d{2,4}[a-z]?\b", RegexOptions.IgnoreCase))
            {
                score += 6;
            }

            if (StartsWithCommandVerb(normalized))
            {
                score += 4;
            }

            if (LooksLikeSpaceCommand(normalized))
            {
                score += 3;
            }

            if (normalized.Contains("studio") && normalized.Contains("unit"))
            {
                score += 2;
            }

            int wordCount = normalized.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Length;
            if (wordCount >= 2 && wordCount <= 6)
            {
                score += 2;
            }
            else if (wordCount > 8)
            {
                score -= 2;
            }

            if (!LooksLikeSpaceCommand(normalized) && wordCount > 4)
            {
                score -= 4;
            }

            return score;
        }

        private static bool StartsWithCommandVerb(string normalized)
        {
            string[] verbs = { "focus on", "go to", "select", "review", "check", "mark", "show", "find" };
            return verbs.Any(verb =>
                normalized.Equals(verb, StringComparison.OrdinalIgnoreCase) ||
                normalized.StartsWith(verb + " ", StringComparison.OrdinalIgnoreCase));
        }

        private static bool LooksLikeSpaceCommand(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            string normalized = NormalizeTranscript(text);
            if (Regex.IsMatch(normalized, @"\b[a-z]?\d{2,4}[a-z]?\b", RegexOptions.IgnoreCase))
            {
                return true;
            }

            string[] cueWords = { "mark", "focus", "go", "select", "review", "check", "show", "find", "studio", "unit", "room", "space", "lobby", "corridor", "elevator", "stair" };
            return cueWords.Any(word => normalized.Contains(word));
        }

        private static string NormalizeTranscript(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return string.Empty;
            }

            string lowered = text.ToLowerInvariant();
            string alnum = Regex.Replace(lowered, @"[^a-z0-9\s]+", " ");
            return Regex.Replace(alnum, @"\s+", " ").Trim();
        }
    }
}
