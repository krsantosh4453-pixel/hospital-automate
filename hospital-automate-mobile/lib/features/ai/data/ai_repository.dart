import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/paged_rows.dart';
import '../../patient/data/json_read.dart';
import 'ai_models.dart';

/// Uploading a long consultation recording can outlast the app's 15 s
/// default. Transcription and drafting are queued, so they never wait.
const aiRequestTimeout = Duration(seconds: 150);

/// A recorded consultation ready to upload.
class ScribeAudio {
  const ScribeAudio({
    required this.path,
    required this.duration,
    this.mimeType = 'audio/mp4',
  });

  final String path;
  final Duration duration;
  final String mimeType;
}

/// The AI scribe and AI status endpoints (`ai_scribe/urls.py`). The server
/// checks that the signed-in doctor is the consultation's own doctor for
/// every step and never lets AI text into the record without approval.
abstract interface class AiRepository {
  Future<AiCapabilities> capabilities();
  Future<List<ScribeSession>> sessions({int? visitId});
  Future<ScribeSession> createSession({
    required int visitId,
    required int hospitalId,
    required int patientId,
    required int doctorId,
    required String language,
  });

  /// [patientConsent] must be true: the server refuses to record without it.
  Future<ScribeSession> startRecording(
    int sessionId, {
    required bool patientConsent,
  });
  Future<ScribeSession> stopRecording(int sessionId, ScribeAudio audio);
  Future<ScribeTranscript> transcribe(int sessionId, {String? language});
  Future<ScribeTranscript?> transcript(int sessionId);
  Future<List<ScribeDraft>> drafts(int sessionId);
  Future<ScribeDraft> generate(int draftId);
  Future<ScribeDraft> regenerate(int draftId);
  Future<void> editSection(
    int draftId, {
    required DraftSection section,
    required Object aiValue,
    required Object doctorValue,
  });

  /// Writes the clinical note; returns its id.
  Future<int?> approve(int draftId);
  Future<ScribeDraft> reject(int draftId, {String notes});
}

class ApiAiRepository implements AiRepository {
  ApiAiRepository(this._api);

  final ApiClient _api;

  static const _sessions = 'ai/consultation-sessions/';
  static const _drafts = 'ai/drafts/';

  /// POST with [aiRequestTimeout] for calls that wait on a provider.
  Future<T> _slowPost<T>(
    String path,
    Object? body,
    T Function(Object? json) decode,
  ) async {
    try {
      final response = await _api.dio.post<Object?>(
        path,
        data: body,
        options: Options(
          receiveTimeout: aiRequestTimeout,
          sendTimeout: aiRequestTimeout,
        ),
      );
      return decode(response.data);
    } on DioException catch (error) {
      throw ApiException.fromDio(error);
    }
  }

  @override
  Future<AiCapabilities> capabilities() =>
      _api.get('ai/capabilities/', decode: AiCapabilities.fromJson);

  @override
  Future<List<ScribeSession>> sessions({int? visitId}) async => [
    for (final row in await getAllRows(
      _api,
      _sessions,
      query: {'visit': ?visitId},
    ))
      ScribeSession.fromJson(row),
  ];

  @override
  Future<ScribeSession> createSession({
    required int visitId,
    required int hospitalId,
    required int patientId,
    required int doctorId,
    required String language,
  }) => _api.post(
    _sessions,
    body: {
      'visit': visitId,
      'hospital': hospitalId,
      'patient': patientId,
      'doctor': doctorId,
      'language': language,
    },
    decode: (json) => ScribeSession.fromJson(asMap(json)),
  );

  @override
  Future<ScribeSession> startRecording(
    int sessionId, {
    required bool patientConsent,
  }) => _api.post(
    '$_sessions$sessionId/start_recording/',
    body: {'patient_consent': patientConsent},
    decode: (json) => ScribeSession.fromJson(asMap(json)),
  );

  @override
  Future<ScribeSession> stopRecording(int sessionId, ScribeAudio audio) async {
    final type = audio.mimeType.split('/');
    final form = FormData.fromMap({
      'audio_file': await MultipartFile.fromFile(
        audio.path,
        filename: 'consultation.m4a',
        contentType: DioMediaType(type.first, type.last),
      ),
      'duration_seconds': audio.duration.inSeconds,
      'format': type.last,
    });
    return _slowPost(
      '$_sessions$sessionId/stop_recording/',
      form,
      (json) => ScribeSession.fromJson(asMap(json)),
    );
  }

  /// Queued on the server (`async`): the transcript comes back `processing`
  /// and the screen polls [transcript] until it is done.
  @override
  Future<ScribeTranscript> transcribe(int sessionId, {String? language}) =>
      _api.post(
        '$_sessions$sessionId/transcribe/',
        body: {'async': true, 'language': ?language},
        decode: _transcriptOf,
      );

  /// `transcribe` answers with the transcript, or with
  /// `{message, transcript}` when it reuses a finished one.
  static ScribeTranscript _transcriptOf(Object? json) {
    final map = asMap(json);
    final inner = map['transcript'];
    return ScribeTranscript.fromJson(inner is Map ? asMap(inner) : map);
  }

  @override
  Future<ScribeTranscript?> transcript(int sessionId) async {
    final rows = await getAllRows(
      _api,
      'ai/transcripts/',
      query: {'consultation': sessionId},
      maxPages: 1,
    );
    return rows.isEmpty ? null : ScribeTranscript.fromJson(rows.first);
  }

  @override
  Future<List<ScribeDraft>> drafts(int sessionId) async {
    final rows = await getAllRows(
      _api,
      _drafts,
      query: {'consultation': sessionId},
    );
    // The list serializer is a summary; read each draft in full.
    final drafts = [
      for (final row in rows)
        await _api.get(
          '$_drafts${readInt(row['id'])}/',
          decode: (json) => ScribeDraft.fromJson(asMap(json)),
        ),
    ];
    drafts.sort((a, b) => b.version.compareTo(a.version));
    return List.unmodifiable(drafts);
  }

  /// Queued on the server (`async`): the draft reads [ScribeDraft.generating]
  /// until the provider has answered; the screen polls [drafts].
  @override
  Future<ScribeDraft> generate(int draftId) => _api.post(
    '$_drafts$draftId/generate/',
    body: const {'async': true},
    decode: (json) => ScribeDraft.fromJson(asMap(json)),
  );

  @override
  Future<ScribeDraft> regenerate(int draftId) => _api.post(
    '$_drafts$draftId/regenerate/',
    body: const <String, Object?>{},
    decode: (json) => ScribeDraft.fromJson(asMap(json)),
  );

  @override
  Future<void> editSection(
    int draftId, {
    required DraftSection section,
    required Object aiValue,
    required Object doctorValue,
  }) => _api.post(
    '$_drafts$draftId/review/',
    body: {
      'action': 'edited_section',
      'section': section.key,
      'ai_value': aiValue,
      'doctor_value': doctorValue,
    },
    decode: (_) {},
  );

  @override
  Future<int?> approve(int draftId) => _api.post(
    '$_drafts$draftId/approve/',
    body: const <String, Object?>{},
    decode: (json) => readInt(asMap(json)['clinical_note_id']),
  );

  @override
  Future<ScribeDraft> reject(int draftId, {String notes = ''}) => _api.post(
    '$_drafts$draftId/reject/',
    body: {'notes': notes},
    decode: (json) => ScribeDraft.fromJson(asMap(json)),
  );
}
