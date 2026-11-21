import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// One AI assist the server can or cannot run (`GET ai/capabilities/`).
@immutable
class AiEngine {
  const AiEngine({
    required this.available,
    this.provider = '',
    this.model = '',
    this.mock = false,
  });

  factory AiEngine.fromJson(Object? json) {
    final map = asMap(json);
    return AiEngine(
      available: map['available'] == true,
      provider: readText(map['provider']) ?? '',
      model: readText(map['model']) ?? '',
      mock: map['mock'] == true,
    );
  }

  final bool available;
  final String provider;
  final String model;

  /// The development provider: canned text that may never enter a record.
  final bool mock;
}

/// What the hospital's server offers: the scribe's speech-to-text and
/// drafting engines, and the image-prediction (CNN) status.
@immutable
class AiCapabilities {
  const AiCapabilities({
    required this.speechToText,
    required this.drafting,
    required this.languages,
    required this.imagePredictionAvailable,
    required this.imagePredictionStatus,
    required this.imagePredictionReason,
  });

  factory AiCapabilities.fromJson(Object? json) {
    final map = asMap(json);
    final scribe = asMap(map['scribe']);
    final image = asMap(map['image_prediction']);
    final languages = scribe['languages'];
    return AiCapabilities(
      speechToText: AiEngine.fromJson(scribe['speech_to_text']),
      drafting: AiEngine.fromJson(scribe['drafting']),
      languages: [
        if (languages is List)
          for (final code in languages) '$code',
      ],
      imagePredictionAvailable: image['available'] == true,
      imagePredictionStatus: readText(image['status']) ?? 'blocked',
      imagePredictionReason: readText(image['reason']) ?? '',
    );
  }

  final AiEngine speechToText;
  final AiEngine drafting;
  final List<String> languages;
  final bool imagePredictionAvailable;
  final String imagePredictionStatus;
  final String imagePredictionReason;

  bool get scribeReady => speechToText.available && drafting.available;
}

/// `ConsultationSession.Status`.
abstract final class ScribeSessionStatus {
  static const active = 'active';
  static const recording = 'recording';
  static const completed = 'completed';
  static const cancelled = 'cancelled';
}

/// An AI scribe session for one visit (`ai/consultation-sessions/`).
@immutable
class ScribeSession {
  const ScribeSession({
    required this.id,
    required this.status,
    required this.language,
    this.visitId,
    this.patientName,
    this.hasAudio = false,
    this.consentRecorded = false,
    this.startedAt,
  });

  factory ScribeSession.fromJson(Map<String, Object?> json) => ScribeSession(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? ScribeSessionStatus.active,
    language: readText(json['language']) ?? 'en',
    visitId: readInt(json['visit']),
    patientName: readText(json['patient_name']),
    hasAudio: readText(json['audio_file']) != null,
    consentRecorded: readText(json['recording_consent_at']) != null,
    startedAt: readDateTime(json['started_at']),
  );

  final int id;
  final String status;
  final String language;
  final int? visitId;
  final String? patientName;
  final bool hasAudio;
  final bool consentRecorded;
  final DateTime? startedAt;

  bool get isRecording => status == ScribeSessionStatus.recording;
}

/// `ConversationTranscript.Status`.
abstract final class TranscriptStatus {
  static const pending = 'pending';
  static const processing = 'processing';
  static const completed = 'completed';
  static const failed = 'failed';
}

/// The speech-to-text result of a session (`ai/transcripts/`).
@immutable
class ScribeTranscript {
  const ScribeTranscript({
    required this.id,
    required this.status,
    required this.text,
    this.provider = '',
    this.detectedLanguage = '',
  });

  factory ScribeTranscript.fromJson(Map<String, Object?> json) =>
      ScribeTranscript(
        id: readInt(json['id']) ?? 0,
        status: readText(json['status']) ?? TranscriptStatus.pending,
        text: readText(json['text']) ?? '',
        provider: readText(json['provider']) ?? '',
        detectedLanguage: readText(json['detected_language']) ?? '',
      );

  final int id;
  final String status;
  final String text;
  final String provider;
  final String detectedLanguage;

  bool get isReady => status == TranscriptStatus.completed && text.isNotEmpty;
  bool get inProgress => status == TranscriptStatus.processing;
}

/// `AIConsultationDraft.Status`.
abstract final class DraftStatus {
  static const generated = 'generated';
  static const underReview = 'under_review';
  static const edited = 'edited';
  static const approved = 'approved';
  static const rejected = 'rejected';
}

