import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../patient/data/json_read.dart';
import 'hospital_models.dart';

/// Configuration of the acting hospital: its record, departments, wards and
/// staff. Read-only in the app; the server lists only hospitals the person
/// belongs to and answers 403 for staff lists outside Admin or Manager.
abstract interface class HospitalRepository {
  Future<HospitalInfo> hospital(int id);
  Future<List<Department>> departments();
  Future<List<Ward>> wards();
  Future<List<StaffMember>> staff({String search});
}

class ApiHospitalRepository implements HospitalRepository {
  ApiHospitalRepository(this._api);

  final ApiClient _api;

  @override
  Future<HospitalInfo> hospital(int id) => _api.get(
    'hospital/hospitals/$id/',
    decode: (json) => HospitalInfo.fromJson(asMap(json)),
  );

  @override
  Future<List<Department>> departments() async => [
    for (final row in await getAllRows(_api, 'hospital/departments/'))
      Department.fromJson(row),
  ];

  @override
  Future<List<Ward>> wards() async => [
    for (final row in await getAllRows(_api, 'hospital/wards/'))
      Ward.fromJson(row),
  ];

  @override
  Future<List<StaffMember>> staff({String search = ''}) => _api.get(
    'users/',
    query: {if (search.trim().isNotEmpty) 'search': search.trim()},
    decode: (json) => [
      for (final row in readRows(asMap(json)['staff']))
        StaffMember.fromJson(row),
    ],
  );
}
