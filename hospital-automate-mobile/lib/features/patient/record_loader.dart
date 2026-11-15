import 'package:flutter/foundation.dart';

/// Loads one patient record list. Only the latest request may update the
/// screen, so a slow answer for the previous hospital (or a retry racing a
/// refresh) never overwrites newer data.
class RecordLoader<T> extends ChangeNotifier {
  RecordLoader(this._fetch);

  final Future<T> Function() _fetch;
  int _latest = 0;
  bool _disposed = false;

  T? data;
  Object? error;
  bool loading = false;

  /// Fetches again. Keeps the current [data] on screen while loading, so a
  /// background refresh (queue polling) does not flash a spinner.
  Future<void> load() async {
    final request = ++_latest;
    loading = true;
    error = null;
    _notify();
    try {
      final result = await _fetch();
      if (request != _latest) return;
      data = result;
    } catch (failure) {
      if (request != _latest) return;
      error = failure;
    }
    loading = false;
    _notify();
  }

  /// Replaces [data] after a local change the server has confirmed.
  void replace(T value) {
    data = value;
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
