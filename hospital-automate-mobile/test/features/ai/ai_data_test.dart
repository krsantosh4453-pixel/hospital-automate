import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/ai/data/ai_models.dart';
import 'package:hms_mobile/features/ai/data/ai_repository.dart';

import '../../support/test_app.dart';

// Synthetic data only.

ApiClient _client(FakeAdapter adapter) => ApiClient(
  config: testConfig,
  accessToken: () async => 'token',
  hospitalId: () => 7,
  adapter: adapter,
  log: (_) {},
);

Map<String, Object?> _body(RequestOptions options) {
  final data = options.data;
  if (data is Map) return Map<String, Object?>.from(data);
  return Map<String, Object?>.from(jsonDecode('$data') as Map);
}

void main() {
  group('models', () {
    test('capabilities read engines and keep CNN blocked', () {
      final caps = AiCapabilities.fromJson({
        'scribe': {
          'speech_to_text': {
            'available': true,
            'provider': 'whisper_api',
            'model': 'whisper-1',
          },
          'drafting': {'available': false, 'provider': '', 'model': ''},
          'languages': ['en', 'hi'],
        },
        'image_prediction': {
          'available': false,
          'status': 'blocked',
          'reason': 'No model.',
        },
      });
      expect(caps.speechToText.model, 'whisper-1');
      expect(caps.drafting.available, isFalse);
      expect(caps.scribeReady, isFalse);
      expect(caps.imagePredictionAvailable, isFalse);
      expect(caps.imagePredictionStatus, 'blocked');
      expect(caps.languages, ['en', 'hi']);
    });

    test('missing draft sections read as empty, never invented', () {
      final draft = ScribeDraft.fromJson({
        'id': 1,
        'version': 2,
        'status': 'under_review',
        'structured_extraction': {
          'symptoms': ['Cough', ''],
          'vitals': {'spo2': '97', 'heart_rate': ''},
          'allergies': <String>[],
        },
        'summary': '',
      });
      expect(draft.lines(DraftSection.symptoms), ['Cough']);
      expect(draft.lines(DraftSection.vitals), ['spo2: 97']);
      expect(draft.lines(DraftSection.allergies), isEmpty);
      expect(draft.lines(DraftSection.plan), isEmpty);
      expect(draft.lines(DraftSection.summary), isEmpty);
      expect(draft.canApprove, isTrue);
      expect(draft.awaitingGeneration, isFalse);
    });

    test('edited text becomes the schema shape of its section', () {
      expect(ScribeDraft.sectionValue(DraftSection.plan, 'Rest\n\n Fluids '), [
        'Rest',
        'Fluids',
      ]);
      expect(ScribeDraft.sectionValue(DraftSection.plan, '  '), isEmpty);
      expect(
        ScribeDraft.sectionValue(DraftSection.vitals, 'spo2: 97\nnonsense'),
        {'spo2': '97'},
      );
      expect(
        ScribeDraft.sectionValue(DraftSection.summary, 'One.\nTwo.'),
        'One. Two.',
      );
    });

    test('a queued draft reads as generating and cannot be edited', () {
      final draft = ScribeDraft.fromJson({
        'id': 1,
        'status': 'under_review',
        'structured_extraction': {},
        'generation_started_at': '2026-11-18T10:00:00Z',
        'generation_completed_at': null,
      });
      expect(draft.generating, isTrue);
      expect(draft.canEdit, isFalse);
      expect(draft.canApprove, isFalse);
      final failed = ScribeDraft.fromJson({
        'id': 1,
        'status': 'generated',
        'structured_extraction': {},
        'provider_metadata': {'error': 'timeout'},
      });
      expect(failed.lastAttemptFailed, isTrue);
      expect(failed.awaitingGeneration, isTrue);
    });

    test('mock drafts are flagged', () {
      const draft = ScribeDraft(
        id: 1,
        version: 1,
        status: DraftStatus.underReview,
        extraction: {'plan': []},
        provider: 'development',
      );
      expect(draft.fromMock, isTrue);
    });
  });

  group('ApiAiRepository', () {
    test('start recording sends the patient consent', () async {
      final adapter = FakeAdapter(
        (_) async => jsonBody(
          jsonEncode({
            'id': 4,
            'status': 'recording',
            'language': 'hi',
            'recording_consent_at': '2026-11-18T10:00:00Z',
          }),
          200,
        ),
      );
      final session = await ApiAiRepository(
        _client(adapter),
      ).startRecording(4, patientConsent: true);
      final request = adapter.requests.single;
      expect(request.path, 'ai/consultation-sessions/4/start_recording/');
      expect(_body(request), {'patient_consent': true});
      expect(session.isRecording, isTrue);
      expect(session.consentRecorded, isTrue);
    });

    test('transcribe is queued and reads a reused transcript', () async {
      final adapter = FakeAdapter(
        (_) async => jsonBody(
          jsonEncode({
            'message': 'Transcript already exists',
            'transcript': {'id': 9, 'status': 'completed', 'text': 'Hello'},
          }),
          200,
        ),
      );
      final transcript = await ApiAiRepository(
        _client(adapter),
      ).transcribe(4, language: 'hinglish');
      final request = adapter.requests.single;
      expect(request.path, 'ai/consultation-sessions/4/transcribe/');
      expect(_body(request), {'async': true, 'language': 'hinglish'});
      expect(transcript.isReady, isTrue);
      expect(transcript.text, 'Hello');
    });

    test('a section edit posts edited_section with the doctor value', () async {
      final adapter = FakeAdapter((_) async => jsonBody('{"id": 1}', 200));
      await ApiAiRepository(_client(adapter)).editSection(
        21,
        section: DraftSection.followUp,
        aiValue: const <String>[],
        doctorValue: const ['Review in 1 week'],
      );
      final request = adapter.requests.single;
      expect(request.path, 'ai/drafts/21/review/');
      expect(_body(request), {
        'action': 'edited_section',
        'section': 'follow_up',
        'ai_value': <String>[],
        'doctor_value': ['Review in 1 week'],
      });
    });

    test('approve returns the clinical note id', () async {
      final adapter = FakeAdapter(
        (_) async => jsonBody(
          jsonEncode({'message': 'ok', 'draft': {}, 'clinical_note_id': 55}),
          200,
        ),
      );
      final note = await ApiAiRepository(_client(adapter)).approve(21);
      expect(adapter.requests.single.path, 'ai/drafts/21/approve/');
      expect(note, 55);
    });

    test('a provider outage surfaces as an ApiException', () async {
      final adapter = FakeAdapter(
        (_) async => jsonBody(
          jsonEncode({'error': 'AI service is not configured.'}),
          503,
        ),
      );
      await expectLater(
        ApiAiRepository(_client(adapter)).generate(21),
        throwsA(
          isA<ApiException>().having((e) => e.statusCode, 'status', 503),
        ),
      );
    });

    test('capabilities come from ai/capabilities/', () async {
      final adapter = FakeAdapter(
        (_) async => jsonBody(
          jsonEncode({
            'scribe': {
              'speech_to_text': {'available': false},
              'drafting': {'available': false},
              'languages': [],
            },
            'image_prediction': {'available': false, 'status': 'blocked'},
          }),
          200,
        ),
      );
      final caps = await ApiAiRepository(_client(adapter)).capabilities();
      expect(adapter.requests.single.path, 'ai/capabilities/');
      expect(caps.imagePredictionStatus, 'blocked');
    });
  });
}
