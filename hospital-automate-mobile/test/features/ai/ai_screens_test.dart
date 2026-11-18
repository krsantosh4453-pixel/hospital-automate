import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/ai/data/ai_models.dart';
import 'package:hms_mobile/features/ai/ui/scribe_screen.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/shared/widgets/hms_button.dart';

import '../../support/test_app.dart';

// Synthetic data only.

SessionState aiDoctorSession() => SessionState(
  user: const SessionUser(id: 90, displayName: 'dr.test', firstName: 'Test'),
  hospitals: const [
    HospitalContext(
      id: 1,
      name: 'Test General Hospital',
      role: 'Doctor',
      permissions: {'Dashboard.View', 'Doctors.View', 'AIScribe.View'},
    ),
  ],
  activeHospitalId: 1,
);

const scribeVisit = Visit(
  id: 5,
  status: Visit.inConsultation,
  patientId: 2,
  patientName: 'Test Patient Two',
  doctorId: 3,
  hospitalId: 1,
  visitType: 'OPD',
);

Future<({FakeAiRepository ai, FakeScribeRecorder mic})> pumpAi(
  WidgetTester tester,
  String location, {
  FakeAiRepository? ai,
  FakeScribeRecorder? mic,
  List<Visit> visits = const [scribeVisit],
}) async {
  final repo = ai ?? FakeAiRepository();
  final recorder = mic ?? FakeScribeRecorder();
  await pumpApp(
    tester,
    testServices(
      session: aiDoctorSession(),
      doctor: FakeDoctorRepository(visitRows: visits),
      ai: repo,
      scribeRecorder: () => recorder,
    ),
    location: location,
  );
  return (ai: repo, mic: recorder);
}

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('dashboard shows engines, a blocked CNN and no sessions', (
    tester,
  ) async {
    await pumpAi(tester, '/ai-scribe');

    expect(find.text('AI assist'), findsWidgets);
    expect(find.text('AI output is a draft, not a diagnosis'), findsOneWidget);
    expect(find.text('openai · gpt-4o-mini'), findsOneWidget);
    expect(find.text('whisper_api · whisper-1'), findsOneWidget);
    expect(find.byKey(const Key('cnn-status')), findsOneWidget);
    expect(find.text('Blocked'), findsOneWidget);
    expect(find.textContaining('never be a diagnosis'), findsOneWidget);
    expect(find.text('No scribe sessions yet'), findsOneWidget);
  });

  testWidgets('dashboard says when no engine is configured', (tester) async {
    final ai = FakeAiRepository(
      caps: const AiCapabilities(
        speechToText: AiEngine(available: false),
        drafting: AiEngine(available: false),
        languages: [],
        imagePredictionAvailable: false,
        imagePredictionStatus: 'blocked',
        imagePredictionReason: '',
      ),
    );
    await pumpAi(tester, '/ai-scribe', ai: ai);
    expect(find.text('Not configured on this server'), findsNWidgets(2));
  });

  testWidgets('recording needs the patient consent first', (tester) async {
    final env = await pumpAi(tester, '/ai-scribe/visits/5');

    final start = find.byKey(const Key('start-recording'));
    await tester.ensureVisible(start);
    expect(tester.widget<HmsButton>(start).onPressed, isNull);
    expect(env.ai.calls, isEmpty);

    await tapKey(tester, 'scribe-consent');
    await tapKey(tester, 'start-recording');
    expect(env.ai.calls, ['create:en', 'start']);
    expect(env.ai.consentSent, isTrue);
    expect(env.mic.recording, isTrue);
    expect(find.text('Recording… speak normally.'), findsOneWidget);
  });

  testWidgets('a refused microphone stops before the server is called', (
    tester,
  ) async {
    final env = await pumpAi(
      tester,
      '/ai-scribe/visits/5',
      mic: FakeScribeRecorder(permission: false),
    );
    await tapKey(tester, 'scribe-consent');
    await tapKey(tester, 'start-recording');
    expect(env.ai.calls, isEmpty);
    expect(
      find.text('Microphone permission is needed to record.'),
      findsOneWidget,
    );
  });

  testWidgets('record, transcribe, draft, edit and approve end to end', (
    tester,
  ) async {
    final env = await pumpAi(tester, '/ai-scribe/visits/5');

    await tapKey(tester, 'scribe-consent');
    await tapKey(tester, 'start-recording');
    await tapKey(tester, 'stop-recording');
    expect(env.ai.uploads.single.duration, const Duration(seconds: 42));
    expect(find.text('Audio uploaded'), findsWidgets);

    await tapKey(tester, 'transcribe');
    expect(env.ai.calls, contains('transcribe:en'));
    expect(find.byKey(const Key('transcript-text')), findsOneWidget);

    await tapKey(tester, 'generate-draft');
    expect(env.ai.calls, contains('generate'));
    expect(find.text('AI draft v1: pending your review'), findsOneWidget);
    // Sections the consultation did not cover stay marked as missing.
    expect(
      find.descendant(
        of: find.byKey(const Key('section-allergies')),
        matching: find.text('Not recorded in this consultation'),
      ),
      findsOneWidget,
    );
    expect(find.text('• Fluids and rest'), findsOneWidget);

    await tapKey(tester, 'edit-follow_up');
    await tester.enterText(
      find.descendant(
        of: find.byKey(const Key('section-editor')),
        matching: find.byType(TextField),
      ),
      'Review in 3 days',
    );
    await tester.tap(find.byKey(const Key('save-section')));
    await tester.pumpAndSettle();
    expect(env.ai.edits.single.section, DraftSection.followUp);
    expect(env.ai.edits.single.value, ['Review in 3 days']);
    expect(find.text('• Review in 3 days'), findsOneWidget);

    // Approval is explicit: nothing is saved until the doctor confirms.
    await tapKey(tester, 'approve-draft');
    expect(env.ai.calls, isNot(contains('approve')));
    expect(find.text('Save this draft to the medical record?'), findsOneWidget);
    await tester.tap(find.text('Approve and save').last);
    await tester.pumpAndSettle();
    expect(env.ai.calls.last, 'approve');
    expect(find.text('Approved and saved to the record'), findsWidgets);
    expect(find.byKey(const Key('approve-draft')), findsNothing);
  });

  testWidgets('a queued draft shows progress, then appears by itself', (
    tester,
  ) async {
    final ai = FakeAiRepository(
      sessions: const [
        ScribeSession(
          id: 40,
          status: ScribeSessionStatus.completed,
          language: 'en',
          visitId: 5,
          hasAudio: true,
          consentRecorded: true,
        ),
      ],
      transcriptValue: const ScribeTranscript(
        id: 31,
        status: TranscriptStatus.completed,
        text: 'Synthetic transcript.',
      ),
      drafts: const [
        ScribeDraft(
          id: 21,
          version: 1,
          status: DraftStatus.generated,
          extraction: {},
        ),
      ],
    )..queuedReads = 1;
    await pumpAi(tester, '/ai-scribe/visits/5', ai: ai);
    final generate = find.byKey(const Key('generate-draft'));
    await tester.ensureVisible(generate);
    await tester.pumpAndSettle();
    // Single frames: settling would run the poller to the end.
    await tester.tap(generate);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const Key('draft-working')), findsOneWidget);
    expect(find.byKey(const Key('approve-draft')), findsNothing);

    await tester.pump(scribePollInterval);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('draft-working')), findsNothing);
    expect(find.text('AI draft v1: pending your review'), findsOneWidget);
  });

  testWidgets('a failed queued draft says so and offers another try', (
    tester,
  ) async {
    final ai = FakeAiRepository(
      sessions: const [
        ScribeSession(
          id: 40,
          status: ScribeSessionStatus.completed,
          language: 'en',
          visitId: 5,
          hasAudio: true,
          consentRecorded: true,
        ),
      ],
      transcriptValue: const ScribeTranscript(
        id: 31,
        status: TranscriptStatus.completed,
        text: 'Synthetic transcript.',
      ),
      drafts: const [
        ScribeDraft(
          id: 21,
          version: 1,
          status: DraftStatus.generated,
          extraction: {},
        ),
      ],
    )..failQueuedGeneration = true;
    await pumpAi(tester, '/ai-scribe/visits/5', ai: ai);
    await tapKey(tester, 'generate-draft');
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('draft-failed')), findsOneWidget);
    expect(find.byKey(const Key('generate-draft')), findsOneWidget);
  });

  testWidgets('a provider outage shows the manual-documentation message', (
    tester,
  ) async {
    final ai = FakeAiRepository(
      sessions: const [
        ScribeSession(
          id: 40,
          status: ScribeSessionStatus.completed,
          language: 'en',
          visitId: 5,
          hasAudio: true,
          consentRecorded: true,
        ),
      ],
    );
    ai.error = const ApiException(
      kind: ApiErrorKind.unavailable,
      statusCode: 503,
    );
    await pumpAi(tester, '/ai-scribe/visits/5', ai: ai);
    await tapKey(tester, 'transcribe');
    expect(
      find.text(
        'The AI service is not available. Document the consultation manually.',
      ),
      findsOneWidget,
    );
    expect(find.byKey(const Key('transcript-text')), findsNothing);
  });

  testWidgets("another doctor's visit is read-only", (tester) async {
    const otherVisit = Visit(
      id: 5,
      status: Visit.inConsultation,
      patientId: 2,
      patientName: 'Test Patient Two',
      doctorId: 99,
      hospitalId: 1,
    );
    final ai = FakeAiRepository(
      sessions: const [
        ScribeSession(
          id: 40,
          status: ScribeSessionStatus.completed,
          language: 'en',
          visitId: 5,
          hasAudio: true,
          consentRecorded: true,
        ),
      ],
      transcriptValue: const ScribeTranscript(
        id: 31,
        status: TranscriptStatus.completed,
        text: 'Synthetic transcript.',
      ),
      drafts: const [testDraft],
    );
    await pumpAi(tester, '/ai-scribe/visits/5', ai: ai, visits: [otherVisit]);
    expect(
      find.text('You can view this scribe session but not change it.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('start-recording')), findsNothing);
    expect(find.byKey(const Key('approve-draft')), findsNothing);
    expect(find.byKey(const Key('edit-plan')), findsNothing);
  });

  testWidgets('the consultation page links to the scribe', (tester) async {
    await pumpAi(tester, '/consultation/5');
    await tapKey(tester, 'open-ai-scribe');
    expect(find.byKey(const Key('scribe-record')), findsOneWidget);
  });
}
