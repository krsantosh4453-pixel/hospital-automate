import 'package:flutter/foundation.dart';

import 'dashboard_repository.dart';
import 'dashboard_stats.dart';

/// Loads dashboard figures for the active hospital. Only the latest request
/// may update the screen: after a hospital switch a slow earlier answer
/// (or its 403) must not overwrite the new figures.
class DashboardController extends ChangeNotifier {
  DashboardController(this._repository);

  final DashboardRepository _repository;
  int _latest = 0;
  bool _disposed = false;

  DashboardStats? stats;
  Object? error;
  bool loading = false;

  Future<void> load(int hospitalId) async {
    final request = ++_latest;
    loading = true;
    error = null;
    _notify();
    try {
      final result = await _repository.fetch(hospitalId);
      if (request != _latest) return;
      stats = result;
    } catch (failure) {
      if (request != _latest) return;
      error = failure;
    }
    loading = false;
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
