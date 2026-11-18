// Opt-in end-to-end check of the AI scribe against a REAL backend, using the
// app's own API client and repositories (no fakes).
//
// Only for a throwaway e2e server (config.settings.e2e, development mock STT
// and LLM, Celery eager) with seed_demo data, plus one open visit of a
// synthetic patient with demo.doctor1, written to HMS_LIVE_AI_SEED as
// {visit}. Run:
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8151 HMS_LIVE_PASSWORD=… \
//   HMS_LIVE_AI_SEED=…/ai.json flutter test test/live/ai_scribe_live_test.dart
// It uploads synthetic audio bytes and writes one clinical note on that visit.
// Never point it at a server with real patients.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/ai/data/ai_models.dart';
import 'package:hms_mobile/features/ai/data/ai_repository.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';

final _env = Platform.environment;
final _origin = _env['HMS_LIVE_ORIGIN'];
final _password = _env['HMS_LIVE_PASSWORD'];
final _seedPath = _env['HMS_LIVE_AI_SEED'];

const _device = DeviceInfo(
  deviceId: 'live-test-ai',
  platform: 'other',
  appVersion: 'live-test',
);

void main() {
  final skip = _origin == null || _password == null || _seedPath == null
      ? 'Set HMS_LIVE_ORIGIN, HMS_LIVE_PASSWORD and HMS_LIVE_AI_SEED to run'
      : null;

  late int visitId;
  String? token;
  int? hospitalId;
  late ApiClient api;
  late ApiAiRepository ai;
  late ApiDoctorRepository doctors;
  late ScribeSession session;
  late ScribeDraft draft;
  late Directory tmp;

  Future<int> signIn(String username) async {
    final auth = ApiAuthRepository(api);
    token = (await auth.staffPasswordLogin(
      username,
      _password!,
      _device,
    )).access;
    hospitalId = (await auth.meContexts()).hospitals.single.id;
    return (await auth.staffMe()).id!;
  }

  setUpAll(() {
    if (skip != null) return;
    final seed = jsonDecode(File(_seedPath!).readAsStringSync()) as Map;
    visitId = seed['visit'] as int;
    api = ApiClient(
      config: ApiConfig(origin: _origin!),
      accessToken: () async => token,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
    ai = ApiAiRepository(api);
    doctors = ApiDoctorRepository(api);
    tmp = Directory.systemTemp.createTempSync('hms-ai-live-');
  });

  tearDownAll(() {
    if (skip == null) tmp.deleteSync(recursive: true);
  });

  test('1. capabilities report engines and a blocked CNN', () async {
    await signIn('demo.doctor1');
    final caps = await ai.capabilities();
    expect(caps.scribeReady, isTrue);
    expect(caps.imagePredictionAvailable, isFalse);
    expect(caps.imagePredictionStatus, 'blocked');
  }, skip: skip);

  test('2. consent is required, then the consultation is recorded', () async {
    final userId = await signIn('demo.doctor1');
    final visit = await doctors.visit(visitId);
    final me = await doctors.myProfile(
      hospitalId: hospitalId!,
      userId: userId,
    );
    session = await ai.createSession(
      visitId: visit.id,
      hospitalId: hospitalId!,
      patientId: visit.patientId!,
      doctorId: me!.id,
      language: 'en',
    );
    await expectLater(
      ai.startRecording(session.id, patientConsent: false),
      throwsA(isA<ApiException>()),
    );
    session = await ai.startRecording(session.id, patientConsent: true);
    expect(session.isRecording, isTrue);

    final file = File('${tmp.path}/consultation.m4a')
      ..writeAsBytesSync(utf8.encode('synthetic-audio-bytes'));
    session = await ai.stopRecording(
      session.id,
      ScribeAudio(path: file.path, duration: const Duration(seconds: 30)),
    );
    expect(session.hasAudio, isTrue);
  }, skip: skip);

  test('3. queued transcription and drafting finish on the server', () async {
    await ai.transcribe(session.id, language: 'en');
    final transcript = await ai.transcript(session.id);
    expect(transcript!.isReady, isTrue);

    var drafts = await ai.drafts(session.id);
    expect(drafts.single.awaitingGeneration, isTrue);
    await ai.generate(drafts.single.id);
    drafts = await ai.drafts(session.id);
    draft = drafts.single;
    expect(draft.generating, isFalse);
    expect(draft.canApprove, isTrue);
  }, skip: skip);

  test('4. another doctor can neither see nor approve the draft', () async {
    await signIn('demo.doctor2');
    await expectLater(
      ai.approve(draft.id),
      throwsA(
        isA<ApiException>().having(
          (e) => e.kind,
          'kind',
          anyOf(ApiErrorKind.forbidden, ApiErrorKind.notFound),
        ),
      ),
    );
  }, skip: skip);

  test('5. the doctor edits, approves, and a clinical note is saved', () async {
    await signIn('demo.doctor1');
    await ai.editSection(
      draft.id,
      section: DraftSection.followUp,
      aiValue: draft.extraction['follow_up'] ?? const <String>[],
      doctorValue: const ['Live test: review in 3 days'],
    );
    final noteId = await ai.approve(draft.id);
    expect(noteId, isNotNull);
    final notes = await doctors.notes(visitId);
    expect(notes.any((n) => n.id == noteId), isTrue);
    final approved = (await ai.drafts(session.id)).single;
    expect(approved.status, DraftStatus.approved);
    await expectLater(ai.regenerate(draft.id), throwsA(isA<ApiException>()));
  }, skip: skip);
}
