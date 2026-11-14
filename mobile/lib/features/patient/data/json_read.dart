/// Small, forgiving readers for API JSON. The backend sends ids as numbers,
/// money as decimal strings ("120.00") and dates as ISO strings; a missing or
/// malformed field becomes null instead of crashing the screen.
library;

int? readInt(Object? value) => switch (value) {
  final int v => v,
  final num v => v.toInt(),
  final String v => int.tryParse(v),
  _ => null,
};

double? readMoney(Object? value) => switch (value) {
  final num v => v.toDouble(),
  final String v => double.tryParse(v),
  _ => null,
};

String? readText(Object? value) {
  if (value == null) return null;
  final text = '$value'.trim();
  return text.isEmpty ? null : text;
}

DateTime? readDateTime(Object? value) =>
    value is String ? DateTime.tryParse(value)?.toLocal() : null;

/// A `YYYY-MM-DD` date as a local calendar day (no time-zone shift).
DateTime? readDate(Object? value) {
  if (value is! String || value.length < 10) return null;
  return DateTime.tryParse(value.substring(0, 10));
}

/// A calendar day as the API writes it: `YYYY-MM-DD`.
String isoDay(DateTime day) =>
    '${day.year.toString().padLeft(4, '0')}-'
    '${day.month.toString().padLeft(2, '0')}-'
    '${day.day.toString().padLeft(2, '0')}';

/// `HH:MM[:SS]` → `HH:MM`.
String? readClock(Object? value) {
  final text = readText(value);
  if (text == null || text.length < 5) return null;
  return text.substring(0, 5);
}

Map<String, Object?> asMap(Object? value) =>
    value is Map ? Map<String, Object?>.from(value) : const {};

/// The rows of a DRF list response: a plain list or a page (`{results: [...]}`).
List<Map<String, Object?>> readRows(Object? json) {
  final rows = json is Map ? json['results'] : json;
  return [
    if (rows is List)
      for (final row in rows)
        if (row is Map) Map<String, Object?>.from(row),
  ];
}

/// Whether a paged response says another page follows.
bool hasNextPage(Object? json) => json is Map && json['next'] != null;
