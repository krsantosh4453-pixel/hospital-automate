/// The laboratory workflow as the server runs it (laboratory/views.py).
/// The app only decides which step to offer; the server checks the role and
/// refuses any step that does not follow the test's current status.
library;

import '../../../core/security/session_controller.dart';

/// Role names as the server writes them (users.models.StaffRole).
abstract final class StaffRoles {
  static const admin = 'Admin';
  static const doctor = 'Doctor';
  static const nurse = 'Nurse';
  static const labStaff = 'Lab Staff';
  static const receptionist = 'Receptionist';
  static const billingStaff = 'Billing Staff';
  static const hospitalManager = 'Hospital Manager';
}

/// `LabTest.STATUS_CHOICES`.
abstract final class LabStatus {
  static const ordered = 'Ordered';
  static const samplePending = 'Sample Pending';
  static const collected = 'Collected';
  static const dispatched = 'Dispatched';
  static const received = 'Received';
  static const processing = 'Processing';
  static const resultEntered = 'Result Entered';
  static const verified = 'Verified';
  static const released = 'Released';
  static const cancelled = 'Cancelled';

  /// The stages in order, for the progress bar (Sample Pending sits with Ordered).
  static const stages = [
    ordered,
    collected,
    dispatched,
    received,
    processing,
    resultEntered,
    verified,
    released,
  ];

  /// Statuses the server refuses to cancel (`cancel` action).
  static const notCancellable = {verified, released, cancelled};
}

/// One workflow action, by its server endpoint (`laboratory/<id>/<action>/`).
enum LabStep {
  collect('collect_sample', {
    StaffRoles.labStaff,
    StaffRoles.nurse,
    StaffRoles.admin,
  }),
  dispatch('dispatch_sample', {
    StaffRoles.labStaff,
    StaffRoles.nurse,
    StaffRoles.admin,
  }),
  receive('receive_sample', {StaffRoles.labStaff, StaffRoles.admin}),
  startProcessing('start_processing', {StaffRoles.labStaff, StaffRoles.admin}),
  enterResult('enter_result', {StaffRoles.labStaff, StaffRoles.admin}),
  verify('verify_result', {StaffRoles.labStaff, StaffRoles.admin}),
  release('release_result', {StaffRoles.labStaff, StaffRoles.admin});

  const LabStep(this.action, this.roles);

  final String action;

  /// The `permission_classes` of the action on the server.
  final Set<String> roles;

  /// Verifying and releasing are sign-offs: always asked before they are sent.
  bool get isSignOff => this == verify || this == release;
}

/// The one step the server accepts next for [status], or null when none.
LabStep? nextLabStep(String status) => switch (status) {
  LabStatus.ordered || LabStatus.samplePending => LabStep.collect,
  LabStatus.collected => LabStep.dispatch,
  LabStatus.dispatched => LabStep.receive,
  LabStatus.received => LabStep.startProcessing,
  LabStatus.processing => LabStep.enterResult,
  LabStatus.resultEntered => LabStep.verify,
  LabStatus.verified => LabStep.release,
  _ => null,
};

/// Position of [status] in [LabStatus.stages]; -1 when cancelled or unknown.
int labStageIndex(String status) =>
    status == LabStatus.samplePending ? 0 : LabStatus.stages.indexOf(status);

/// Worklist groups shown as filter chips. Every status falls in exactly one.
enum LabQueue {
  awaitingCollection({LabStatus.ordered, LabStatus.samplePending}),
  sampleCollected({
    LabStatus.collected,
    LabStatus.dispatched,
    LabStatus.received,
  }),
  inProgress({LabStatus.processing, LabStatus.resultEntered}),
  awaitingRelease({LabStatus.verified}),
  released({LabStatus.released}),
  cancelled({LabStatus.cancelled});

  const LabQueue(this.statuses);

  final Set<String> statuses;
}

/// Roles the server lets create or cancel an order (LabTestViewSet).
const labOrderingRoles = {
  StaffRoles.admin,
  StaffRoles.doctor,
  StaffRoles.nurse,
  StaffRoles.labStaff,
};

/// Whether [session] may be offered [step]: the server's role for that
/// action and the role's Laboratory edit permission at this hospital.
bool mayRunLabStep(SessionState session, LabStep step) =>
    session.hasRole(step.roles) && session.can('Laboratory', 'Edit');

/// Ordering also needs the Add permission (a Nurse views and edits only).
bool mayOrderLabTests(SessionState session) =>
    session.hasRole(labOrderingRoles) && session.can('Laboratory', 'Add');

bool mayCancelLabOrder(SessionState session, String status) =>
    !LabStatus.notCancellable.contains(status) &&
    session.hasRole(labOrderingRoles) &&
    (session.can('Laboratory', 'Edit') || session.can('Laboratory', 'Add'));

/// `SampleCollection.SAMPLE_TYPES` values.
const labSampleTypes = [
  'Blood',
  'Urine',
  'Stool',
  'Sputum',
  'Swab',
  'Tissue',
  'Fluid',
  'Other',
];

/// `SampleCollection.CONTAINER_TYPES` values.
const labContainerTypes = [
  'EDTA',
  'Plain',
  'Heparin',
  'Citrate',
  'Fluoride',
  'Urine Container',
  'Stool Container',
  'Swab Tube',
  'Other',
];

/// The quick picks the web order form offers (src/pages/laboratory.jsx
/// `TEST_CHOICES`). The server has no test catalogue, so these are names
/// only: no price, preparation or reference range comes with them.
const commonLabTests = [
  'Complete Blood Count',
  'Blood Sugar',
  'Lipid Profile',
  'Liver Function Test',
  'Kidney Function Test',
  'Thyroid Profile',
];
