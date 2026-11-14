import '../../core/network/api_client.dart';
import 'dashboard_stats.dart';

/// Source of dashboard figures. The app uses [ApiDashboardRepository];
/// tests substitute their own.
abstract interface class DashboardRepository {
  Future<DashboardStats> fetch(int hospitalId);
}

/// Reads the same endpoint the web home page uses (`api.home.stats`).
class ApiDashboardRepository implements DashboardRepository {
  ApiDashboardRepository(this._api);

  final ApiClient _api;

  @override
  Future<DashboardStats> fetch(int hospitalId) => _api.get(
    'home/stats/detail/',
    query: {'hospital': hospitalId},
    decode: DashboardStats.fromJson,
  );
}
