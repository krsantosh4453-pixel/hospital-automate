import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// A hospital as `HospitalSerializer` sends it. Only fields the server has
/// are kept; the counts are the server's own.
@immutable
class HospitalInfo {
  const HospitalInfo({
    required this.id,
    required this.name,
    this.code,
    this.type,
    this.isActive = true,
    this.address,
    this.city,
    this.state,
    this.phone,
    this.email,
    this.departments,
    this.doctors,
    this.nurses,
    this.grievanceOfficerName,
    this.grievanceOfficerEmail,
    this.grievanceOfficerPhone,
  });

  factory HospitalInfo.fromJson(Map<String, Object?> json) => HospitalInfo(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    code: readText(json['code']),
    type: readText(json['type']),
    isActive: json['is_active'] != false,
    address: readText(json['address']),
    city: readText(json['city']),
    state: readText(json['state']),
    phone: readText(json['phone']),
    email: readText(json['email']),
    departments: readInt(json['departments']),
    doctors: readInt(json['doctors']),
    nurses: readInt(json['nurses']),
    grievanceOfficerName: readText(json['grievance_officer_name']),
    grievanceOfficerEmail: readText(json['grievance_officer_email']),
    grievanceOfficerPhone: readText(json['grievance_officer_phone']),
  );

  final int id;
  final String name;
  final String? code;
  final String? type;
  final bool isActive;
  final String? address;
  final String? city;
  final String? state;
  final String? phone;
  final String? email;
  final int? departments;
  final int? doctors;
  final int? nurses;
  final String? grievanceOfficerName;
  final String? grievanceOfficerEmail;
  final String? grievanceOfficerPhone;

  /// Address, city and state on one line, skipping blanks.
  String? get fullAddress {
    final parts = [address, city, state].whereType<String>().toList();
    return parts.isEmpty ? null : parts.join(', ');
  }
}

@immutable
class Department {
  const Department({
    required this.id,
    required this.name,
    this.code,
    this.headName,
    this.doctors,
    this.description,
    this.isActive = true,
  });

  factory Department.fromJson(Map<String, Object?> json) => Department(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    code: readText(json['code']),
    headName: readText(json['head_name']),
    doctors: readInt(json['doctors']),
    description: readText(json['description']),
    isActive: json['is_active'] != false,
  );

  final int id;
  final String name;
  final String? code;
  final String? headName;
  final int? doctors;
  final String? description;
  final bool isActive;
}

@immutable
class Ward {
  const Ward({required this.id, required this.name, this.wardType});

  factory Ward.fromJson(Map<String, Object?> json) => Ward(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    wardType: readText(json['ward_type']),
  );

  final int id;
  final String name;
  final String? wardType;
}

/// One staff row of `GET users/` (users/staff_admin.py), for this hospital.
/// Contact details stay on the server; the app shows who and what role.
@immutable
class StaffMember {
  const StaffMember({
    required this.userId,
    required this.name,
    this.employeeId,
    this.role,
    this.departmentId,
    this.membershipActive = false,
    this.invitePending = false,
  });

  factory StaffMember.fromJson(Map<String, Object?> json) {
    final membership = asMap(json['membership']);
    return StaffMember(
      userId: readInt(json['id']) ?? 0,
      name: readText(json['name']) ?? readText(json['username']) ?? '',
      employeeId: readText(json['employee_id']),
      role: readText(membership['role']),
      departmentId: readInt(membership['department']),
      membershipActive: membership['is_active'] == true,
      invitePending: json['invite_pending'] == true,
    );
  }

  final int userId;
  final String name;
  final String? employeeId;
  final String? role;
  final int? departmentId;

  /// Active at this hospital (a membership can be ended without deleting it).
  final bool membershipActive;
  final bool invitePending;
}