/// The sections of a clinical draft, in the order of the clinical note
/// (ai_scribe/services/llm.py DEFAULT_SCHEMA). [vitals] is an object, the
/// summary a string, every other section a list of short lines.
enum DraftSection {
  chiefComplaint('chief_complaint'),
  symptoms('symptoms'),
  history('history'),
  allergies('allergies'),
  medications('medications'),
  examination('examination'),
  vitals('vitals'),
  assessment('assessment'),
  investigations('investigations'),
  plan('plan'),
  followUp('follow_up'),
  summary('summary');

  const DraftSection(this.key);

  final String key;
}

/// The vital-sign fields the draft schema allows.
const draftVitalKeys = ['blood_pressure', 'heart_rate', 'temperature', 'spo2'];

/// An AI clinical draft (`ai/drafts/`). Nothing in it is part of the medical
/// record until the doctor approves it.
@immutable
class ScribeDraft {
  const ScribeDraft({
    required this.id,
    required this.version,
    required this.status,
    required this.extraction,
    this.summary = '',
    this.provider = '',
    this.model = '',
    this.clinicalNoteId,
    this.generationStartedAt,
    this.generationCompletedAt,
    this.lastAttemptFailed = false,
  });

  factory ScribeDraft.fromJson(Map<String, Object?> json) => ScribeDraft(
    id: readInt(json['id']) ?? 0,
    version: readInt(json['version']) ?? 1,
    status: readText(json['status']) ?? DraftStatus.generated,
    extraction: Map.unmodifiable(asMap(json['structured_extraction'])),
    summary: readText(json['summary']) ?? '',
    provider: readText(json['provider']) ?? '',
    model: readText(json['provider_model']) ?? '',
    clinicalNoteId: readInt(json['final_clinical_note']),
    generationStartedAt: readDateTime(json['generation_started_at']),
    generationCompletedAt: readDateTime(json['generation_completed_at']),
    lastAttemptFailed:
        readText(json['status']) == DraftStatus.generated &&
        asMap(json['provider_metadata'])['error'] != null,
  );

  final int id;
  final int version;
  final String status;
  final Map<String, Object?> extraction;
  final String summary;
  final String provider;
  final String model;
  final int? clinicalNoteId;
  final DateTime? generationStartedAt;
  final DateTime? generationCompletedAt;

  /// The previous generation failed (provider down or timed out).
  final bool lastAttemptFailed;

  /// The provider is still writing this draft (queued on the server).
  bool get generating =>
      status == DraftStatus.underReview &&
      generationStartedAt != null &&
      generationCompletedAt == null;

  /// No AI text yet: the doctor still has to ask for the draft.
  bool get awaitingGeneration =>
      status == DraftStatus.generated && extraction.isEmpty;
  bool get canEdit =>
      !generating &&
      (status == DraftStatus.underReview || status == DraftStatus.edited);
  bool get canApprove => canEdit;
  bool get isFinal =>
      status == DraftStatus.approved || status == DraftStatus.rejected;
  bool get fromMock => provider == 'development';

  /// The lines of a section; an empty list means "not recorded".
  List<String> lines(DraftSection section) {
    final value = section == DraftSection.summary
        ? (summary.isNotEmpty ? summary : extraction[section.key])
        : extraction[section.key];
    return switch (value) {
      final List<Object?> items => [
        for (final item in items)
          if ('${item ?? ''}'.trim().isNotEmpty) '$item'.trim(),
      ],
      final Map<Object?, Object?> map => [
        for (final key in draftVitalKeys)
          if ('${map[key] ?? ''}'.trim().isNotEmpty) '$key: ${map[key]}',
      ],
      final String text when text.trim().isNotEmpty => [text.trim()],
      _ => const [],
    };
  }

  /// The value to send when the doctor saves [text] for [section]: one line
  /// per item, `name: value` lines for vitals, plain text for the summary.
  static Object sectionValue(DraftSection section, String text) {
    final rows = [
      for (final line in text.split('\n'))
        if (line.trim().isNotEmpty) line.trim(),
    ];
    if (section == DraftSection.summary) return rows.join(' ');
    if (section == DraftSection.vitals) {
      return {
        for (final row in rows)
          if (row.contains(':'))
            row.substring(0, row.indexOf(':')).trim(): row
                .substring(row.indexOf(':') + 1)
                .trim(),
      };
    }
    return rows;
  }
}
