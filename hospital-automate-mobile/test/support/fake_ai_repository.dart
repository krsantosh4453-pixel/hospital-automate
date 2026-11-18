import 'package:hms_mobile/features/ai/data/ai_models.dart';
import 'package:hms_mobile/features/ai/data/ai_repository.dart';
import 'package:hms_mobile/features/ai/data/scribe_recorder.dart';

/// Server-shaped capabilities: scribe engines configured, CNN blocked.
const testCapabilities = AiCapabilities(
  speechToText: AiEngine(
    available: true,
    provider: 'whisper_api',
    model: 'whisper-1',
  ),
  drafting: AiEngine(available: true, provider: 'openai', model: 'gpt-4o-mini'),
  languages: ['auto', 'en', 'hi', 'hinglish'],
  imagePredictionAvailable: false,
  imagePredictionStatus: 'blocked',
  imagePredictionReason: 'No validated imaging model.',
);

/// A generated draft with some sections missing. Synthetic text only.
const testDraft = ScribeDraft(
  id: 21,
  version: 1,
  status: DraftStatus.underReview,
  provider: 'openai',
  model: 'gpt-4o-mini',
  extraction: {
    'chief_complaint': ['Fever for three days'],
    'symptoms': ['Fever', 'Dry cough'],
    'allergies': <String>[],
    'vitals': {'temperature': '38.2 C'},
    'assessment': ['Likely viral fever?'],
    'plan': ['Fluids and rest'],
  },
  summary: 'Fever for three days with dry cough.',
);

/// In-memory [AiRepository] that follows the server's scribe workflow and
/// records every call. Set [error] to make the next write fail.
class FakeAiRepository implements AiRepository {
  FakeAiRepository({
    this.caps = testCapabilities,
    List<ScribeSession> sessions = const [],
    this.transcriptValue,
    List<ScribeDraft> drafts = const [],
  }) : sessionRows = [...sessions],
       draftRows = [...drafts];

  AiCapabilities caps;
  final List<ScribeSession> sessionRows;
  ScribeTranscript? transcriptValue;
  final List<ScribeDraft> draftRows;
  Object? error;

  /// Like the server's `async` mode: [generate] returns a draft still being
  /// written, and [drafts] shows it finished after this many reads.
  int queuedReads = 0;
  bool failQueuedGeneration = false;

  final List<String> calls = [];
  final List<ScribeAudio> uploads = [];
  final List<({DraftSection section, Object value})> edits = [];
  bool? consentSent;

  void _fail() {
    final failure = error;
    if (failure != null) {
      error = null;
      throw failure;
    }
  }

  ScribeSession _update(int id, String status, {bool? hasAudio}) {
    final i = sessionRows.indexWhere((s) => s.id == id);
    final old = sessionRows[i];
    final updated = ScribeSession(
      id: old.id,
      status: status,
      language: old.language,
      visitId: old.visitId,
      patientName: old.patientName,
      hasAudio: hasAudio ?? old.hasAudio,
      consentRecorded: true,
    );
    sessionRows[i] = updated;
    return updated;
  }

  ScribeDraft _withStatus(ScribeDraft d, String status, {int? note}) =>
      ScribeDraft(
        id: d.id,
        version: d.version,
        status: status,
        extraction: d.extraction,
        summary: d.summary,
        provider: d.provider,
        model: d.model,
        clinicalNoteId: note ?? d.clinicalNoteId,
      );

  @override
  Future<AiCapabilities> capabilities() async => caps;

  @override
  Future<List<ScribeSession>> sessions({int? visitId}) async => [
    for (final s in sessionRows)
      if (visitId == null || s.visitId == visitId) s,
  ];

  @override
  Future<ScribeSession> createSession({
    required int visitId,
    required int hospitalId,
    required int patientId,
    required int doctorId,
    required String language,
  }) async {
    calls.add('create:$language');
    _fail();
    final session = ScribeSession(
      id: 40,
      status: ScribeSessionStatus.active,
      language: language,
      visitId: visitId,
    );
    sessionRows.add(session);
    return session;
  }

