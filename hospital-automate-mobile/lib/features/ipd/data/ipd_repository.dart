import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../patient/data/json_read.dart';
import 'ipd_models.dart';

const _admissions = 'ipd/admissions/';

/// Bed lists are read up to this many pages (50 beds each); past that the
/// board says its counts are partial instead of guessing.
const maxBedPages = 10;

/// Inpatient stays, beds and discharges of the acting hospital.
///
/// The server scopes every list to that hospital and to the patients the
/// role may see (users/care_scope.py). Bed moves and discharge steps need a
/// Doctor, Nurse or Admin role there; it refuses an occupied bed, a second
/// bed for one stay and a discharge whose checklist, summary or bill is not
/// done (ipd/views.py, ipd/discharge.py). The app only reflects its answers.
abstract interface class IpdRepository {
  Future<IpdOverview> overview(int hospitalId);
  Future<List<IpdAdmission>> admissions({String? status, int? patientId});
  Future<IpdAdmission> admission(int id);
  Future<DischargeReadiness> readiness(int admissionId);
  Future<List<AvailableBed>> availableBeds(int hospitalId);
  Future<BedBoard> bedBoard();
  Future<void> allocateBed(int admissionId, int bedId);
  Future<void> transferBed(int admissionId, int bedId);
  Future<IpdAdmission> initiateDischarge(int admissionId);
  Future<IpdAdmission> completeDischarge(int admissionId);

  /// The stay's discharge summary, or null when none is written. The server
  /// shows summaries to doctors and managers only (403 for other roles).
  Future<DischargeSummaryRecord?> dischargeSummary(int admissionId);
}

/// [IpdRepository] over the endpoints the web's IPD page uses.
class ApiIpdRepository implements IpdRepository {
  ApiIpdRepository(this._api);

  final ApiClient _api;

  @override
  Future<IpdOverview> overview(int hospitalId) async {
    final counts = await Future.wait([
      _count(AdmissionStatus.admitted),
      _count(AdmissionStatus.dischargeInitiated),
      _count(AdmissionStatus.discharged),
      _availableCount(hospitalId),
    ]);
    return IpdOverview(
      admitted: counts[0],
      dischargeInitiated: counts[1],
      discharged: counts[2],
      availableBeds: counts[3],
    );
  }

  @override
  Future<List<IpdAdmission>> admissions({
    String? status,
    int? patientId,
  }) async => [
    for (final row in await getAllRows(
      _api,
      _admissions,
      query: {'status': ?status, 'patient': ?patientId},
    ))
      IpdAdmission.fromJson(row),
  ];

  @override
  Future<IpdAdmission> admission(int id) => _api.get(
    '$_admissions$id/',
    decode: (json) => IpdAdmission.fromJson(asMap(json)),
  );

  @override
  Future<DischargeReadiness> readiness(int admissionId) => _api.get(
    '$_admissions$admissionId/readiness/',
    decode: (json) => DischargeReadiness.fromJson(asMap(json)),
  );

  @override
  Future<List<AvailableBed>> availableBeds(int hospitalId) => _api.get(
    'ipd/bed-allocations/available_beds/',
    query: {'hospital': hospitalId},
    decode: (json) => [
      for (final row in readRows(json)) AvailableBed.fromJson(row),
    ],
  );

  @override
  Future<BedBoard> bedBoard() async {
    final beds = <HospitalBed>[];
    for (var page = 1; page <= maxBedPages; page++) {
      final json = await _api.get<Object?>(
        'hospital/beds/',
        query: {if (page > 1) 'page': page},
        decode: (json) => json,
      );
      beds.addAll(readRows(json).map(HospitalBed.fromJson));
      if (!hasNextPage(json)) {
        return BedBoard(beds: List.unmodifiable(beds), complete: true);
      }
    }
    return BedBoard(beds: List.unmodifiable(beds), complete: false);
  }

  @override
  Future<void> allocateBed(int admissionId, int bedId) =>
      _bedMove(admissionId, 'allocate_bed', bedId);

  @override
  Future<void> transferBed(int admissionId, int bedId) =>
      _bedMove(admissionId, 'transfer', bedId);

  @override
  Future<IpdAdmission> initiateDischarge(int admissionId) =>
      _step(admissionId, 'initiate_discharge');

  @override
  Future<IpdAdmission> completeDischarge(int admissionId) =>
      _step(admissionId, 'complete_discharge');

  /// The list has no `?admission=` filter on the server, so rows are
  /// matched here by their own `admission` field.
  @override
  Future<DischargeSummaryRecord?> dischargeSummary(int admissionId) async {
    final rows = await getAllRows(_api, 'ipd/discharge-summaries/');
    for (final row in rows) {
      if (readInt(row['admission']) == admissionId) {
        return DischargeSummaryRecord.fromJson(row);
      }
    }
    return null;
  }

  Future<void> _bedMove(int admissionId, String action, int bedId) => _api.post(
    '$_admissions$admissionId/$action/',
    body: {'bed_id': bedId},
    decode: (_) {},
  );

  Future<IpdAdmission> _step(int admissionId, String action) => _api.post(
    '$_admissions$admissionId/$action/',
    body: const <String, Object?>{},
    decode: (json) => IpdAdmission.fromJson(asMap(json)),
  );

  /// The server's total for [status]: DRF's `count`, or the row count of an
  /// unpaged answer.
  Future<int?> _count(String status) => _api.get(
    _admissions,
    query: {'status': status},
    decode: (json) =>
        json is Map ? readInt(json['count']) : readRows(json).length,
  );

  Future<int?> _availableCount(int hospitalId) async =>
      (await availableBeds(hospitalId)).length;
}
