import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'ai_repository.dart';

/// Records the consultation to a temporary file. The scribe screen only
/// starts it after the doctor confirms the patient's consent.
abstract interface class ScribeRecorder {
  /// Asks for the microphone; false when the user refuses.
  Future<bool> requestPermission();
  Future<void> start();

  /// Stops and returns the recording, or null when nothing was captured.
  Future<ScribeAudio?> stop();
  Future<void> cancel();

  /// Deletes a recording returned by [stop] once it has been uploaded (or
  /// the upload failed): consultation audio must not stay on the device.
  Future<void> discard(ScribeAudio audio);
  Future<void> dispose();
}

/// [ScribeRecorder] on the device microphone (AAC in an .m4a file, which the
/// server accepts as `audio/mp4`).
class DeviceScribeRecorder implements ScribeRecorder {
  DeviceScribeRecorder({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final AudioRecorder _recorder = AudioRecorder();
  final DateTime Function() _clock;
  DateTime? _startedAt;

  @override
  Future<bool> requestPermission() => _recorder.hasPermission();

  @override
  Future<void> start() async {
    final dir = await getTemporaryDirectory();
    final stamp = _clock().millisecondsSinceEpoch;
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc, numChannels: 1),
      path: '${dir.path}/scribe-$stamp.m4a',
    );
    _startedAt = _clock();
  }

  @override
  Future<ScribeAudio?> stop() async {
    final path = await _recorder.stop();
    final started = _startedAt;
    _startedAt = null;
    if (path == null || started == null) return null;
    return ScribeAudio(path: path, duration: _clock().difference(started));
  }

  @override
  Future<void> cancel() async {
    _startedAt = null;
    await _recorder.cancel();
  }

  @override
  Future<void> discard(ScribeAudio audio) async {
    final file = File(audio.path);
    if (await file.exists()) await file.delete();
  }

  @override
  Future<void> dispose() => _recorder.dispose();
}

final _recordingName = RegExp(r'^scribe-\d+\.m4a$');

/// Deletes consultation recordings left in [dir] by a recording that never
/// reached its upload (the app was killed or crashed). Run at start-up and
/// at sign-out; returns how many files were removed.
Future<int> deleteLeftoverRecordings(Directory dir) async {
  if (!await dir.exists()) return 0;
  var removed = 0;
  await for (final entity in dir.list(followLinks: false)) {
    final name = entity.uri.pathSegments.last;
    if (entity is File && _recordingName.hasMatch(name)) {
      await entity.delete();
      removed++;
    }
  }
  return removed;
}

/// [deleteLeftoverRecordings] in the app's temporary directory, where
/// [DeviceScribeRecorder] records.
Future<int> deleteLeftoverRecordingsInTemp() async =>
    deleteLeftoverRecordings(await getTemporaryDirectory());