  @override
  Future<ScribeSession> startRecording(
    int sessionId, {
    required bool patientConsent,
  }) async {
    calls.add('start');
    consentSent = patientConsent;
    _fail();
    return _update(sessionId, ScribeSessionStatus.recording);
  }

  @override
  Future<ScribeSession> stopRecording(int sessionId, ScribeAudio audio) async {
    calls.add('stop');
    _fail();
    uploads.add(audio);
    return _update(sessionId, ScribeSessionStatus.completed, hasAudio: true);
  }

  @override
  Future<ScribeTranscript> transcribe(int sessionId, {String? language}) async {
    calls.add('transcribe:$language');
    _fail();
    transcriptValue = const ScribeTranscript(
      id: 31,
      status: TranscriptStatus.completed,
      text: 'Doctor: How long have you had fever? Patient: Three days.',
    );
    if (draftRows.isEmpty) {
      draftRows.add(
        const ScribeDraft(
          id: 21,
          version: 1,
          status: DraftStatus.generated,
          extraction: {},
        ),
      );
    }
    return transcriptValue!;
  }

  @override
  Future<ScribeTranscript?> transcript(int sessionId) async => transcriptValue;

  @override
  Future<List<ScribeDraft>> drafts(int sessionId) async {
    if (draftRows.isNotEmpty && draftRows.first.generating) {
      if (queuedReads > 0) {
        queuedReads--;
      } else {
        draftRows[0] = failQueuedGeneration
            ? const ScribeDraft(
                id: 21,
                version: 1,
                status: DraftStatus.generated,
                extraction: {},
                lastAttemptFailed: true,
              )
            : testDraft;
      }
    }
    return [...draftRows];
  }

  @override
  Future<ScribeDraft> generate(int draftId) async {
    calls.add('generate');
    _fail();
    if (queuedReads > 0 || failQueuedGeneration) {
      draftRows[0] = ScribeDraft(
        id: 21,
        version: 1,
        status: DraftStatus.underReview,
        extraction: const {},
        generationStartedAt: DateTime(2026, 11, 18, 10),
      );
      return draftRows.first;
    }
    draftRows[0] = testDraft;
    return testDraft;
  }

  @override
  Future<ScribeDraft> regenerate(int draftId) async {
    calls.add('regenerate');
    _fail();
    return draftRows.first;
  }

  @override
  Future<void> editSection(
    int draftId, {
    required DraftSection section,
    required Object aiValue,
    required Object doctorValue,
  }) async {
    calls.add('edit:${section.key}');
    _fail();
    edits.add((section: section, value: doctorValue));
    final d = draftRows.first;
    draftRows[0] = ScribeDraft(
      id: d.id,
      version: d.version,
      status: DraftStatus.edited,
      extraction: {...d.extraction, section.key: doctorValue},
      summary: d.summary,
      provider: d.provider,
      model: d.model,
    );
  }

  @override
  Future<int?> approve(int draftId) async {
    calls.add('approve');
    _fail();
    draftRows[0] = _withStatus(draftRows.first, DraftStatus.approved, note: 77);
    return 77;
  }

  @override
  Future<ScribeDraft> reject(int draftId, {String notes = ''}) async {
    calls.add('reject');
    _fail();
    draftRows[0] = _withStatus(draftRows.first, DraftStatus.rejected);
    return draftRows.first;
  }
}

/// A microphone that "records" [length] of audio without hardware.
class FakeScribeRecorder implements ScribeRecorder {
  FakeScribeRecorder({
    this.permission = true,
    this.length = const Duration(seconds: 42),
  });

  bool permission;
  Duration length;
  bool recording = false;
  bool disposed = false;

  @override
  Future<bool> requestPermission() async => permission;

  @override
  Future<void> start() async => recording = true;

  @override
  Future<ScribeAudio?> stop() async {
    recording = false;
    return ScribeAudio(path: '/tmp/test-consultation.m4a', duration: length);
  }

  @override
  Future<void> cancel() async => recording = false;

  /// Paths passed to [discard], in order.
  final List<String> discarded = [];

  @override
  Future<void> discard(ScribeAudio audio) async => discarded.add(audio.path);

  @override
  Future<void> dispose() async => disposed = true;
}
