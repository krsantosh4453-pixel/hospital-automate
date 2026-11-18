import '../../features/patient/data/json_read.dart';
import 'api_client.dart';

/// Lists are paged by 50 on the server. A screen rarely needs more than a
/// few pages, and this bounds the work if it does.
const maxListPages = 5;

/// The first page of a DRF list and the server's total `count` (null when
/// the list is not paged), for counts and "recent" lists.
Future<({List<Map<String, Object?>> rows, int? count})> getFirstPage(
  ApiClient api,
  String path, {
  Map<String, Object?>? query,
}) => api.get<({List<Map<String, Object?>> rows, int? count})>(
  path,
  query: query,
  decode: (json) => (
    rows: List.unmodifiable(readRows(json)),
    count: json is Map ? readInt(json['count']) : readRows(json).length,
  ),
);

/// Every row of a DRF list at [path], following `next` up to [maxPages].
Future<List<Map<String, Object?>>> getAllRows(
  ApiClient api,
  String path, {
  Map<String, Object?>? query,
  int maxPages = maxListPages,
}) async {
  final rows = <Map<String, Object?>>[];
  for (var page = 1; page <= maxPages; page++) {
    final json = await api.get<Object?>(
      path,
      query: {...?query, if (page > 1) 'page': page},
      decode: (json) => json,
    );
    rows.addAll(readRows(json));
    if (!hasNextPage(json)) break;
  }
  return List.unmodifiable(rows);
}
