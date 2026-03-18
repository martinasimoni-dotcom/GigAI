using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Speech.Recognition;

namespace GigAi.RevitAddin
{
    internal class VoiceDictationService : IDisposable
    {
        private static readonly string[] CommandVerbs =
        {
            "focus on",
            "go to",
            "select",
            "review",
            "check",
            "mark",
            "show",
            "find",
        };
        private static readonly string[] CommandQualifiers =
        {
            "the",
            "room",
            "space",
            "area",
            "unit",
            "studio unit",
        };
        private static readonly HashSet<string> HintNoiseWords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "the",
            "a",
            "an",
            "please",
            "on",
            "to",
            "go",
            "focus",
            "mark",
            "select",
            "review",
            "check",
            "show",
            "find",
            "room",
            "space",
            "area",
        };
        private static readonly Dictionary<string, string> SpokenDigitMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["zero"] = "0",
            ["oh"] = "0",
            ["o"] = "0",
            ["one"] = "1",
            ["won"] = "1",
            ["two"] = "2",
            ["too"] = "2",
            ["to"] = "2",
            ["three"] = "3",
            ["four"] = "4",
            ["for"] = "4",
            ["fore"] = "4",
            ["five"] = "5",
            ["six"] = "6",
            ["seven"] = "7",
            ["eight"] = "8",
            ["ate"] = "8",
            ["nine"] = "9",
        };
        private static readonly Dictionary<string, string> TokenRewrites = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["stdo"] = "studio",
            ["studo"] = "studio",
            ["unet"] = "unit",
            ["unti"] = "unit",
            ["loby"] = "lobby",
            ["elevater"] = "elevator",
            ["coridor"] = "corridor",
            ["tolet"] = "toilet",
            ["toliet"] = "toilet",
        };
        private SpeechRecognitionEngine? _engine;
        private DictationGrammar? _dictationGrammar;
        private Grammar? _hintGrammar;
        private Grammar? _commandGrammar;
        private bool _commandOnlyMode;
        private string _lastHeardText = string.Empty;
        private string _lastHypothesisText = string.Empty;
        private string _recognizerCulture = string.Empty;
        private string? _preferredCulture;
        private string[] _hintPhrases = Array.Empty<string>();
        private readonly AutoResetEvent _recognizeCompleted = new AutoResetEvent(true);
        public event Action<string>? TextRecognized;

        public bool IsAvailable => _engine != null;
        public bool IsListening { get; private set; }
        public string AvailabilityMessage { get; private set; } = "Ready";
        public string LastHeardText => _lastHeardText;
        public string RecognizerCulture => _recognizerCulture;

        public VoiceDictationService(string? preferredCulture = null)
        {
            _preferredCulture = preferredCulture;
            InitializeEngine();
        }

        public void SetPreferredCulture(string? culture)
        {
            if (string.Equals(culture, _preferredCulture, StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            _preferredCulture = culture;
            RestartEngine();
        }

        private void RestartEngine()
        {
            try
            {
                DisposeEngine();
                InitializeEngine();
            }
            catch
            {
                // Ignore -- availability message will be set by InitializeEngine.
            }
        }

        private void DisposeEngine()
        {
            try
            {
                Stop();
            }
            catch
            {
                // ignore
            }

            _engine?.Dispose();
            _engine = null;
        }

        public void Start()
        {
            if (_engine == null)
            {
                throw new InvalidOperationException(AvailabilityMessage);
            }

            if (IsListening)
            {
                return;
            }

            try
            {
                _lastHeardText = string.Empty;
                _lastHypothesisText = string.Empty;
                _recognizeCompleted.Reset();
                _engine.SetInputToDefaultAudioDevice();
                _engine.RecognizeAsync(RecognizeMode.Multiple);
                IsListening = true;
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException(
                    "Could not start microphone dictation. Check microphone permissions and default input device.",
                    ex
                );
            }
        }

        public void Stop()
        {
            if (_engine == null || !IsListening)
            {
                return;
            }

            try
            {
                _engine.RecognizeAsyncStop();
            }
            catch
            {
                _engine.RecognizeAsyncCancel();
                IsListening = false;
                _recognizeCompleted.Set();
            }
        }

        public void StopAndWaitForFinalResult(int timeoutMs = 2500)
        {
            if (_engine == null || !IsListening)
            {
                return;
            }

            Stop();
            bool completed = _recognizeCompleted.WaitOne(Math.Max(250, timeoutMs));
            if (!completed)
            {
                try
                {
                    _engine.RecognizeAsyncCancel();
                }
                catch
                {
                    // Ignore best-effort cancellation errors.
                }
            }

            if (string.IsNullOrWhiteSpace(_lastHeardText) && !string.IsNullOrWhiteSpace(_lastHypothesisText))
            {
                _lastHeardText = _lastHypothesisText;
            }

            IsListening = false;
        }

        public void ConfigurePhraseHints(string[] hints)
        {
            if (_engine == null)
            {
                return;
            }

            if (_hintGrammar != null)
            {
                _engine.UnloadGrammar(_hintGrammar);
                _hintGrammar = null;
            }
            if (_commandGrammar != null)
            {
                _engine.UnloadGrammar(_commandGrammar);
                _commandGrammar = null;
            }

            string[] cleaned = hints
                .Where(h => !string.IsNullOrWhiteSpace(h))
                .Select(h => h.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Take(250)
                .ToArray();
            _hintPhrases = BuildCanonicalHintPhrases(cleaned);
            _commandOnlyMode = _hintPhrases.Length > 0;
            EnsureDictationGrammarLoaded();

            if (_hintPhrases.Length == 0)
            {
                return;
            }

            Choices choices = new Choices(_hintPhrases);
            GrammarBuilder builder = new GrammarBuilder();
            builder.Append(choices);
            _hintGrammar = new Grammar(builder)
            {
                Name = "GigAI.ArchitectureHints",
                Priority = 90,
                Weight = 0.9f,
            };
            _engine.LoadGrammar(_hintGrammar);

            Choices commandChoices = BuildCommandChoices(choices);
            GrammarBuilder commandBuilder = new GrammarBuilder();
            commandBuilder.Append(commandChoices);
            _commandGrammar = new Grammar(commandBuilder)
            {
                Name = "GigAI.CommandHints",
                Priority = 110,
                Weight = 1.0f,
            };
            _engine.LoadGrammar(_commandGrammar);
        }

        private void InitializeEngine()
        {
            try
            {
                RecognizerInfo recognizer = GetRecognizer(_preferredCulture);
                _engine = new SpeechRecognitionEngine(recognizer);
                _recognizerCulture = recognizer.Culture.Name;
                _engine.BabbleTimeout = TimeSpan.FromSeconds(2);
                _engine.InitialSilenceTimeout = TimeSpan.FromSeconds(12);
                _engine.EndSilenceTimeout = TimeSpan.FromMilliseconds(800);
                _engine.EndSilenceTimeoutAmbiguous = TimeSpan.FromMilliseconds(1200);
                _engine.MaxAlternates = 5;
                _dictationGrammar = new DictationGrammar
                {
                    Name = "GigAI.DictationFallback",
                };
                EnsureDictationGrammarLoaded();
                _engine.SpeechRecognized += OnSpeechRecognized;
                _engine.SpeechHypothesized += OnSpeechHypothesized;
                _engine.RecognizeCompleted += (_, _) =>
                {
                    IsListening = false;
                    _recognizeCompleted.Set();
                };
            }
            catch (Exception ex)
            {
                _engine = null;
                AvailabilityMessage =
                    "Speech recognition engine is unavailable. Install Windows speech pack (en-US recommended). " +
                    $"Details: {ex.Message}";
            }
        }

        private static RecognizerInfo GetRecognizer(string? preferredCulture)
        {
            if (string.IsNullOrWhiteSpace(preferredCulture))
            {
                preferredCulture = Environment.GetEnvironmentVariable("GIGAI_SPEECH_CULTURE");
            }

            if (string.IsNullOrWhiteSpace(preferredCulture))
            {
                preferredCulture = "en-US";
            }

            RecognizerInfo? chosen = SpeechRecognitionEngine.InstalledRecognizers()
                .FirstOrDefault(info => info.Culture.Name.Equals(preferredCulture, StringComparison.OrdinalIgnoreCase));

            if (chosen != null)
            {
                return chosen;
            }

            chosen = SpeechRecognitionEngine.InstalledRecognizers()
                .FirstOrDefault(info => info.Culture.Name.Equals(CultureInfo.CurrentUICulture.Name, StringComparison.OrdinalIgnoreCase));

            if (chosen != null)
            {
                return chosen;
            }

            chosen = SpeechRecognitionEngine.InstalledRecognizers()
                .FirstOrDefault(info => info.Culture.Name.StartsWith("en", StringComparison.OrdinalIgnoreCase));

            if (chosen != null)
            {
                return chosen;
            }

            throw new InvalidOperationException("No compatible speech recognizer is installed.");
        }

        private void OnSpeechRecognized(object? sender, SpeechRecognizedEventArgs e)
        {
            RecognitionResult? result = e.Result;
            if (result == null || string.IsNullOrWhiteSpace(result.Text))
            {
                return;
            }

            string text = ResolvePreferredText(result);
            if (string.IsNullOrWhiteSpace(text))
            {
                return;
            }

            _lastHeardText = text;
            TextRecognized?.Invoke(text);
        }

        private void OnSpeechHypothesized(object? sender, SpeechHypothesizedEventArgs e)
        {
            RecognitionResult? result = e.Result;
            if (result == null || string.IsNullOrWhiteSpace(result.Text))
            {
                return;
            }

            string text = CanonicalizeRecognizedText(result.Text);
            if (_commandOnlyMode && !IsLikelyUsefulTranscript(text))
            {
                return;
            }

            if (text.Length >= 3 && (ContainsRoomToken(text) || LooksLikeHintDrivenCommand(text)))
            {
                _lastHypothesisText = text;
                _lastHeardText = text;
            }
        }

        private string ResolvePreferredText(RecognitionResult result)
        {
            List<(string Text, float Confidence)> candidates = new List<(string Text, float Confidence)>
            {
                (result.Text?.Trim() ?? string.Empty, result.Confidence),
            };

            foreach (RecognizedPhrase alternate in result.Alternates)
            {
                string text = alternate.Text?.Trim() ?? string.Empty;
                if (!string.IsNullOrWhiteSpace(text))
                {
                    candidates.Add((text, alternate.Confidence));
                }
            }

            string bestText = string.Empty;
            double bestScore = double.MinValue;
            bool preferCommands = IsCommandGrammar(result.Grammar);

            foreach ((string text, float confidence) in candidates)
            {
                string canonicalText = CanonicalizeRecognizedText(text);
                double score = ScoreCandidate(canonicalText, confidence, preferCommands);
                if (score > bestScore)
                {
                    bestScore = score;
                    bestText = canonicalText;
                }
            }

            double threshold = IsLikelyUsefulTranscript(bestText) ? 0.60 : 0.86;
            return bestScore >= threshold ? bestText : string.Empty;
        }

        private double ScoreCandidate(string text, float confidence, bool preferCommands)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return double.MinValue;
            }

            double score = confidence;
            double hintSimilarity = GetBestHintSimilarity(text);
            if (ContainsRoomToken(text))
            {
                score += 0.45;
            }
            if (MatchesHintPhrase(text))
            {
                score += 0.45;
            }
            if (LooksLikeHintDrivenCommand(text))
            {
                score += 0.22;
            }
            if (HasCommandCue(text))
            {
                score += 0.18;
            }
            if (preferCommands)
            {
                score += 0.25;
            }
            else if (_commandOnlyMode)
            {
                if (IsStrongFallbackText(text))
                {
                    score += 0.10;
                }
                else
                {
                    score -= 0.95;
                }
            }
            score += hintSimilarity * 0.45;

            if (text.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Length <= 1 && !ContainsRoomToken(text))
            {
                score -= 0.15;
            }
            if (!IsLikelyUsefulTranscript(text))
            {
                score -= 0.45;
            }

            return score;
        }

        private static bool IsCommandGrammar(Grammar? grammar)
        {
            if (grammar == null || string.IsNullOrWhiteSpace(grammar.Name))
            {
                return false;
            }

            return grammar.Name.Equals("GigAI.CommandHints", StringComparison.OrdinalIgnoreCase) ||
                grammar.Name.Equals("GigAI.ArchitectureHints", StringComparison.OrdinalIgnoreCase);
        }

        private bool MatchesHintPhrase(string text)
        {
            string normalizedText = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalizedText))
            {
                return false;
            }

            return GetBestHintSimilarity(normalizedText) >= 0.92;
        }

        private bool LooksLikeHintDrivenCommand(string text)
        {
            string normalizedText = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalizedText))
            {
                return false;
            }

            string[] tokens = normalizedText.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            HashSet<string> tokenSet = new HashSet<string>(tokens, StringComparer.OrdinalIgnoreCase);
            string[] usefulHintTokens = _hintPhrases
                .SelectMany(hint => NormalizeText(hint).Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
                .Where(token => token.Length >= 3 && !HintNoiseWords.Contains(token))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();

            int overlaps = usefulHintTokens.Count(token => tokenSet.Contains(token));
            return overlaps >= 2 || (overlaps >= 1 && ContainsRoomToken(normalizedText));
        }

        private static bool ContainsRoomToken(string text)
        {
            return System.Text.RegularExpressions.Regex.IsMatch(
                NormalizeText(text),
                @"\b[a-z]?\d{2,4}[a-z]?\b",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase
            );
        }

        private bool HasCommandCue(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                return false;
            }

            if (normalized.StartsWith("please ", StringComparison.OrdinalIgnoreCase))
            {
                normalized = normalized.Substring("please ".Length).Trim();
            }

            return CommandVerbs.Any(verb =>
                normalized.Equals(verb, StringComparison.OrdinalIgnoreCase) ||
                normalized.StartsWith(verb + " ", StringComparison.OrdinalIgnoreCase));
        }

        private bool IsLikelyUsefulTranscript(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                return false;
            }

            return ContainsRoomToken(normalized) ||
                HasCommandCue(normalized) ||
                LooksLikeHintDrivenCommand(normalized) ||
                GetBestHintSimilarity(normalized) >= 0.65;
        }

        private bool IsStrongFallbackText(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                return false;
            }

            return HasCommandCue(normalized) ||
                GetBestHintSimilarity(normalized) >= 0.82 ||
                (ContainsRoomToken(normalized) && LooksLikeHintDrivenCommand(normalized));
        }

        private double GetBestHintSimilarity(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized) || _hintPhrases.Length == 0)
            {
                return 0;
            }

            double best = 0;
            foreach (string hint in _hintPhrases)
            {
                string normalizedHint = NormalizeText(hint);
                if (string.IsNullOrWhiteSpace(normalizedHint))
                {
                    continue;
                }

                double score = ComputeHintSimilarity(normalized, normalizedHint);
                if (score > best)
                {
                    best = score;
                }
            }

            return best;
        }

        private string CanonicalizeRecognizedText(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                return string.Empty;
            }

            string? commandVerb = ExtractCommandVerb(normalized);
            string bestHint = FindBestHintPhrase(normalized);
            if (!string.IsNullOrWhiteSpace(bestHint))
            {
                string target = StripLeadingCommand(bestHint);
                if (!string.IsNullOrWhiteSpace(commandVerb))
                {
                    return CollapseWhitespace(commandVerb + " " + target);
                }

                return CollapseWhitespace(bestHint);
            }

            return normalized;
        }

        private string FindBestHintPhrase(string text)
        {
            string normalized = NormalizeText(text);
            if (string.IsNullOrWhiteSpace(normalized) || _hintPhrases.Length == 0)
            {
                return string.Empty;
            }

            string bestHint = string.Empty;
            double bestScore = 0;
            foreach (string hint in _hintPhrases)
            {
                string normalizedHint = NormalizeText(hint);
                if (string.IsNullOrWhiteSpace(normalizedHint))
                {
                    continue;
                }

                double score = ComputeHintSimilarity(normalized, normalizedHint);
                if (score > bestScore)
                {
                    bestScore = score;
                    bestHint = hint;
                }
            }

            return bestScore >= 0.76 ? bestHint : string.Empty;
        }

        private static double ComputeHintSimilarity(string normalizedText, string normalizedHint)
        {
            if (string.IsNullOrWhiteSpace(normalizedText) || string.IsNullOrWhiteSpace(normalizedHint))
            {
                return 0;
            }

            HashSet<string> textTokens = new HashSet<string>(
                normalizedText.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries),
                StringComparer.OrdinalIgnoreCase);
            HashSet<string> hintTokens = new HashSet<string>(
                normalizedHint.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries),
                StringComparer.OrdinalIgnoreCase);
            HashSet<string> textRoots = ExtractRoomRoots(normalizedText);
            HashSet<string> hintRoots = ExtractRoomRoots(normalizedHint);

            double rootScore = textRoots.Count > 0 || hintRoots.Count > 0
                ? JaccardSimilarity(textRoots, hintRoots)
                : 0;
            double tokenScore = JaccardSimilarity(textTokens, hintTokens);
            double containsScore = normalizedText.IndexOf(normalizedHint, StringComparison.OrdinalIgnoreCase) >= 0 ||
                normalizedHint.IndexOf(normalizedText, StringComparison.OrdinalIgnoreCase) >= 0
                ? 1.0
                : 0.0;

            return (rootScore * 0.60) + (tokenScore * 0.30) + (containsScore * 0.10);
        }

        private static double JaccardSimilarity(HashSet<string> left, HashSet<string> right)
        {
            if (left.Count == 0 && right.Count == 0)
            {
                return 0;
            }

            int intersection = left.Intersect(right, StringComparer.OrdinalIgnoreCase).Count();
            int union = left.Union(right, StringComparer.OrdinalIgnoreCase).Count();
            return union == 0 ? 0 : (double)intersection / union;
        }

        private static HashSet<string> ExtractRoomRoots(string text)
        {
            HashSet<string> roots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (System.Text.RegularExpressions.Match match in System.Text.RegularExpressions.Regex.Matches(
                NormalizeText(text),
                @"\b[a-z]?\d{2,4}[a-z]?\b",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase))
            {
                string digits = new string(match.Value.Where(char.IsDigit).ToArray());
                if (digits.Length >= 2)
                {
                    roots.Add(digits);
                }
            }

            return roots;
        }

        private static string[] BuildCanonicalHintPhrases(IEnumerable<string> hints)
        {
            HashSet<string> phrases = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string hint in hints)
            {
                string trimmed = CollapseWhitespace(hint);
                if (string.IsNullOrWhiteSpace(trimmed))
                {
                    continue;
                }

                phrases.Add(trimmed);
                phrases.Add(StripLeadingCommand(trimmed));
            }

            return phrases
                .Where(phrase => !string.IsNullOrWhiteSpace(phrase))
                .Take(250)
                .ToArray();
        }

        private static string StripLeadingCommand(string text)
        {
            string trimmed = CollapseWhitespace(text);
            if (trimmed.StartsWith("please ", StringComparison.OrdinalIgnoreCase))
            {
                trimmed = trimmed.Substring("please ".Length).Trim();
            }

            foreach (string verb in CommandVerbs)
            {
                if (trimmed.StartsWith(verb + " ", StringComparison.OrdinalIgnoreCase))
                {
                    return trimmed.Substring(verb.Length).Trim();
                }
            }

            return trimmed;
        }

        private static string? ExtractCommandVerb(string text)
        {
            string normalized = NormalizeText(text);
            if (normalized.StartsWith("please ", StringComparison.OrdinalIgnoreCase))
            {
                normalized = normalized.Substring("please ".Length).Trim();
            }

            foreach (string verb in CommandVerbs)
            {
                if (normalized.Equals(verb, StringComparison.OrdinalIgnoreCase) ||
                    normalized.StartsWith(verb + " ", StringComparison.OrdinalIgnoreCase))
                {
                    return verb;
                }
            }

            return null;
        }

        private static Choices BuildCommandChoices(Choices targetChoices)
        {
            List<GrammarBuilder> patterns = new List<GrammarBuilder>
            {
                BuildCommandPattern(null, null, targetChoices),
                BuildCommandPattern("please", null, targetChoices),
            };

            foreach (string qualifier in CommandQualifiers)
            {
                patterns.Add(BuildCommandPattern(null, qualifier, targetChoices));
                patterns.Add(BuildCommandPattern("please", qualifier, targetChoices));
            }

            return new Choices(patterns.ToArray());
        }

        private static GrammarBuilder BuildCommandPattern(string? politeLead, string? qualifier, Choices targetChoices)
        {
            GrammarBuilder builder = new GrammarBuilder();
            if (!string.IsNullOrWhiteSpace(politeLead))
            {
                builder.Append(politeLead);
            }

            builder.Append(new Choices(CommandVerbs));
            if (!string.IsNullOrWhiteSpace(qualifier))
            {
                builder.Append(qualifier);
            }

            builder.Append(targetChoices);
            return builder;
        }

        private static string NormalizeText(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return string.Empty;
            }

            char[] chars = text
                .ToLowerInvariant()
                .Select(ch => char.IsLetterOrDigit(ch) || char.IsWhiteSpace(ch) ? ch : ' ')
                .ToArray();
            string[] tokens = new string(chars)
                .Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(token => TokenRewrites.TryGetValue(token, out string replacement) ? replacement : token)
                .ToArray();
            return string.Join(" ", CollapseSpokenDigits(tokens));
        }

        private static IEnumerable<string> CollapseSpokenDigits(IEnumerable<string> tokens)
        {
            List<string> collapsed = new List<string>();
            List<string> digits = new List<string>();

            void FlushDigits()
            {
                if (digits.Count == 0)
                {
                    return;
                }

                collapsed.Add(digits.Count >= 2 ? string.Concat(digits) : digits[0]);
                digits.Clear();
            }

            foreach (string token in tokens)
            {
                if (SpokenDigitMap.TryGetValue(token, out string digit))
                {
                    digits.Add(digit);
                    continue;
                }

                FlushDigits();
                collapsed.Add(token);
            }

            FlushDigits();
            return collapsed;
        }

        private static string CollapseWhitespace(string text)
        {
            return System.Text.RegularExpressions.Regex.Replace(text ?? string.Empty, @"\s+", " ").Trim();
        }

        private void EnsureDictationGrammarLoaded()
        {
            if (_engine == null || _dictationGrammar == null)
            {
                return;
            }

            try
            {
                if (!_engine.Grammars.Any(grammar =>
                    grammar.Name.Equals(_dictationGrammar.Name, StringComparison.OrdinalIgnoreCase)))
                {
                    _engine.LoadGrammar(_dictationGrammar);
                }
            }
            catch
            {
                // Best effort only.
            }
        }

        private void UnloadDictationGrammar()
        {
            if (_engine == null || _dictationGrammar == null)
            {
                return;
            }

            try
            {
                _engine.UnloadGrammar(_dictationGrammar);
            }
            catch
            {
                // Grammar may already be unloaded.
            }
        }

        public void Dispose()
        {
            try
            {
                Stop();
            }
            catch
            {
                // Ignore cleanup failures.
            }

            _engine?.Dispose();
            _engine = null;
            _recognizeCompleted.Dispose();
        }
    }
}
